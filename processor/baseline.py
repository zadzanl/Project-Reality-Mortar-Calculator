#!/usr/bin/env python3
"""Baseline capture/compare regression safety harness for generated map artifacts.

ROLE: Maintainer-only Regression Safety Gate. Ensures zero silent data corruption across 84 maps.
INPUTS:
    - processed_maps/ (read-only verification of terrain, flow, heightmap, metadata)
OUTPUTS:
    - Baseline JSON snapshots or comparison regression reports.
HOW TO RUN:
    python processor/baseline.py capture --out baseline.json
    python processor/baseline.py compare --baseline baseline.json
DID IT WORK CHECK:
    Exits with code 0 on pass / capture written; non-zero on regression tolerance exceedance.

Dependencies: Python stdlib + NumPy only. The harness is READ-ONLY against
processed_maps/ and raw_map_data/ and refuses to write output files inside them.
It deliberately does NOT import processor/terrain_artifact.py or any other
processor module: artifacts are decoded directly from sidecar JSON + np.fromfile
so the harness keeps working while the pipeline modules are mid-refactor.

Deterministic sampling rule (recorded in every baseline document):
    per (map, grid): rng = numpy.random.default_rng(20261009);
    indices = sorted(rng.choice(grid_size, size=min(64, grid_size), replace=False)).
    The SAME seed is reused for every grid by design, so equal-sized grids share
    indices; that is deterministic, which is all the regression use needs.

Grid decode contract (format 1.0/1.1 today, 1.2 after quantization):
    - Shape always comes from the terrain sidecar grid.rows/grid.cols (or the
      flow sidecar grid for flow grids); never guessed.
    - dtype comes from the sidecar entry. Legacy defaults when the sidecar has
      no per-grid entry: cost.bin "<f4", classes.bin "u1", road_mask/water/
      bridge_mask "u1", diagnostics carry their own "dtype".
    - Format 1.2 quantization entry (per grid): {"dtype", "offset", "scale"}
      either nested under a grid entry's "quantization" key, as top-level
      "offset"/"scale" keys on a diagnostics entry, or in a sidecar-level
      "quantization" dict keyed by terrain-relative path (e.g.
      "infantry/cost.bin"). Dequantize as value = offset + raw * scale.
      If the 1.2 writer picks a different shape, update _entry_with_quant()
      below -- it is the single point of change.

Known ceilings (deliberate, documented):
    - The firing-solution fixture needs `node` on PATH and covers only
      FIRING_MAPS (adak, muttrah_city_2). If node or the script fails, the
      fixture records {"status": "unavailable", "reason": ...} and capture
      CONTINUES; compare treats unavailable-on-either-side as a note, not a
      failure. Upgrade path: extend FIRING_MAPS once the fixture proves stable.
    - File sha256s are INFORMATIONAL only: serialization changes legitimately
      change them, so they are reported but never fail a comparison.
    - The baseline document contains no timestamp, so two captures over
      unchanged data are byte-identical.

Compare integrity (fail-closed; review-001 repairs):
    - The baseline document must carry format == BASELINE_FORMAT, a non-empty
      "maps" object, and the same sampling seed/count as this harness;
      anything else (including a compare REPORT mistaken for a baseline)
      exits 2 before any map data is read.
    - Every requested --maps name must exist in the baseline; unknown names
      exit 2. Zero-coverage compares are therefore impossible.
    - Per grid, stored sample indices must equal the deterministic rule for
      the grid shape and len(values) must equal len(indices); a mismatch is an
      exceedance, never silently zip-truncated.
    - Blocked cost cells: when the terrain sidecar records blocked_sentinel,
      a sampled cost cell equal to the sentinel on either side must be exactly
      equal on the other side; scale/2 never applies to sentinels. This
      matches the terrain-traversability 1.2 spec: "blocked/unreachable
      sentinel cells decode to the exact documented sentinel".

Operator safety (fail-closed; review-003 repairs):
    - An explicit --maps argument that parses to zero names (",", ",,",
      whitespace) exits 2 for both capture and compare; only an omitted
      --maps selects the default set.
    - compare rejects a --report path that resolves to the --baseline path
      before reading or writing anything, so a path mistake cannot destroy
      the gate artifact.
    - The final console line always prints compared/total map coverage
      (e.g. "compare: pass (0 exceedances; 1/8 maps)") so a subset run can
      never be mistaken for the full gate.
    - The >50-exceedance truncation hint says "see --report" only when a
      report was actually requested; otherwise it tells the operator to
      rerun with --report.
"""

