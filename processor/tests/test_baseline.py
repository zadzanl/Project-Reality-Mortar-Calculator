"""Tests for processor/baseline.py (OpenSpec change reduce-map-data-footprint,
task 1.4). Synthetic fixtures only: tiny fake map folders under tmp_path.
The firing fixture is never exercised here (fake maps are not in
baseline.FIRING_MAPS), so these tests do not require node."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import baseline

MAP = "fake_map"
ROWS = 16
COLS = 16
N = ROWS * COLS
QUANTUM_S = 2


def _write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def _flow_sidecar(format_version):
    return {"format_version": format_version,
            "artifact": "flow_field",
            "team": 1,
            "agent_class": "infantry",
            "grid": {"rows": ROWS, "cols": COLS, "cell_size_m": 4.0,
                     "origin": "top-left; x east, y south; repo world meters"},
            "quantization": {"dtype": "u1", "quantum_s": QUANTUM_S,
                             "cap_s": 3600.0, "unreachable": 255}}


def _flow_grid():
    arr = (np.arange(N) % 200).astype(np.uint8)
    arr[5] = 255  # one unreachable cell
    return arr


def make_map(root, name=MAP):
    """Build a tiny fake map folder under root (the processed_maps stand-in)."""
    map_dir = Path(root) / name
    terrain = map_dir / "terrain"
    (terrain / "infantry").mkdir(parents=True, exist_ok=True)

    slope = (np.arange(N, dtype=np.float32) * 0.5)
    (terrain / "slope_deg_mean.bin").write_bytes(slope.astype("<f4").tobytes())
    (terrain / "road_mask.bin").write_bytes((np.arange(N) % 2).astype("u1").tobytes())
    (terrain / "water.bin").write_bytes(np.zeros(N, dtype="u1").tobytes())
    (terrain / "infantry" / "cost.bin").write_bytes(
        (np.arange(N, dtype=np.float32) + 1.0).astype("<f4").tobytes())
    (terrain / "infantry" / "classes.bin").write_bytes(
        (np.arange(N) % 7).astype("u1").tobytes())
    _write_json(terrain / "sidecar.json", {
        "map_name": name, "format_version": "1.0", "artifact": "terrain_cost",
        "blocked_sentinel": -1.0,
        "diagnostics": {"slope_deg_mean": {"file": "slope_deg_mean.bin",
                                           "dtype": "<f4",
                                           "min": float(slope.min()),
                                           "max": float(slope.max())}},
        "grid": {"rows": ROWS, "cols": COLS, "cell_size_m": 4.0,
                 "origin": "top-left; x east, y south; repo world meters"},
    })
    _write_json(terrain / "infantry" / "sidecar.json", {"profile": "infantry"})

    layer = map_dir / "flow" / "gpm_cq_64"
    (layer / "team1").mkdir(parents=True, exist_ok=True)
    (layer / "team1" / "infantry.bin").write_bytes(_flow_grid().tobytes())
    _write_json(layer / "team1" / "infantry.json", _flow_sidecar("1.0"))
    gen = layer / "generations" / "v2-fake-abc"
    (gen / "team1").mkdir(parents=True, exist_ok=True)
    (gen / "team1" / "infantry.bin").write_bytes(_flow_grid().tobytes())
    _write_json(gen / "team1" / "infantry.json", _flow_sidecar("2.0"))
    _write_json(layer / "class_manifest.json", {
        "format_version": "2.0", "artifact": "flow_class_manifest",
        "build_id": "v2-fake-abc", "generation": "generations/v2-fake-abc"})

    _write_json(map_dir / "obstructions.json", {
        "map_name": name, "format_version": "1.0",
        "roads": [{"name": "road_a",
                   "triangles": [[[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]]]}],
        "statics": [{"template": "bldg", "class": "building",
                     "x": 5.0, "y": 6.0, "rotation_deg": 90.0}],
        "vegetation": [{"template": "bush", "x": 1.0, "y": 2.0}],
        "counts": {"roads": 1, "road_triangles": 1, "statics_classified": 1,
                   "statics_unclassified": 0, "vegetation": 1},
    })
    return map_dir


@pytest.fixture()
def root(tmp_path):
    root = tmp_path / "processed_maps"
    make_map(root)
    return root


def capture(root, out):
    return baseline.main(["capture", "--out", str(out),
                          "--root", str(root), "--maps", MAP])


def compare(root, baseline_path, report=None, extra=None):
    argv = ["compare", "--baseline", str(baseline_path), "--root", str(root)]
    if report:
        argv += ["--report", str(report)]
    if extra:
        argv += extra
    return baseline.main(argv)


def test_roundtrip_identical_data_passes(root, tmp_path):
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    assert compare(root, out) == 0


def test_capture_is_byte_identical_on_unchanged_data(root, tmp_path):
    first = tmp_path / "b1.json"
    second = tmp_path / "b2.json"
    assert capture(root, first) == 0
    assert capture(root, second) == 0
    assert first.read_bytes() == second.read_bytes()


def test_firing_fixture_not_attempted_for_non_firing_maps(root, tmp_path):
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "firing" not in doc["maps"][MAP]


def test_mask_cell_flip_fails(root, tmp_path):
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    mask_path = root / MAP / "terrain" / "road_mask.bin"
    arr = np.fromfile(mask_path, dtype=np.uint8)
    cell = baseline.sample_indices(arr.size)[0]
    arr[cell] ^= 1
    arr.tofile(mask_path)
    assert compare(root, out, report) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    hits = [e for e in data["exceedances"]
            if e["artifact"] == "terrain/road_mask.bin"
            and e["rule"] == "mask_exact" and e["cell_index"] == cell]
    assert len(hits) == 1
    assert hits[0]["baseline"] != hits[0]["new"]


def _quantize_slope(root, bump_cell=None):
    """Rewrite slope_deg_mean.bin as a fake format-1.2 quantized uint8 grid."""
    terrain = root / MAP / "terrain"
    sidecar_path = terrain / "sidecar.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    original = np.arange(N, dtype=np.float32) * 0.5
    raw = np.rint(original / 2.0).astype(np.uint8)  # offset 0, scale 2
    if bump_cell is not None:
        raw[bump_cell] += 3  # dequantized drift = 6 > scale/2 = 1
    (terrain / "slope_deg_mean.bin").write_bytes(raw.tobytes())
    sidecar["format_version"] = "1.2"
    sidecar["diagnostics"]["slope_deg_mean"]["quantization"] = {
        "dtype": "u1", "offset": 0.0, "scale": 2.0}
    _write_json(sidecar_path, sidecar)


def test_quantized_grid_within_half_scale_passes(root, tmp_path):
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    _quantize_slope(root)
    assert compare(root, out) == 0


def test_quantized_grid_beyond_half_scale_fails(root, tmp_path):
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    cell = baseline.sample_indices(N)[0]
    _quantize_slope(root, bump_cell=cell)
    assert compare(root, out, report) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    hits = [e for e in data["exceedances"]
            if e["artifact"] == "terrain/slope_deg_mean.bin"
            and e["rule"] == "continuous_quantized" and e["cell_index"] == cell]
    assert len(hits) == 1
    assert hits[0]["tolerance"] == 1.0


def test_flow_arrival_drift_fails(root, tmp_path):
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    bin_path = root / MAP / "flow" / "gpm_cq_64" / "team1" / "infantry.bin"
    arr = np.fromfile(bin_path, dtype=np.uint8)
    cell = next(i for i in baseline.sample_indices(arr.size)
                if arr[i] not in (255,) and arr[i] <= 100)
    arr[cell] += 100  # +200 s >> max(2% of baseline, 1.0 s)
    arr.tofile(bin_path)
    assert compare(root, out, report) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    hits = [e for e in data["exceedances"]
            if e["artifact"] == "flow/gpm_cq_64/v1/team1/infantry"
            and e["rule"] == "flow_arrival" and e["cell_index"] == cell]
    assert len(hits) == 1


def test_flow_unreachable_count_change_fails(root, tmp_path):
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    bin_path = (root / MAP / "flow" / "gpm_cq_64" / "generations"
                / "v2-fake-abc" / "team1" / "infantry.bin")
    arr = np.fromfile(bin_path, dtype=np.uint8)
    cell = next(i for i in baseline.sample_indices(arr.size) if arr[i] != 255)
    arr[cell] = 255
    arr.tofile(bin_path)
    assert compare(root, out, report) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    rules = {e["rule"] for e in data["exceedances"]
             if e["artifact"] == "flow/gpm_cq_64/v2/team1/infantry"}
    assert "unreachable_count" in rules
    assert "flow_flip" in rules


def test_obstruction_record_dropped_fails(root, tmp_path):
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    obs_path = root / MAP / "obstructions.json"
    doc = json.loads(obs_path.read_text(encoding="utf-8"))
    doc["vegetation"] = []
    _write_json(obs_path, doc)
    assert compare(root, out, report) == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    rules = {e["rule"] for e in data["exceedances"]
             if e["artifact"] == "obstructions"}
    assert "record_count" in rules
    assert "normalized_hash" in rules


def test_output_inside_processed_maps_is_refused(root, tmp_path):
    bad = root / MAP / "baseline.json"
    assert baseline.main(["capture", "--out", str(bad),
                          "--root", str(root), "--maps", MAP]) == 2
    assert not bad.exists()


# ---------------------------------------------------------------------------
# Negative tripwires added in review-001 revision (impl-002a)
# ---------------------------------------------------------------------------

def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(path, doc):
    Path(path).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n",
                          encoding="utf-8")


def test_compare_rejects_report_json_as_baseline(root, tmp_path):
    """C-01: a compare report is not a baseline; must exit 2, not pass/0."""
    fake = tmp_path / "report.json"
    _write_json(fake, {"result": "pass", "maps_compared": [],
                       "exceedances": []})
    assert compare(root, fake) == 2


def test_compare_rejects_empty_or_wrong_format_baseline(root, tmp_path):
    empty = tmp_path / "empty.json"
    _write_json(empty, {"format": baseline.BASELINE_FORMAT, "maps": {}})
    assert compare(root, empty) == 2
    wrong = tmp_path / "wrong.json"
    _write_json(wrong, {"format": "9.9", "maps": {MAP: {}}})
    assert compare(root, wrong) == 2


def test_compare_rejects_corrupt_baseline(root, tmp_path):
    bad = tmp_path / "corrupt.json"
    bad.write_text("{not json", encoding="utf-8")
    assert compare(root, bad) == 2


def test_compare_rejects_unknown_map_names(root, tmp_path):
    """C-02: unknown requested maps must exit 2, not warn + pass/0."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    assert compare(root, out, extra=["--maps", "not_a_map"]) == 2
    assert compare(root, out, extra=["--maps", "%s,not_a_map" % MAP]) == 2


