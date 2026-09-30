import gzip
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from build_terrain_cost import (confirmed_water_mask, candidate_water_mask,
                                compute_cost)
import build_terrain_cost as terrain
from terrain_features import compute_features


def test_flat_cost_is_passable_without_roads():
    shape = (2, 2)
    agg = {key: np.zeros(shape) for key in (
        "slope_deg_mean", "slope_deg_max", "edge_rise_m_max",
        "edge_grade_max", "roughness_m_mean")}
    config = {"profiles": {"infantry": {
        "max_slope_deg": {"value": 50}, "slope_full_penalty_deg": {"value": 30},
        "step_max_m": {"value": 0.5}}},
        "multipliers": {key: {"value": value} for key, value in {
            "slope_max": 4, "road": 1, "water": 8, "water_candidate": 1,
            "vegetation_dense": 2, "roughness_max": 2}.items()},
        "grid": {"roughness_ref_m": {"value": 0.25},
                 "roughness_multiplier_enabled": {"value": 0},
                 "smooth_slope_deg": {"value": 6},
                 "smooth_roughness_m": {"value": 0.1}}}
    costs, classes, info = compute_cost(
        agg, np.zeros(shape, dtype=np.uint8), np.zeros(shape, bool),
        np.ones(shape), np.zeros(shape, bool), config, "infantry")
    assert np.all(costs == 1.0)
    assert np.all(classes == 1)
    assert info["blocked_cells"] == 0


def test_confirmed_and_candidate_water_semantics():
    assert confirmed_water_mask(np.zeros((4, 4)), 1.0).all()
    candidate = candidate_water_mask(
        np.full((5, 5), 10.0), np.zeros((5, 5)),
        np.zeros((5, 5), bool), 0.0, 1.0, 1.0, 1.0, 0.1)
    assert not candidate.any()


@pytest.fixture
def config():
    # Inline, deliberately synthetic thresholds; no dependency on tuning defaults.
    return {
        "profiles": {"infantry": {
            "max_slope_deg": {"value": 45},
            "slope_full_penalty_deg": {"value": 30},
            "step_max_m": {"value": 0.5}}},
        "multipliers": {key: {"value": value} for key, value in {
            "slope_max": 4, "road": 0.5, "water": 8,
            "water_candidate": 1, "building": 5,
            "vegetation_dense": 2, "roughness_max": 2}.items()},
        "grid": {key: {"value": value} for key, value in {
            "cell_size_m": 4, "roughness_window_m": 6,
            "roughness_ref_m": 0.25, "roughness_multiplier_enabled": 0,
            "smooth_slope_deg": 6, "smooth_roughness_m": 0.1}.items()},
        "vegetation": {"density_radius_m": {"value": 0},
                       "dense_count": {"value": 2}},
        "water": {"flat_epsilon_deg": {"value": 1},
                  "candidate_min_area_m2": {"value": 4},
                  "basin_margin_m": {"value": 0.1}},
        "footprints_m": {"building": {"value": 4}},
    }


@pytest.mark.parametrize("geometry", ["step", "ridge"])
@pytest.mark.parametrize("height,blocked", [(1.5, False), (2.5, True)])
def test_step_and_ridge_hazards_survive_aggregation_and_roads(config, geometry, height, blocked):
    elevation = np.zeros((9, 9))
    if geometry == "step":
        elevation[:, 3:] = height
    else:
        elevation[:, 3] = height
    features = compute_features(elevation, 2.0, 6.0)
    agg = terrain.aggregate(features, elevation, 2, 4)
    assert agg["edge_rise_m_max"][0, 0] == height
    assert agg["edge_grade_max"][0, 0] == height / 2.0
    assert agg["slope_deg_mean"][0, 0] < agg["slope_deg_max"][0, 0]
    shape = (2, 2)
    costs = []
    for roads in (np.zeros(shape, bool), np.ones(shape, bool)):
        cost, classes, info = compute_cost(
            agg, np.zeros(shape, np.uint8), roads, np.ones(shape),
            np.zeros(shape, bool), config, "infantry")
        costs.append(cost)
        assert (cost[0, 0] == terrain.BLOCKED) == blocked
        assert classes[0, 0] == (4 if blocked else 3)
        # The ridge's falling face also touches the right-hand aggregate cells.
        expected_blocked = (4 if geometry == "ridge" else 2) if blocked else 0
        assert info["blocked_cells"] == expected_blocked
    if not blocked:
        assert costs[1][0, 0] == pytest.approx(costs[0][0, 0] * 0.5)