import argparse
import gc
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "processed_maps"
RAW_MAP_DATA = REPO_ROOT / "raw_map_data"
FIRING_SCRIPT = Path(__file__).resolve().parent / "baseline_firing.mjs"

BASELINE_FORMAT = "1.0"
SAMPLE_SEED = 20261009
SAMPLE_COUNT = 64
FLOW_SENTINEL = 255
FLOW_TOL_REL = 0.02
FLOW_TOL_ABS_S = 1.0
BBOX_TOL_M = 0.1
FIRING_TOL_MILS = 0.5

# Fixed choices adak/albasrah_2/muttrah_city_2 plus the five maps with the
# largest obstructions.json (fields_of_kassel 182.6 MB, ascheberg 172.9 MB,
# korbach_offensive 169.6 MB, road_to_damascus 166.3 MB, shijiavalley 148.9 MB
# as of 2026-10-09).
DEFAULT_MAPS = [
    "adak",
    "albasrah_2",
    "muttrah_city_2",
    "fields_of_kassel",
    "ascheberg",
    "korbach_offensive",
    "road_to_damascus",
    "shijiavalley",
]

# Maps that get the node-based firing-solution fixture (known ceiling, see header).
FIRING_MAPS = ("adak", "muttrah_city_2")

TOLERANCES = {
    "mask_grids": "exact per sampled cell (uint8 masks/classes)",
    "continuous_grids": "exact on 6-decimal rounded values when the NEW artifact is "
                        "unquantized (legacy float32); <= scale/2 per cell when the NEW "
                        "sidecar carries a quantization entry",
    "flow_arrival_seconds": "<= max(2% of baseline, 1.0 s) per sampled cell",
    "flow_unreachable_count": "exact per grid (count of 255 sentinel cells)",
    "flow_reachable_flips": "<= --max-flow-flips per grid (default 0)",
    "obstruction_counts": "exact (total, per type, road_triangles)",
    "obstruction_normalized_hash": "exact (records normalized to 0.1 m before hashing)",
    "obstruction_bbox": "<= 0.1 m per bbox component",
    "firing_mils": "<= 0.5 mil per fixed pair",
}

