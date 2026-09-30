import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import build_flow_fields as bff
from build_flow_fields import (QUANT_UNREACHABLE, UNREACHABLE, layer_team_sources,
                               pick_vehicle_speed, prepare_sources, quantize_field,
                               sample_quantized_arrival,
                               solve_field, world_to_cell)

CELL = 4.0
SPEED = 4.0


def flat_costs(rows=64, cols=64):
    return np.ones((rows, cols), dtype=np.float32)


def test_flat_uniform_frontier_is_circle_within_one_cell():
    # Radius 10 cells keeps the 8-connected octagon approximation error
    # (~8% of radius) under the 1-cell tolerance required by the spec.
    costs = flat_costs()
    field = solve_field(costs, [(32, 32)], SPEED, CELL)
    time_s = 10.0  # frontier radius = 4 m/s * 10 s = 40 m = 10 cells
    rows, cols = np.indices(costs.shape)
    dist = np.hypot(rows - 32, cols - 32)
    assert (field[dist <= 9] >= 0).all()
    assert (field[dist <= 9] <= time_s).all()
    reached = field[(field >= 0) & (field <= time_s)]
    assert (dist[(field >= 0) & (field <= time_s)] <= 11).all()
    # Axis cell exactly 10 cells away: 40 m / 4 m/s = 10 s, tolerance 1 cell-time.
    assert abs(field[32, 42] - 10.0) <= CELL / SPEED


def test_ridge_forces_detour_not_straight_line():
    costs = flat_costs()
    costs[16:49, 40] = -1.0  # blocked ridge with gaps at both ends
    field = solve_field(costs, [(32, 32)], SPEED, CELL)
    straight_s = 16 * CELL / SPEED  # 16 cells straight through the wall
    assert field[32, 48] >= 0  # reached via detour
    assert field[32, 48] > straight_s * 1.5


def test_water_is_heavy_cost_never_blocked():
    costs = flat_costs()
    costs[:, 36:40] = 10.0  # water band spanning every row: no detour possible
    field = solve_field(costs, [(32, 32)], SPEED, CELL)
    assert field[32, 44] >= 0  # D7: water is crossed, never a hard wall
    clear_s = 12 * CELL / SPEED
    # Path crosses 4 water cells at 10x: expect roughly (32 + 160) / 4 = 48 s.
    assert field[32, 44] > clear_s * 3


def test_building_is_heavy_cost_never_blocked():
    costs = flat_costs()
    costs[:, 36:40] = 5.0  # building band, lighter than water but still heavy
    field = solve_field(costs, [(32, 32)], SPEED, CELL)
    assert field[32, 44] >= 0
    clear_s = 12 * CELL / SPEED
    assert field[32, 44] > clear_s * 1.5


def test_fully_walled_region_is_unreachable_sentinel():
    costs = flat_costs()
    costs[50:55, 50:55] = 1.0
    costs[49:56, 49] = -1.0
    costs[49:56, 55] = -1.0
    costs[49, 49:56] = -1.0
    costs[55, 49:56] = -1.0
    field = solve_field(costs, [(32, 32)], SPEED, CELL)
    assert field[52, 52] == UNREACHABLE
    assert field[32, 32] == 0.0


def test_blocked_source_is_nudged_or_dropped():
    costs = flat_costs()
    costs[10, 10] = -1.0
    cells, dropped = prepare_sources(costs, [(10 * CELL + 1, 10 * CELL + 1)], CELL)
    assert dropped == 0
    assert cells and costs[cells[0]] > 0
    island = np.full((8, 8), -1.0, dtype=np.float32)
    cells, dropped = prepare_sources(island, [(16, 16)], CELL)
    assert cells == [] and dropped == 1


def test_world_to_cell_clamps_to_grid():
    assert world_to_cell(-5, 10, 64, 64, CELL) == (2, 0)
    assert world_to_cell(10, 99999, 64, 64, CELL) == (63, 2)


def test_quantize_field_sentinel_and_monotonic():
    field = np.array([[0.0, 10.0, 100.0], [UNREACHABLE, 5000.0, 1.0]], dtype=np.float32)
    quant, quantum = quantize_field(field)
    assert quant[1, 0] == QUANT_UNREACHABLE
    assert quantum >= 1
    assert quant[0, 0] == 0
    assert quant[0, 1] < quant[0, 2]
    assert quant[1, 1] <= 254  # capped, never collides with sentinel


def test_sample_quantized_arrival_uses_shipped_byte_value():
    grid = np.full((8, 8), QUANT_UNREACHABLE, dtype=np.uint8)
    grid[4, 4] = 7
    assert sample_quantized_arrival(grid, 15, 4 * CELL + 1,
                                   4 * CELL + 1, CELL) == 105.0


def test_sample_quantized_arrival_preserves_unreachable_representation():
    grid = np.full((8, 8), QUANT_UNREACHABLE, dtype=np.uint8)
    assert sample_quantized_arrival(grid, 15, 4 * CELL,
                                   4 * CELL, CELL) is None


