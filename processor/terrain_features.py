#!/usr/bin/env python3
"""Terrain feature extraction from processed heightmaps (design D1-D3).

Known ceiling: features are computed at native heightmap resolution (about 2-4 m
per sample). Curbs, foliage, and sub-sample ledges cannot be represented at this
resolution; the output sidecar records source spacing so consumers can see the
limit. Upgrade path: collision-mesh or navmesh parsing for geometry-complete
features.
"""
import gzip
import json
import math
from pathlib import Path

import numpy as np

# Feature-scale bound for the roughness window (D3): roads are ~6-10 m wide, so
# a window much larger than this smooths away the very features being measured.
# Map-width-relative windows (e.g. map_size / 32 = 32-128 m) are rejected.
MAX_ROUGHNESS_WINDOW_M = 24.0


def load_heightmap(map_dir):
    """Return (uint16 2D ndarray, metadata dict) for a processed map directory."""
    map_dir = Path(map_dir)
    metadata = json.loads((map_dir / "metadata.json").read_text(encoding="utf-8"))
    compressed = map_dir / "heightmap.json.gz"
    plain = map_dir / "heightmap.json"
    if compressed.exists():
        with gzip.open(compressed, "rt", encoding="ascii") as handle:
            payload = json.load(handle)
    elif plain.exists():
        payload = json.loads(plain.read_text(encoding="ascii"))
    else:
        raise FileNotFoundError("no heightmap.json[.gz] in " + str(map_dir))
    resolution = int(payload["resolution"])
    grid = np.asarray(payload["data"], dtype=np.uint16).reshape(resolution, resolution)
    return grid, metadata


def samples_to_meters(samples, height_scale):
    """Raw 16-bit samples to elevation meters. The 65535.0 divisor is fixed
    repository convention (AGENTS.md); never change it."""
    return samples.astype(np.float64) / 65535.0 * float(height_scale)


def to_repository_orientation(array):
    """Convert raw BF2 heightmap rows to the repository/image north-up plane.

    The raw heightmap row order is vertically opposite to the decoded textured
    minimap. Keep heightmap JSON unchanged as source data; terrain consumers use
    this single boundary transform before deriving world-space features.
    """
    if np.asarray(array).ndim != 2:
        raise ValueError("heightmap orientation transform requires a 2-D array")
    return np.flipud(array)


def sample_spacing(map_size, resolution):
    """Horizontal spacing in meters; samples sit on both world edges."""
    return float(map_size) / (int(resolution) - 1)


def slope_features(elevation, spacing):
    """Central-difference slope (D1).

    np.gradient(edge_order=1) is the documented numpy idiom for interior central
    differences with one-sided differences at the boundary, so no invented
    elevation padding is introduced. Returns (magnitude m/m, angle degrees).
    """
    d_row, d_col = np.gradient(elevation, spacing, edge_order=1)
    magnitude = np.hypot(d_row, d_col)
    return magnitude, np.degrees(np.arctan(magnitude))


def edge_features(elevation, spacing):
    """Per-sample max absolute rise (m) and max grade (m/m) to neighbors (D2).

    All 8 neighbors are considered; diagonal edges use spacing*sqrt(2). Boundary
    samples compare only against neighbors that exist (np.roll wraps the map
    edge, so wrapped comparisons are masked out). Kept separate from average
    slope so a one-sample ledge survives later aggregation (D7).
    """
    rise = np.zeros_like(elevation)
    grade = np.zeros_like(elevation)
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            distance = spacing * (math.sqrt(2.0) if d_row and d_col else 1.0)
            shifted = np.roll(elevation, (d_row, d_col), axis=(0, 1))
            diff = np.abs(elevation - shifted)
            if d_row == 1:
                diff[0, :] = 0.0
            elif d_row == -1:
                diff[-1, :] = 0.0
            if d_col == 1:
                diff[:, 0] = 0.0
            elif d_col == -1:
                diff[:, -1] = 0.0
            rise = np.maximum(rise, diff)
            grade = np.maximum(grade, diff / distance)
    return rise, grade


def resolve_roughness_window(window_m, spacing):
    """Convert a metric roughness window to an odd sample count (D3).

    Rejects even/tiny windows and anything beyond the feature-scale bound; this
    is where map-width-relative window requests fail loudly (spec: Metric-scale
    roughness / Map-width window rejected).
    """
    samples = int(round(float(window_m) / spacing))
    if samples % 2 == 0:
        samples += 1
    if samples < 3:
        samples = 3
    if samples * spacing > MAX_ROUGHNESS_WINDOW_M:
        raise ValueError(
            "roughness window %.1f m exceeds the %.1f m feature-scale bound; "
            "map-width-relative windows are rejected (D3)"
            % (samples * spacing, MAX_ROUGHNESS_WINDOW_M))
    return samples


def detrended_roughness(elevation, spacing, window):
    """Local least-squares plane residual RMS in meters (D3).

    Concept from the ETH traversability_estimation roughness filter (see
    research-traversability-methods-001.md): fit a plane z = a*x + b*y + c per
    local window and measure what the plane cannot explain. For a uniform odd
    window the least-squares fit has a closed form (c = window mean; a, b from
    offset-weighted sums), so a smooth tilted plane scores ~0 while bumps around
    the local grade score high. Boundary cells replicate the nearest interior
    value; this is recorded in the output sidecar.

    Memory note: the sliding-window temporaries scale with window^2; for a 5x5
    window on a 1025x1025 map one residual tensor alone is about 199 MiB and the
    total peak is higher (unmeasured). Acceptable for an offline maintainer
    pipeline; do not call this from anything user-facing.
    """
    if window % 2 == 0 or window < 3:
        raise ValueError("roughness window must be odd and >= 3")
    if window * spacing > MAX_ROUGHNESS_WINDOW_M:
        raise ValueError(
            "roughness window %.1f m exceeds the %.1f m feature-scale bound (D3)"
            % (window * spacing, MAX_ROUGHNESS_WINDOW_M))
    from numpy.lib.stride_tricks import sliding_window_view
    offsets = (np.arange(window) - window // 2) * spacing
    x_matrix = np.tile(offsets, (window, 1))
    y_matrix = np.tile(offsets[:, None], (1, window))
    sxx = float((x_matrix ** 2).sum())
    syy = float((y_matrix ** 2).sum())
    windows = sliding_window_view(elevation, (window, window))
    center = windows.mean(axis=(-2, -1))
    a_coef = np.tensordot(windows, x_matrix, axes=([2, 3], [0, 1])) / sxx
    b_coef = np.tensordot(windows, y_matrix, axes=([2, 3], [0, 1])) / syy
    residual = windows - (center[..., None, None]
                          + a_coef[..., None, None] * x_matrix
                          + b_coef[..., None, None] * y_matrix)
    roughness = np.sqrt((residual ** 2).mean(axis=(-2, -1)))
    pad = window // 2
    return np.pad(roughness, pad, mode="edge")


def compute_features(elevation, spacing, roughness_window_m):
    """Convenience bundle: all native-resolution features in one dict."""
    window = resolve_roughness_window(roughness_window_m, spacing)
    slope_mag, slope_deg = slope_features(elevation, spacing)
    edge_rise, edge_grade = edge_features(elevation, spacing)
    roughness = detrended_roughness(elevation, spacing, window)
    return {
        "slope_mag": slope_mag,
        "slope_deg": slope_deg,
        "edge_rise_m": edge_rise,
        "edge_grade": edge_grade,
        "roughness_m": roughness,
        "roughness_window_samples": window,
    }