SAMPLING_RULE = (
    "per (map, grid): rng = numpy.random.default_rng(20261009); "
    "indices = sorted(rng.choice(grid_size, size=min(64, grid_size), replace=False)); "
    "same seed reused for every grid by design"
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_indices(size):
    """Deterministic flat cell sample; see SAMPLING_RULE."""
    rng = np.random.default_rng(SAMPLE_SEED)
    count = min(SAMPLE_COUNT, int(size))
    return sorted(int(i) for i in rng.choice(int(size), size=count, replace=False))


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _round6(value):
    return round(float(value), 6)


# ---------------------------------------------------------------------------
# Grid decoding (sidecar-driven; no processor imports)
# ---------------------------------------------------------------------------

def _entry_with_quant(default_dtype, *sources):
    """Resolve {dtype, offset, scale} for one grid.

    sources are dicts that may carry quantization info, in priority order:
    a nested {"quantization": {dtype, offset, scale}} mapping, or a dict that
    itself has a "scale" key (a bare quantization entry). offset/scale are
    None for unquantized (legacy) grids.
    """
    for src in sources:
        if not isinstance(src, dict):
            continue
        quant = src.get("quantization")
        if isinstance(quant, dict) and "scale" in quant:
            return {"dtype": quant.get("dtype", default_dtype),
                    "offset": float(quant.get("offset", 0.0)),
                    "scale": float(quant["scale"])}
        if "scale" in src:
            return {"dtype": src.get("dtype", default_dtype),
                    "offset": float(src.get("offset", 0.0)),
                    "scale": float(src["scale"])}
    return {"dtype": default_dtype, "offset": None, "scale": None}


def decode_grid(bin_path, entry, rows, cols):
    """Decode one grid via np.fromfile; dequantize when entry has a scale.

    Returns a flat NumPy array (float64 when dequantized or float dtype,
    integer otherwise). Raises ValueError on element-count mismatch.
    """
    dtype = np.dtype(entry["dtype"])
    raw = np.fromfile(bin_path, dtype=dtype)
    expected = int(rows) * int(cols)
    if raw.size != expected:
        raise ValueError("%s: expected %d elements (%dx%d), got %d"
                         % (bin_path, expected, rows, cols, raw.size))
    if entry.get("scale") is not None:
        return raw.astype(np.float64) * entry["scale"] + (entry.get("offset") or 0.0)
    return raw


def _grid_fixture(bin_path, entry, rows, cols):
    """Decode + sample one terrain grid into a fixture dict."""
    arr = decode_grid(bin_path, entry, rows, cols)
    kind = "continuous" if (entry.get("scale") is not None
                            or np.dtype(entry["dtype"]).kind == "f") else "mask"
    indices = sample_indices(arr.size)
    if kind == "mask":
        values = [int(arr[i]) for i in indices]
    else:
        values = [_round6(arr[i]) for i in indices]
    return {"kind": kind,
            "dtype": str(np.dtype(entry["dtype"])),
            "scale": entry.get("scale"),
            "shape": [int(rows), int(cols)],
            "indices": indices,
            "values": values}


# ---------------------------------------------------------------------------
# Capture: files / terrain / flow / obstructions / firing
# ---------------------------------------------------------------------------

def capture_files(map_dir):
    """sha256 + size of every file under the map folder. INFORMATIONAL only."""
    out = {}
    for path in sorted(map_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(map_dir).as_posix()
            out[rel] = {"sha256": sha256_file(path), "size": path.stat().st_size}
    return out


def capture_terrain(map_dir):
    terrain_dir = map_dir / "terrain"
    if not terrain_dir.is_dir():
        return {"format_version": None, "blocked_sentinel": None, "grids": {}}
    sidecar = _read_json(terrain_dir / "sidecar.json")
    grid = sidecar["grid"]
    rows, cols = int(grid["rows"]), int(grid["cols"])
    top_quant = sidecar.get("quantization", {})
    if not isinstance(top_quant, dict):
        top_quant = {}
    grids = {}

    def add(rel, entry):
        bin_path = terrain_dir / rel
        if not bin_path.is_file():
            return
        grids[rel] = _grid_fixture(bin_path, entry, rows, cols)

    # Diagnostics carry their own dtype (and, in 1.2, quantization) entries.
    for name, diag in sorted(sidecar.get("diagnostics", {}).items()):
        rel = diag.get("file", name + ".bin")
        add(rel, _entry_with_quant(diag.get("dtype", "<f4"), diag, top_quant.get(rel)))

    # Masks: uint8 today; a 1.2 sidecar-level quantization entry would override.
    for mask_name in ("road_mask.bin", "water.bin", "bridge_mask.bin"):
        add(mask_name, _entry_with_quant("u1", top_quant.get(mask_name)))

    # Per-profile cost/classes grids.
    for sub in sorted(terrain_dir.iterdir()):
        if not sub.is_dir():
            continue
        profile_sidecar = {}
        ps_path = sub / "sidecar.json"
        if ps_path.is_file():
            profile_sidecar = _read_json(ps_path)
        pquant = profile_sidecar.get("quantization", {})
        if not isinstance(pquant, dict):
            pquant = {}
        for fname, default_dtype in (("cost.bin", "<f4"), ("classes.bin", "u1")):
            rel = "%s/%s" % (sub.name, fname)
            add(rel, _entry_with_quant(default_dtype, pquant.get(fname),
                                       top_quant.get(rel)))

    return {"format_version": sidecar.get("format_version"),
            "blocked_sentinel": sidecar.get("blocked_sentinel"),
            "grids": grids}


def _flow_grid_fixture(bin_path, sidecar):
    """Sample one uint8 arrival grid; values stored as SECONDS (None = unreachable)."""
    grid = sidecar["grid"]
    rows, cols = int(grid["rows"]), int(grid["cols"])
    quant = sidecar.get("quantization", {})
    quantum = float(quant.get("quantum_s", 1.0))
    sentinel = int(quant.get("unreachable", FLOW_SENTINEL))
    raw = np.fromfile(bin_path, dtype=np.uint8)
    if raw.size != rows * cols:
        raise ValueError("%s: expected %d elements, got %d"
                         % (bin_path, rows * cols, raw.size))
    indices = sample_indices(raw.size)
    values = [None if int(raw[i]) == sentinel else _round6(int(raw[i]) * quantum)
              for i in indices]
    return {"shape": [rows, cols],
            "quantum_s": quantum,
            "unreachable_count": int(np.count_nonzero(raw == sentinel)),
            "indices": indices,
            "values": values}


def _capture_flow_team_dir(fixtures, key_prefix, team_dir):
    for bin_path in sorted(team_dir.glob("*.bin")):
        sidecar_path = bin_path.with_suffix(".json")
        if not sidecar_path.is_file():
            continue  # no sidecar: cannot decode shape; file hash still covers it
        sidecar = _read_json(sidecar_path)
        fixtures["%s/%s/%s" % (key_prefix, team_dir.name, bin_path.stem)] = \
            _flow_grid_fixture(bin_path, sidecar)


def capture_flow(map_dir):
    """Capture v1 layer-root grids and the ACTIVE v2 generation per layer.

    v2 generations are keyed as "<layer>/v2/team<N>/<class>" (not by build_id,
    which legitimately changes on regeneration); the active build_id is recorded
    informationally per layer. Stale non-active generations are not captured.
    """
    flow_dir = map_dir / "flow"
    if not flow_dir.is_dir():
        return {"grids": {}, "active_builds": {}}
    fixtures = {}
    active_builds = {}
    for layer_dir in sorted(p for p in flow_dir.iterdir() if p.is_dir()):
        layer = layer_dir.name
        for team_dir in sorted(layer_dir.glob("team*")):
            if team_dir.is_dir():
                _capture_flow_team_dir(fixtures, "%s/v1" % layer, team_dir)
        pointer_path = layer_dir / "class_manifest.json"
        if pointer_path.is_file():
            pointer = _read_json(pointer_path)
            active_builds[layer] = pointer.get("build_id")
            gen_rel = pointer.get("generation")
            gen_dir = layer_dir / gen_rel if gen_rel else None
            if gen_dir is not None and gen_dir.is_dir():
                for team_dir in sorted(gen_dir.glob("team*")):
                    if team_dir.is_dir():
                        _capture_flow_team_dir(fixtures, "%s/v2" % layer, team_dir)
    return {"grids": fixtures, "active_builds": active_builds}


def _round_deep(value, digits):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, list):
        return [_round_deep(v, digits) for v in value]
    if isinstance(value, dict):
        return {k: _round_deep(v, digits) for k, v in value.items()}
    return value


def capture_obstructions(map_dir):
    """Counts, bbox, and a normalized hash over 0.1 m-rounded records.

    Reads obstructions.json, or obstructions.json.gz when only the gzipped
    form exists (the planned post-change layout). The normalized hash is the
    semantic-equality anchor: rounding every float to 0.1 m is idempotent, so
    it survives the planned coordinate rounding + gzip serialization change.
    """
    plain = map_dir / "obstructions.json"
    gzipped = map_dir / "obstructions.json.gz"
    if plain.is_file():
        source = plain.name
        with open(plain, "r", encoding="ascii") as handle:
            data = json.load(handle)
    elif gzipped.is_file():
        source = gzipped.name
        with gzip.open(gzipped, "rt", encoding="ascii") as handle:
            data = json.load(handle)
    else:
        return {"status": "missing"}

    counts = {}
    record_strings = []
    minx = miny = float("inf")
    maxx = maxy = float("-inf")

    def track(x, y):
        nonlocal minx, miny, maxx, maxy
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x)
            maxy = max(maxy, y)

    roads = data.get("roads", [])
    for rec in roads:
        for tri in rec.get("triangles", []):
            for point in tri:
                if isinstance(point, list) and len(point) >= 2:
                    track(point[0], point[1])
        record_strings.append(json.dumps(_round_deep(rec, 1), sort_keys=True,
                                         separators=(",", ":")))
    for rtype in ("statics", "vegetation"):
        for rec in data.get(rtype, []):
            track(rec.get("x"), rec.get("y"))
            record_strings.append(json.dumps(_round_deep(rec, 1), sort_keys=True,
                                             separators=(",", ":")))
        counts[rtype] = len(data.get(rtype, []))
    counts["roads"] = len(roads)
    counts["road_triangles"] = sum(len(r.get("triangles", [])) for r in roads)
    counts["total"] = counts["roads"] + counts["statics"] + counts["vegetation"]

    record_strings.sort()
    digest = hashlib.sha256("\n".join(record_strings).encode("utf-8")).hexdigest()
    bbox = None
    if minx != float("inf"):
        bbox = [_round6(minx), _round6(miny), _round6(maxx), _round6(maxy)]
    result = {"status": "ok", "source_file": source, "counts": counts,
              "bbox": bbox, "normalized_sha256": digest}
    del data, record_strings
    return result