def test_compare_rejects_sampling_seed_count_mismatch(root, tmp_path):
    """C-03: stored sampling seed/count must match this harness."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    tampered = _load(out)
    tampered["sampling"]["seed"] += 1
    seed_path = tmp_path / "seed.json"
    _dump(seed_path, tampered)
    assert compare(root, seed_path) == 2
    tampered = _load(out)
    tampered["sampling"]["count"] += 1
    count_path = tmp_path / "count.json"
    _dump(count_path, tampered)
    assert compare(root, count_path) == 2


def test_compare_rejects_shortened_sample_arrays(root, tmp_path):
    """C-03: zip truncation attack - dropping the last index+value from the
    baseline must fail, not silently compare one cell fewer."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    doc = _load(out)
    grid = doc["maps"][MAP]["terrain"]["grids"]["road_mask.bin"]
    grid["indices"] = grid["indices"][:-1]
    grid["values"] = grid["values"][:-1]
    _dump(out, doc)
    assert compare(root, out) == 1


def test_compare_rejects_reordered_flow_sample_indices(root, tmp_path):
    """C-03: changed index order with unchanged values passes value-wise under
    zip, so it must be caught by the sampling-integrity check."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    doc = _load(out)
    grid = doc["maps"][MAP]["flow"]["grids"]["gpm_cq_64/v1/team1/infantry"]
    grid["indices"] = list(reversed(grid["indices"]))
    _dump(out, doc)
    assert compare(root, out) == 1


def _set_cost_sentinel_at_sampled_cell(root):
    """Put a blocked sentinel (-1.0) at the first sampled cost cell."""
    cost_path = root / MAP / "terrain" / "infantry" / "cost.bin"
    arr = np.fromfile(cost_path, dtype="<f4")
    cell = baseline.sample_indices(arr.size)[0]
    arr[cell] = -1.0
    arr.tofile(cost_path)
    return cell


def _quantize_cost(root, dtype, offset, scale):
    """Rewrite infantry/cost.bin as a fake format-1.2 quantized grid."""
    terrain = root / MAP / "terrain"
    cost_path = terrain / "infantry" / "cost.bin"
    values = np.fromfile(cost_path, dtype="<f4").astype(np.float64)
    raw = np.rint((values - offset) / scale).astype(dtype)
    cost_path.write_bytes(raw.tobytes())
    sidecar_path = terrain / "sidecar.json"
    sidecar = _load(sidecar_path)
    sidecar["format_version"] = "1.2"
    _write_json(sidecar_path, sidecar)
    profile_path = terrain / "infantry" / "sidecar.json"
    profile = _load(profile_path)
    profile["quantization"] = {"cost.bin": {"dtype": np.dtype(dtype).str,
                                            "offset": offset,
                                            "scale": scale}}
    _write_json(profile_path, profile)


def test_quantized_blocked_sentinel_drift_within_half_scale_fails(root, tmp_path):
    """B-03/C-05: sentinel -1.0 quantizes to raw -3 at scale 0.3, decoding to
    -0.9: drift 0.1 <= scale/2 = 0.15, so only exact-sentinel enforcement
    can catch it. The 1.2 spec requires sentinel cells to decode exactly."""
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    cell = _set_cost_sentinel_at_sampled_cell(root)
    assert capture(root, out) == 0
    _quantize_cost(root, "<i2", 0.0, 0.3)
    assert compare(root, out, report) == 1
    data = _load(report)
    hits = [e for e in data["exceedances"]
            if e["artifact"] == "terrain/infantry/cost.bin"
            and e["rule"] == "blocked_sentinel_exact"
            and e["cell_index"] == cell]
    assert len(hits) == 1
    assert hits[0]["baseline"] == -1.0
    assert hits[0]["new"] == pytest.approx(-0.9)


def test_quantized_blocked_sentinel_exact_passes(root, tmp_path):
    """offset = sentinel: raw 0 decodes to exactly -1.0 and integer costs stay
    exact, so the quantized grid (including non-sentinel cells within
    scale/2) must pass unchanged."""
    out = tmp_path / "baseline.json"
    _set_cost_sentinel_at_sampled_cell(root)
    assert capture(root, out) == 0
    _quantize_cost(root, "<u2", -1.0, 0.5)
    assert compare(root, out) == 0


def test_firing_skip_note_visible_without_report(root, tmp_path, monkeypatch,
                                                 capsys):
    """C-06: unavailable firing fixture stays a note (exit 0) but must be
    printed even without --report."""
    monkeypatch.setattr(baseline, "FIRING_MAPS", (MAP,))
    monkeypatch.setattr(baseline, "FIRING_SCRIPT", tmp_path / "missing.mjs")
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    capsys.readouterr()  # drop capture output
    assert compare(root, out) == 0
    assert "firing fixture unavailable" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Negative tripwires added in review-003 revision (impl-003)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [",", ",,", "   "])
def test_capture_rejects_delimiter_only_maps(root, tmp_path, bad):
    """R-003-B01: an explicit --maps that parses to zero names must exit 2
    and write nothing, not capture an empty baseline."""
    out = tmp_path / "baseline.json"
    assert baseline.main(["capture", "--out", str(out), "--root", str(root),
                          "--maps", bad]) == 2
    assert not out.exists()


@pytest.mark.parametrize("bad", [",", ",,", "   "])
def test_compare_rejects_delimiter_only_maps(root, tmp_path, bad):
    """R-003-B01: delimiter/whitespace-only --maps must exit 2, not pass
    with zero maps compared."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    assert compare(root, out, extra=["--maps", bad]) == 2


