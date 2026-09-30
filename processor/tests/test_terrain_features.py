import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from terrain_features import (detrended_roughness, edge_features,
                              load_heightmap, resolve_roughness_window,
                              sample_spacing, samples_to_meters, slope_features,
                              to_repository_orientation)


def test_flat_plane_has_zero_slope_and_roughness():
    elevation = np.full((7, 7), 12.0)
    slope, angle = slope_features(elevation, 2.0)
    assert np.allclose(slope, 0)
    assert np.allclose(angle, 0)
    assert np.allclose(detrended_roughness(elevation, 2.0, 3), 0)


def test_analytic_ramp_is_orientation_independent_and_detrended():
    axis = np.arange(7, dtype=float) * 2.0
    for elevation in (np.tile(axis[:, None] * 0.5, (1, 7)),
                      np.tile(axis[None, :] * 0.5, (7, 1))):
        slope, _ = slope_features(elevation, 2.0)
        assert np.allclose(slope, 0.5)
        assert np.allclose(detrended_roughness(elevation, 2.0, 3), 0)


def test_step_survives_edge_feature_and_diagonal_distance():
    elevation = np.zeros((5, 5))
    elevation[2:, 2:] = 3.0
    rise, grade = edge_features(elevation, 2.0)
    assert rise.max() == 3.0
    assert grade[1, 1] == pytest.approx(3.0 / (2.0 * np.sqrt(2.0)))


def test_boundary_gradient_is_one_sided_not_zero_padded():
    elevation = np.arange(25, dtype=float).reshape(5, 5)
    slope, _ = slope_features(elevation, 1.0)
    assert slope[0, 0] == pytest.approx(np.sqrt(26.0))
    assert slope[-1, -1] == pytest.approx(np.sqrt(26.0))


def test_map_relative_roughness_window_is_rejected():
    with pytest.raises(ValueError, match="feature-scale bound"):
        resolve_roughness_window(64.0, 2.0)


def test_authoritative_conversion_and_compressed_row_major_heightmap(tmp_path):
    metadata = {"map_size": 1024, "height_scale": 163.8375}
    (tmp_path / "metadata.json").write_text(json.dumps(metadata), encoding="ascii")
    values = [0, 1, 32768, 65535]
    with gzip.open(tmp_path / "heightmap.json.gz", "wt", encoding="ascii") as handle:
        json.dump({"resolution": 2, "data": values}, handle)
    samples, loaded_metadata = load_heightmap(tmp_path)
    assert loaded_metadata == metadata
    assert samples.dtype == np.uint16
    np.testing.assert_array_equal(samples, [[0, 1], [32768, 65535]])
    meters = samples_to_meters(samples, loaded_metadata["height_scale"])
    np.testing.assert_allclose(
        meters, [[0, 0.0025], [81.92, 163.8375]], rtol=0, atol=1e-12)
    assert sample_spacing(1024, 513) == 2.0
    assert sample_spacing(1024, 257) == 4.0


def test_repository_orientation_flips_asymmetric_north_south_marker():
    raw = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    np.testing.assert_array_equal(to_repository_orientation(raw), [[3, 4], [1, 2]])


def test_cardinal_and_diagonal_edges_use_distinct_distances_without_wrap():
    elevation = np.zeros((5, 5))
    elevation[2, 2] = 3.0
    rise, grade = edge_features(elevation, 2.0)
    assert rise[2, 1] == rise[1, 1] == 3.0
    assert grade[2, 1] == pytest.approx(1.5)
    assert grade[1, 1] == pytest.approx(1.5 / np.sqrt(2.0))
    elevation = np.zeros((5, 5))
    elevation[0, 0] = 3.0
    rise, grade = edge_features(elevation, 2.0)
    assert np.all(rise[-1, :] == 0)
    assert np.all(grade[:, -1] == 0)


def test_bump_increases_roughness_over_smooth_tilted_plane():
    row, col = np.indices((7, 7), dtype=float)
    plane = 0.5 * row + 0.25 * col
    bumpy = plane.copy()
    bumpy[3, 3] += 3.0
    assert detrended_roughness(plane, 2.0, 3)[3, 3] == pytest.approx(0, abs=1e-12)
    assert detrended_roughness(bumpy, 2.0, 3)[3, 3] == pytest.approx(np.sqrt(8.0 / 9.0))