def capture_firing(map_name, map_dir):
    """Node-based firing-solution fixture; unavailable is NOT a hard failure."""
    if map_name not in FIRING_MAPS:
        return None
    node = shutil.which("node")
    if node is None:
        return {"status": "unavailable", "reason": "node executable not found on PATH"}
    if not FIRING_SCRIPT.is_file():
        return {"status": "unavailable",
                "reason": "missing script: %s" % FIRING_SCRIPT}
    try:
        proc = subprocess.run([node, str(FIRING_SCRIPT), str(map_dir)],
                              capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": str(exc)}
    if proc.returncode != 0:
        return {"status": "unavailable",
                "reason": "exit %d: %s" % (proc.returncode,
                                           proc.stderr.strip()[:500])}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "unavailable", "reason": "invalid JSON from script: %s" % exc}
    return {"status": "ok", "pairs": payload.get("pairs", [])}


def capture_map(root, map_name):
    map_dir = Path(root) / map_name
    if not map_dir.is_dir():
        raise FileNotFoundError("map directory not found: %s" % map_dir)
    result = {"files": capture_files(map_dir),
              "terrain": capture_terrain(map_dir),
              "flow": capture_flow(map_dir),
              "obstructions": capture_obstructions(map_dir)}
    gc.collect()  # drop obstructions parse garbage before the next map
    firing = capture_firing(map_name, map_dir)
    if firing is not None:
        result["firing"] = firing
    return result