def test_compare_rejects_report_path_equal_to_baseline(root, tmp_path):
    """R-003-B02: --report resolving to the --baseline path must exit 2
    before any read/write and leave the baseline byte-identical."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    before = out.read_bytes()
    assert compare(root, out, report=out) == 2
    assert out.read_bytes() == before


def test_compare_distinct_report_path_still_valid(root, tmp_path):
    """R-003-B02: a distinct --report path remains a valid compare."""
    out = tmp_path / "baseline.json"
    report = tmp_path / "report.json"
    assert capture(root, out) == 0
    assert compare(root, out, report) == 0
    assert report.is_file()


def test_compare_prints_subset_and_full_coverage(root, tmp_path, capsys):
    """R-003-C02: console output must state compared/total map coverage so a
    subset run can never be mistaken for the full gate."""
    other = "fake_map_2"
    make_map(root, name=other)
    out = tmp_path / "baseline.json"
    assert baseline.main(["capture", "--out", str(out), "--root", str(root),
                          "--maps", "%s,%s" % (MAP, other)]) == 0
    capsys.readouterr()  # drop capture output
    assert compare(root, out, extra=["--maps", MAP]) == 0
    assert "compare: pass (0 exceedances; 1/2 maps)" in capsys.readouterr().out
    assert compare(root, out) == 0
    assert "compare: pass (0 exceedances; 2/2 maps)" in capsys.readouterr().out


def test_truncation_hint_matches_report_request(root, tmp_path, capsys):
    """R-003-C03: the >50-exceedance truncation hint must not point at a
    report that was never requested."""
    out = tmp_path / "baseline.json"
    assert capture(root, out) == 0
    mask_path = root / MAP / "terrain" / "road_mask.bin"
    arr = np.fromfile(mask_path, dtype=np.uint8)
    for cell in baseline.sample_indices(arr.size):
        arr[cell] ^= 1  # 64 sampled mask flips > 50 printed cap
    arr.tofile(mask_path)
    assert compare(root, out) == 1
    assert "rerun with --report for full details" in capsys.readouterr().out
    report = tmp_path / "report.json"
    assert compare(root, out, report) == 1
    assert "(see --report)" in capsys.readouterr().out