def test_layer_team_sources_follow_cp_initial_owner():
    layer = {
        "control_points": [
            {"id": 1, "name": "base_a", "team": 1, "x": 10.0, "y": 10.0},
            {"id": 2, "name": "mid", "team": 0, "x": 50.0, "y": 50.0},
        ],
        "spawn_points": [
            {"name": "sp_a", "group": 1, "control_point_id": 1, "x": 12.0, "y": 12.0},
            {"name": "sp_mid", "group": 1, "control_point_id": 2, "x": 52.0, "y": 52.0},
        ],
        "vehicle_spawners": [
            {"name": "vs_a", "team": 0, "control_point_id": 1,
             "templates": {"1": "trk_a", "2": "trk_b"}, "x": 14.0, "y": 14.0},
        ],
    }
    infantry, vehicles = layer_team_sources(layer)
    assert infantry[1] == [(12.0, 12.0)]
    assert infantry[2] == []  # neutral CP spawn skipped
    assert vehicles[1] == [(14.0, 14.0, "trk_a")]  # inherits CP owner, picks team template
    assert vehicles[2] == []


def test_pick_vehicle_speed_median_and_fallback():
    vehicles = {"fast": {"max_speed_ms": 30.0}, "slow": {"max_speed_ms": 10.0}}
    speed, prov = pick_vehicle_speed(["fast", "slow", "missing"], vehicles, "test")
    assert speed == 20.0  # median of 30, 10, found-average 20
    assert "missing" in prov
    speed, prov = pick_vehicle_speed(["nope"], vehicles, "test")
    assert speed is None


# ---------------------------------------------------------------------------
# Parallel driver (--workers): processes, not threads (GIL); outputs must be
# byte-identical to the sequential path.
# ---------------------------------------------------------------------------

def _write_fixture_map(root, name, rows=16, cols=16):
    """Minimal valid map: terrain artifact contract + one two-team layer."""
    map_dir = root / name
    terrain = map_dir / "terrain"
    for profile in ("infantry", "wheeled_vehicle"):
        (terrain / profile).mkdir(parents=True)
        np.ones((rows, cols), dtype="<f4").tofile(terrain / profile / "cost.bin")
        np.zeros((rows, cols), dtype="u1").tofile(terrain / profile / "classes.bin")
    np.zeros((rows, cols), dtype="u1").tofile(terrain / "road_mask.bin")
    np.zeros((rows, cols), dtype="u1").tofile(terrain / "water.bin")
    (terrain / "sidecar.json").write_text(json.dumps({
        "format_version": "1.0",
        "artifact": "terrain_cost",
        "grid": {"rows": rows, "cols": cols, "cell_size_m": 4.0,
                 "origin": "top-left; x east, y south; repo world meters"},
        "blocked_sentinel": -1.0,
        "profiles": ["infantry", "wheeled_vehicle"],
        "roads": {},
        "provenance": {},
        "config": {},
    }), encoding="ascii")
    (map_dir / "gamelayers.json").write_text(json.dumps({
        "map_name": name,
        "format_version": "1.0",
        "layers": [{
            "mode": "gpm_cq", "size": 64,
            "control_points": [
                {"id": 1, "name": "alpha", "team": 1, "x": 8.0, "y": 8.0},
                {"id": 2, "name": "bravo", "team": 2, "x": 56.0, "y": 56.0},
            ],
            "spawn_points": [
                {"name": "s1", "group": 1, "control_point_id": 1, "x": 8.0, "y": 8.0},
                {"name": "s2", "group": 1, "control_point_id": 2, "x": 56.0, "y": 56.0},
            ],
            "vehicle_spawners": [],
        }],
    }), encoding="ascii")


def _hash_tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def test_parallel_workers_match_sequential_bytes(tmp_path, monkeypatch):
    for name in ("fixture_alpha", "fixture_beta"):
        _write_fixture_map(tmp_path, name)
    # Spawned workers are fresh interpreters: they read PR_FLOW_OUT from the
    # inherited environment; the sequential path uses the module constant.
    monkeypatch.setenv("PR_FLOW_OUT", str(tmp_path))
    monkeypatch.setattr(bff, "OUT", tmp_path)

    monkeypatch.setattr(sys, "argv", ["build_flow_fields.py", "--workers", "1",
                                      "fixture_alpha", "fixture_beta"])
    assert bff.main() == 0
    serial = _hash_tree(tmp_path)
    assert any("flow" in rel for rel in serial)  # fixture actually produced fields
    for name in ("fixture_alpha", "fixture_beta"):
        shutil.rmtree(tmp_path / name / "flow")

    monkeypatch.setattr(sys, "argv", ["build_flow_fields.py", "--workers", "2",
                                      "fixture_alpha", "fixture_beta"])
    assert bff.main() == 0
    assert _hash_tree(tmp_path) == serial


def test_workers_must_be_positive(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["build_flow_fields.py", "--workers", "0"])
    with pytest.raises(SystemExit):
        bff.main()