def build_document(maps_data):
    return {
        "format": BASELINE_FORMAT,
        "tool": "processor/baseline.py",
        "sampling": {"seed": SAMPLE_SEED, "count": SAMPLE_COUNT,
                     "rule": SAMPLING_RULE},
        "tolerances": TOLERANCES,
        "maps": maps_data,
    }


def dump_document(doc):
    """Deterministic serialization: sorted keys, fixed formatting, no timestamp."""
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

def _exceed(exceedances, map_name, artifact, rule, message,
            cell_index=None, baseline=None, new=None, tolerance=None):
    entry = {"map": map_name, "artifact": artifact, "rule": rule,
             "message": message}
    if cell_index is not None:
        entry["cell_index"] = cell_index
    if baseline is not None:
        entry["baseline"] = baseline
    if new is not None:
        entry["new"] = new
    if tolerance is not None:
        entry["tolerance"] = tolerance
    exceedances.append(entry)


def _sampling_ok(map_name, artifact, fix, side, exceedances):
    """Fail-closed check: stored indices/values must match the recorded rule.

    Guards against zip pairing mismatched or truncated samples when a
    baseline was captured with different sampling constants or hand-edited.
    """
    rows, cols = fix.get("shape", (0, 0))
    expected = sample_indices(int(rows) * int(cols))
    indices = fix.get("indices")
    values = fix.get("values")
    if indices != expected:
        _exceed(exceedances, map_name, artifact, "sampling_integrity",
                "%s fixture indices do not match the recorded sampling rule "
                "for shape %s" % (side, fix.get("shape")))
        return False
    if not isinstance(values, list) or len(values) != len(indices):
        _exceed(exceedances, map_name, artifact, "sampling_integrity",
                "%s fixture values length (%s) != indices length (%d)"
                % (side,
                   len(values) if isinstance(values, list)
                   else type(values).__name__,
                   len(indices)))
        return False
    return True


def _compare_terrain(map_name, baseline, current, exceedances, notes):
    bsent = baseline.get("blocked_sentinel")
    csent = current.get("blocked_sentinel")
    if bsent is not None and csent is not None and float(bsent) != float(csent):
        _exceed(exceedances, map_name, "terrain", "blocked_sentinel",
                "blocked sentinel changed", baseline=bsent, new=csent,
                tolerance=0)
    sentinel = bsent if bsent is not None else csent
    if sentinel is None:
        notes.append("%s: no blocked_sentinel recorded on either side; "
                     "sentinel exactness not enforced" % map_name)
    else:
        sentinel = float(sentinel)
    bgrids = baseline.get("grids", {})
    cgrids = current.get("grids", {})
    for rel, bfix in sorted(bgrids.items()):
        artifact = "terrain/%s" % rel
        cfix = cgrids.get(rel)
        if cfix is None:
            _exceed(exceedances, map_name, artifact, "presence",
                    "grid missing in current data")
            continue
        if bfix["shape"] != cfix["shape"]:
            _exceed(exceedances, map_name, artifact, "shape",
                    "shape changed: %s -> %s" % (bfix["shape"], cfix["shape"]),
                    baseline=bfix["shape"], new=cfix["shape"])
            continue
        if not (_sampling_ok(map_name, artifact, bfix, "baseline", exceedances)
                and _sampling_ok(map_name, artifact, cfix, "current",
                                 exceedances)):
            continue
        if bfix["kind"] == "mask":
            if cfix["kind"] != "mask":
                _exceed(exceedances, map_name, artifact, "kind",
                        "mask grid became continuous (quantized?)")
                continue
            for idx, bval, cval in zip(bfix["indices"], bfix["values"],
                                       cfix["values"]):
                if bval != cval:
                    _exceed(exceedances, map_name, artifact, "mask_exact",
                            "mask cell changed", cell_index=idx,
                            baseline=bval, new=cval, tolerance=0)
        else:
            scale = cfix.get("scale")
            tol = None if scale is None else abs(float(scale)) / 2.0
            rule = "continuous_exact" if tol is None else "continuous_quantized"
            is_cost = rel.endswith("cost.bin")
            for idx, bval, cval in zip(bfix["indices"], bfix["values"],
                                       cfix["values"]):
                if sentinel is not None and is_cost \
                        and (bval == sentinel or cval == sentinel):
                    # Sentinels must match exactly on both sides; scale/2
                    # never applies (1.2 spec: sentinel cells decode to the
                    # exact documented sentinel).
                    if bval != cval:
                        _exceed(exceedances, map_name, artifact,
                                "blocked_sentinel_exact",
                                "blocked sentinel cell changed",
                                cell_index=idx, baseline=bval, new=cval,
                                tolerance=0.0)
                    continue
                if tol is None:
                    ok = bval == cval  # exact on 6-decimal rounded values
                else:
                    ok = abs(cval - bval) <= tol + 1e-6
                if not ok:
                    _exceed(exceedances, map_name, artifact, rule,
                            "continuous cell drift",
                            cell_index=idx, baseline=bval, new=cval,
                            tolerance=0.0 if tol is None else tol)
    for rel in sorted(set(cgrids) - set(bgrids)):
        notes.append("%s: new terrain grid not in baseline: %s" % (map_name, rel))


