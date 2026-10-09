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