def test_explicit_roads_exclude_decals_and_keep_terrain_class(config):
    triangle = [[0, 0], [4, 0], [0, 4]]
    decal_triangle = [[4, 4], [8, 4], [4, 8]]
    roads = [{"name": "dirtroad", "triangles": [triangle]}]
    roads += [{"name": name, "triangles": [decal_triangle]} for name in
              ("STAIN", "decal", "parkinglot", "oilstain")]
    mask, kept, filtered = terrain.rasterize_roads(roads, 2, 2, 4.0)
    np.testing.assert_array_equal(mask, [[True, False], [False, False]])
    assert (kept, filtered) == (1, 4)
    elevation = np.zeros((5, 5))
    agg = terrain.aggregate(compute_features(elevation, 2.0, 6.0), elevation, 2, 2)
    cost, classes, _ = compute_cost(
        agg, np.zeros((2, 2), np.uint8), mask, np.ones((2, 2)),
        np.zeros((2, 2), bool), config, "infantry")
    np.testing.assert_array_equal(cost, [[0.5, 1], [1, 1]])
    assert np.all(classes == 1)


def test_boundary_water_does_not_confirm_isolated_below_sea_depression():
    elevation = np.full((7, 7), 10.0)
    elevation[0:3, 1] = -1.0
    elevation[4:6, 4:6] = -1.0
    expected = np.zeros((7, 7), bool)
    expected[0:3, 1] = True
    np.testing.assert_array_equal(confirmed_water_mask(elevation, 0.0), expected)


def test_flat_basin_is_candidate_but_flat_dry_field_is_not():
    basin = np.full((9, 9), 12.0)
    basin[2:7, 2:7] = 10.0
    slope = compute_features(basin, 1.0, 3.0)["slope_deg"]
    confirmed = confirmed_water_mask(basin, 0.0)
    candidate = candidate_water_mask(basin, slope, confirmed, 0.0, 1.0, 9.0, 1.0, 0.1)
    expected = np.zeros((9, 9), bool)
    expected[3:6, 3:6] = True
    # Keep this end-to-end assertion: a hand-supplied slope mask would hide
    # the equal-height border ring left by native central differences.
    np.testing.assert_array_equal(candidate, expected)
    assert not confirmed.any()
    dry = np.full((9, 9), 10.0)
    assert not candidate_water_mask(
        dry, np.zeros_like(dry), confirmed, 0.0, 1.0, 9.0, 1.0, 0.1).any()


def test_candidate_basin_area_threshold_and_flat_dry_field():
    elevation = np.full((7, 7), 12.0)
    elevation[2:5, 2:5] = 10.0
    # Isolate the component/area rule from the native-gradient integration above.
    slope = np.full((7, 7), 10.0)
    slope[2:5, 2:5] = 0.0
    confirmed = np.zeros((7, 7), bool)
    expected = np.zeros((7, 7), bool)
    expected[2:5, 2:5] = True
    np.testing.assert_array_equal(candidate_water_mask(
        elevation, slope, confirmed, 0.0, 1.0, 36.0, 4.0, 0.1), expected)
    assert not candidate_water_mask(
        elevation, slope, confirmed, 0.0, 1.0, 37.0, 4.0, 0.1).any()
    assert not candidate_water_mask(
        np.full((7, 7), 10.0), np.zeros((7, 7)), confirmed,
        0.0, 1.0, 36.0, 4.0, 0.1).any()