def _compare_flow(map_name, baseline, current, max_flow_flips, exceedances, notes):
    bgrids = baseline.get("grids", {})
    cgrids = current.get("grids", {})
    for key, bfix in sorted(bgrids.items()):
        artifact = "flow/%s" % key
        cfix = cgrids.get(key)
        if cfix is None:
            _exceed(exceedances, map_name, artifact, "presence",
                    "flow grid missing in current data")
            continue
        if bfix["shape"] != cfix["shape"]:
            _exceed(exceedances, map_name, artifact, "shape",
                    "shape changed: %s -> %s" % (bfix["shape"], cfix["shape"]),
                    baseline=bfix["shape"], new=cfix["shape"])
            continue
        if not (_sampling_ok(map_name, artifact, bfix, "baseline", exceedances)
                and _sampling_ok(map_name, artifact, cfix, "current",
                                 exceedances)):
            continue
        if bfix["unreachable_count"] != cfix["unreachable_count"]:
            _exceed(exceedances, map_name, artifact, "unreachable_count",
                    "unreachable sentinel count changed",
                    baseline=bfix["unreachable_count"],
                    new=cfix["unreachable_count"], tolerance=0)
        flips = []
        for idx, bval, cval in zip(bfix["indices"], bfix["values"],
                                   cfix["values"]):
            if bval is None and cval is None:
                continue
            if (bval is None) != (cval is None):
                flips.append((idx, bval, cval))
                continue
            tol = max(FLOW_TOL_REL * bval, FLOW_TOL_ABS_S)
            if abs(cval - bval) > tol + 1e-6:
                _exceed(exceedances, map_name, artifact, "flow_arrival",
                        "arrival time drift (seconds)", cell_index=idx,
                        baseline=bval, new=cval, tolerance=tol)
        if len(flips) > max_flow_flips:
            for idx, bval, cval in flips:
                _exceed(exceedances, map_name, artifact, "flow_flip",
                        "cell flipped reachable<->unreachable "
                        "(%d flips > cap %d)" % (len(flips), max_flow_flips),
                        cell_index=idx, baseline=bval, new=cval,
                        tolerance=max_flow_flips)
    for key in sorted(set(cgrids) - set(bgrids)):
        notes.append("%s: new flow grid not in baseline: %s" % (map_name, key))


def _compare_obstructions(map_name, baseline, current, exceedances, notes):
    if baseline is None and current is None:
        return
    if baseline is None or current is None:
        _exceed(exceedances, map_name, "obstructions", "presence",
                "obstruction fixture present on one side only")
        return
    if baseline.get("status") != "ok" or current.get("status") != "ok":
        if baseline.get("status") != current.get("status"):
            _exceed(exceedances, map_name, "obstructions", "presence",
                    "status changed: %s -> %s"
                    % (baseline.get("status"), current.get("status")))
        return
    for key, bval in sorted(baseline["counts"].items()):
        cval = current["counts"].get(key)
        if bval != cval:
            _exceed(exceedances, map_name, "obstructions", "record_count",
                    "record count mismatch for '%s'" % key,
                    baseline=bval, new=cval, tolerance=0)
    if baseline["normalized_sha256"] != current["normalized_sha256"]:
        _exceed(exceedances, map_name, "obstructions", "normalized_hash",
                "normalized (0.1 m) record hash mismatch",
                baseline=baseline["normalized_sha256"],
                new=current["normalized_sha256"], tolerance=0)
    bbbox, cbbox = baseline.get("bbox"), current.get("bbox")
    if (bbbox is None) != (cbbox is None):
        _exceed(exceedances, map_name, "obstructions", "bbox",
                "bbox present on one side only",
                baseline=bbbox, new=cbbox)
    elif bbbox is not None:
        for axis, bval, cval in zip(("minx", "miny", "maxx", "maxy"), bbbox, cbbox):
            if abs(cval - bval) > BBOX_TOL_M:
                _exceed(exceedances, map_name, "obstructions", "bbox",
                        "bbox component '%s' moved" % axis,
                        baseline=bval, new=cval, tolerance=BBOX_TOL_M)
    if baseline.get("source_file") != current.get("source_file"):
        notes.append("%s: obstructions source file changed: %s -> %s"
                     % (map_name, baseline.get("source_file"),
                        current.get("source_file")))