def test_water_static_and_dense_vegetation_raise_cost_without_blocking(config):
    elevation = np.zeros((5, 5))
    agg = terrain.aggregate(compute_features(elevation, 2.0, 6.0), elevation, 2, 2)
    static, counts = terrain.static_multiplier(
        [{"class": "building", "x": 2, "y": 2}], 2, 2, 4.0, {"building": 4}, 5)
    dense, dense_count = terrain.vegetation_density(
        [{"x": 2, "y": 2}, {"x": 2, "y": 2}], 2, 2, 4.0, 0.0, 2)
    assert counts == {"building": 1}
    assert static[0, 0] == 5
    assert dense_count == 1 and dense[0, 0]
    water = np.array([[1, 0], [0, 2]], dtype=np.uint8)
    cost, classes, info = compute_cost(
        agg, water, np.zeros((2, 2), bool), static, dense, config, "infantry")
    np.testing.assert_array_equal(cost, [[80, 5], [5, 1]])
    assert np.isfinite(cost).all() and (cost > 0).all()
    np.testing.assert_array_equal(classes, [[5, 3], [3, 6]])
    assert info["blocked_cells"] == 0


@pytest.mark.parametrize("state,names,has_client,decoded,referenced", [
    ("no_road_definitions", [], False, 0, 0),
    ("no_road_definitions", ["decal", "oilstain"], False, 0, 0),
    ("missing_client_zip", ["road_a"], False, 0, 1),
    ("missing_mesh_records", ["road_a"], True, 0, 1),
    ("partial", ["road_a", "road_b"], True, 1, 2),
    ("complete", ["road_a", "decal"], True, 1, 1),
])
def test_road_coverage_reads_real_zip_archives(
        tmp_path, monkeypatch, state, names, has_client, decoded, referenced):
    monkeypatch.setattr(terrain, "RAW", tmp_path)
    map_dir = tmp_path / "demo"
    map_dir.mkdir()
    with zipfile.ZipFile(map_dir / "server.zip", "w") as archive:
        archive.writestr("Roads/CompiledRoads.con", "\n".join(
            "Object.create " + name for name in names))
    if has_client:
        with zipfile.ZipFile(map_dir / "client.zip", "w") as archive:
            archive.writestr("fixture.txt", "coverage consumes decoded count, not mesh bytes")
    result = terrain.road_coverage("demo", decoded)
    assert result["state"] == state
    assert result["referenced_segments"] == referenced


@pytest.mark.parametrize("spacing", [2.0, 8.0])
@pytest.mark.parametrize("road_references", [False, True])
def test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes(
        tmp_path, monkeypatch, config, spacing, road_references):
    output = tmp_path / "processed"
    raw = tmp_path / "raw"
    map_dir = output / "demo"
    map_dir.mkdir(parents=True)
    (raw / "demo").mkdir(parents=True)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="ascii")
    monkeypatch.setattr(terrain, "OUT", output)
    monkeypatch.setattr(terrain, "RAW", raw)
    monkeypatch.setattr(terrain, "CONFIG_PATH", config_path)
    metadata = {"map_size": 8 * spacing, "height_scale": 163.8375, "sea_level_m": 0}
    (map_dir / "metadata.json").write_text(json.dumps(metadata), encoding="ascii")
    with gzip.open(map_dir / "heightmap.json.gz", "wt", encoding="ascii") as handle:
        json.dump({"resolution": 9, "data": [4000] * 81}, handle)
    (map_dir / "obstructions.json").write_text(
        json.dumps({"roads": [], "statics": [], "vegetation": []}), encoding="ascii")
    with zipfile.ZipFile(raw / "demo" / "server.zip", "w") as archive:
        archive.writestr("Roads/compiledroads.con",
                         "Object.create road_a" if road_references else "")
    assert terrain.process_map("demo", 1, 1, config)
    terrain_dir = map_dir / "terrain"
    first = {path.relative_to(terrain_dir).as_posix(): path.read_bytes()
             for path in terrain_dir.rglob("*") if path.is_file()}
    assert {"sidecar.json", "road_mask.bin", "water.bin",
            "infantry/cost.bin", "infantry/classes.bin", "infantry/sidecar.json"} <= set(first)
    sidecar = json.loads(first["sidecar.json"])
    assert set(sidecar["diagnostics"]) == {
        "slope_deg_mean", "slope_deg_max", "edge_rise_m_max", "edge_grade_max",
        "roughness_m_mean", "elevation_mean", "static_multiplier", "vegetation_dense"}
    cells = 8 if spacing == 8 else 4
    assert sidecar["grid"]["rows"] == sidecar["grid"]["cols"] == cells
    assert sidecar["grid"]["cell_size_m"] == max(4, spacing)
    assert sidecar["grid"]["source_spacing_m"] == spacing
    assert sidecar["grid"]["degraded_source_resolution"] == (spacing > 4)
    assert sidecar["roads"]["state"] == (
        "missing_client_zip" if road_references else "no_road_definitions")
    np.testing.assert_array_equal(np.frombuffer(first["infantry/cost.bin"], dtype="<f4"),
                                  np.ones(cells * cells))
    assert first["road_mask.bin"] == bytes(cells * cells)
    assert first["water.bin"] == bytes(cells * cells)
    assert first["infantry/classes.bin"] == bytes([1]) * (cells * cells)
    assert terrain.process_map("demo", 1, 1, config)
    second = {path.relative_to(terrain_dir).as_posix(): path.read_bytes()
              for path in terrain_dir.rglob("*") if path.is_file()}
    assert second == first