def _compare_firing(map_name, baseline, current, exceedances, notes):
    if baseline is None:
        return  # not a firing-fixture map
    if baseline.get("status") != "ok" or not isinstance(current, dict) \
            or current.get("status") != "ok":
        notes.append("%s: firing fixture unavailable on %s side; skipped "
                     "(documented known ceiling)"
                     % (map_name,
                        "baseline" if baseline.get("status") != "ok"
                        else "current"))
        return
    bpairs = {(p["mortar"], p["target"]): p for p in baseline.get("pairs", [])}
    cpairs = {(p["mortar"], p["target"]): p for p in current.get("pairs", [])}
    for key, bpair in sorted(bpairs.items()):
        artifact = "firing/%s->%s" % key
        cpair = cpairs.get(key)
        if cpair is None:
            _exceed(exceedances, map_name, artifact, "presence",
                    "firing pair missing in current data")
            continue
        if bpair.get("valid") != cpair.get("valid") \
                or bpair.get("status") != cpair.get("status"):
            _exceed(exceedances, map_name, artifact, "firing_status",
                    "solution validity/status changed",
                    baseline=bpair.get("status"), new=cpair.get("status"))
            continue
        bmils, cmils = bpair.get("elevationMils"), cpair.get("elevationMils")
        if bmils is None or cmils is None:
            continue  # both invalid with equal status; nothing to compare
        if abs(cmils - bmils) > FIRING_TOL_MILS:
            _exceed(exceedances, map_name, artifact, "firing_mils",
                    "elevation drift", baseline=bmils, new=cmils,
                    tolerance=FIRING_TOL_MILS)


def compare_maps(baseline_maps, current_maps, max_flow_flips):
    exceedances = []
    notes = []
    files_info = {}
    for map_name in sorted(baseline_maps):
        bmap = baseline_maps[map_name]
        cmap = current_maps.get(map_name)
        if cmap is None:
            _exceed(exceedances, map_name, "<map>", "presence",
                    "map directory missing in current data")
            continue
        bfiles, cfiles = bmap.get("files", {}), cmap.get("files", {})
        files_info[map_name] = {
            "changed": sum(1 for p in bfiles if p in cfiles
                           and bfiles[p]["sha256"] != cfiles[p]["sha256"]),
            "missing": sum(1 for p in bfiles if p not in cfiles),
            "added": sum(1 for p in cfiles if p not in bfiles),
        }
        _compare_terrain(map_name, bmap.get("terrain", {}),
                         cmap.get("terrain", {}), exceedances, notes)
        _compare_flow(map_name, bmap.get("flow", {}), cmap.get("flow", {}),
                      max_flow_flips, exceedances, notes)
        _compare_obstructions(map_name, bmap.get("obstructions"),
                              cmap.get("obstructions"), exceedances, notes)
        _compare_firing(map_name, bmap.get("firing"), cmap.get("firing"),
                        exceedances, notes)
    return exceedances, notes, files_info


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_maps(value):
    if value is None:
        return list(DEFAULT_MAPS)
    maps = [part.strip() for part in value.split(",") if part.strip()]
    if not maps:
        raise ValueError("--maps %r selects zero maps; pass comma-separated "
                         "map names or omit --maps for the default set"
                         % value)
    return maps


def _guard_output_path(path, root):
    resolved = Path(path).resolve()
    for forbidden in (Path(root).resolve(), RAW_MAP_DATA.resolve()):
        try:
            resolved.relative_to(forbidden)
        except ValueError:
            continue
        raise ValueError("refusing to write inside read-only tree: %s" % forbidden)


def _cmd_capture(args):
    root = Path(args.root)
    maps = _parse_maps(args.maps)
    _guard_output_path(args.out, root)
    maps_data = {}
    for index, name in enumerate(maps, 1):
        print("[%d/%d] capturing %s ..." % (index, len(maps), name), flush=True)
        maps_data[name] = capture_map(root, name)
        gc.collect()
    doc = build_document(maps_data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_document(doc), encoding="utf-8")
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))
    return 0


def _cmd_compare(args):
    root = Path(args.root)
    if args.report:
        _guard_output_path(args.report, root)
    baseline_path = Path(args.baseline)
    if args.report and Path(args.report).resolve() == baseline_path.resolve():
        print("error: --report path resolves to the --baseline path (%s); "
              "refusing to overwrite the baseline" % baseline_path,
              file=sys.stderr)
        return 2
    if not baseline_path.is_file():
        print("error: baseline not found: %s" % baseline_path, file=sys.stderr)
        return 2
    baseline_doc = _read_json(baseline_path)
    if not isinstance(baseline_doc, dict) \
            or baseline_doc.get("format") != BASELINE_FORMAT:
        print("error: %s is not a format-%s baseline document "
              "(a compare report is not a baseline)"
              % (baseline_path, BASELINE_FORMAT), file=sys.stderr)
        return 2
    baseline_maps = baseline_doc.get("maps")
    if not isinstance(baseline_maps, dict) or not baseline_maps:
        print("error: baseline document has no maps: %s" % baseline_path,
              file=sys.stderr)
        return 2
    sampling = baseline_doc.get("sampling")
    if not isinstance(sampling, dict) or sampling.get("seed") != SAMPLE_SEED \
            or sampling.get("count") != SAMPLE_COUNT:
        print("error: baseline sampling seed/count does not match this harness "
              "(expected seed=%d count=%d); recapture the baseline"
              % (SAMPLE_SEED, SAMPLE_COUNT), file=sys.stderr)
        return 2
    maps = (_parse_maps(args.maps) if args.maps is not None
            else sorted(baseline_maps))
    unknown = sorted(set(maps) - set(baseline_maps))
    if unknown:
        print("error: requested map(s) not in baseline: %s"
              % ", ".join(unknown), file=sys.stderr)
        return 2
    current_maps = {}
    selected = {name: baseline_maps[name] for name in maps}
    for index, name in enumerate(maps, 1):
        map_dir = root / name
        if not map_dir.is_dir():
            current_maps[name] = None
            continue
        print("[%d/%d] reading %s ..." % (index, len(maps), name), flush=True)
        current_maps[name] = capture_map(root, name)
        gc.collect()
    exceedances, notes, files_info = compare_maps(selected, current_maps,
                                                  args.max_flow_flips)
    report = {"result": "fail" if exceedances else "pass",
              "baseline": str(baseline_path),
              "root": str(root),
              "max_flow_flips": args.max_flow_flips,
              "maps_compared": sorted(selected),
              "exceedance_count": len(exceedances),
              "exceedances": exceedances,
              "notes": notes,
              "files_informational": files_info}
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                               encoding="utf-8")
    for exc in exceedances[:50]:
        print("FAIL %(map)s %(artifact)s [%(rule)s] %(message)s" % exc)
    if len(exceedances) > 50:
        if args.report:
            print("... and %d more (see --report)" % (len(exceedances) - 50))
        else:
            print("... and %d more (rerun with --report for full details)"
                  % (len(exceedances) - 50))
    for note in notes:
        print("NOTE %s" % note)
    print("compare: %s (%d exceedance%s; %d/%d maps)"
          % (report["result"], len(exceedances),
             "" if len(exceedances) == 1 else "s",
             len(selected), len(baseline_maps)))
    return 1 if exceedances else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Baseline capture/compare harness for generated map artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="snapshot current artifacts")
    cap.add_argument("--out", required=True, help="baseline JSON output path")
    cap.add_argument("--maps", help="comma-separated map names (default: the fixed 8)")
    cap.add_argument("--root", default=str(DEFAULT_ROOT),
                     help="processed_maps directory")
    cap.set_defaults(func=_cmd_capture)

    cmp_parser = sub.add_parser("compare", help="verify artifacts against a baseline")
    cmp_parser.add_argument("--baseline", required=True, help="baseline JSON path")
    cmp_parser.add_argument("--report", help="write a JSON report to this path")
    cmp_parser.add_argument("--maps", help="comma-separated map names "
                            "(default: all maps in the baseline)")
    cmp_parser.add_argument("--root", default=str(DEFAULT_ROOT),
                            help="processed_maps directory")
    cmp_parser.add_argument("--max-flow-flips", type=int, default=0,
                            help="allowed reachable<->unreachable flips per flow grid")
    cmp_parser.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