def test_raw_south_rows_reach_south_artifact_and_minimap(tmp_path, monkeypatch, config):
    """Guard the whole boundary: flip terrain once, never flip world-space roads.

    Raw row 0 is south; repository/image row 0 is north. Real-map orientation
    was cross-checked against gameplay object heights, not inferred from this
    synthetic fixture (see research-orientation-002.md).
    """
    from PIL import Image
    from terrain_artifact import load_terrain_artifact
    import render_terrain_qa as qa

    map_dir = tmp_path / "processed_maps" / "demo"
    map_dir.mkdir(parents=True)
    monkeypatch.setattr(terrain, "OUT", map_dir.parent)
    monkeypatch.setattr(terrain, "RAW", tmp_path / "raw")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="ascii")
    monkeypatch.setattr(terrain, "CONFIG_PATH", config_path)
    monkeypatch.setattr(qa, "ROOT", tmp_path)
    monkeypatch.setattr(qa, "OUTPUT", tmp_path / "qa")

    # Low southern shore, high northern plateau; no east/west symmetry assumption.
    samples = np.zeros((9, 9), dtype=np.uint16)
    samples[4:, :] = 10
    source = map_dir / "heightmap.json.gz"
    with gzip.open(source, "wt", encoding="ascii") as handle:
        json.dump({"resolution": 9, "data": samples.ravel().tolist()}, handle)
    source_bytes = source.read_bytes()
    (map_dir / "metadata.json").write_text(json.dumps({
        "map_size": 16, "height_scale": 65535, "sea_level_m": 1}), encoding="ascii")
    (map_dir / "obstructions.json").write_text(json.dumps({
        "roads": [{"name": "road", "triangles": [[[0, 0], [4, 0], [0, 4]]]}],
        "statics": [], "vegetation": []}), encoding="ascii")
    base_color = (40, 50, 60, 255)
    Image.new("RGBA", (160, 160), base_color).save(map_dir / "minimap.png")

    assert terrain.process_map("demo", 1, 1, config)
    artifact = load_terrain_artifact(map_dir / "terrain")
    np.testing.assert_array_equal(artifact["diagnostics"]["elevation_mean"][:, 0],
                                  [10, 10, 5, 0])
    np.testing.assert_array_equal(artifact["water"][:, 0], [0, 0, 1, 1])
    assert artifact["road_mask"][0, 0] == 1
    assert artifact["road_mask"].sum() == 1
    assert artifact["costs"][0, 0] == pytest.approx(0.5)
    assert artifact["costs"][-1, 0] == pytest.approx(8)
    assert artifact["classes"][0, 0] == 1
    assert artifact["classes"][-1, 0] == 5
    assert artifact["grid"]["heightmap_orientation"] == (
        "raw rows vertically flipped once into minimap/image coordinates")
    assert source.read_bytes() == source_bytes

    qa.render("demo")
    with Image.open(qa.OUTPUT / "qa_terrain_demo.png") as image:
        # Interior pixels avoid the coverage label and road outlines.
        for pixel, category in (((20, 35), 1), ((20, 140), 5)):
            expected = Image.alpha_composite(
                Image.new("RGBA", (1, 1), base_color),
                Image.new("RGBA", (1, 1), qa.COLORS[category])).getpixel((0, 0))
            assert image.getpixel(pixel) == expected