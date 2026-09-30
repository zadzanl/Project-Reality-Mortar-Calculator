#!/usr/bin/env python3
"""Build per-map terrain movement-cost grids (design D4-D7; tasks 3.1-3.8, 4.1-4.5).

Reads processed heightmaps (via terrain_features), obstruction extraction, and
terrain_params.json; writes processed_maps/<map>/terrain/ artifacts consumed by
the later offline opening-flow solver. Nothing here runs in the browser.

Known ceiling: static-object footprints are fixed-radius proxies from a name
heuristic (no collision meshes), vegetation is a per-cell density proxy, and
candidate inland water is a geometric heuristic (flat basin above sea level).
All three are recorded in the sidecar. Upgrade path: collision-mesh or navmesh
parsing, curated per-map water patches.

Output layout per map (loader contract, task 6.1):
  terrain/sidecar.json            shared: grid shape, origin, cell size, units,
                                  coverage states, config values + sha256,
                                  provenance, degraded-resolution flags,
                                  reserved surface_material field
  terrain/road_mask.bin           uint8 rows*cols, 1 = explicit road member
  terrain/water.bin               uint8: 0 none, 1 confirmed, 2 candidate
  terrain/<profile>/cost.bin      float32 little-endian rows*cols, -1.0 blocked
  terrain/<profile>/classes.bin   uint8 diagnostic class per cell
  terrain/<profile>/sidecar.json  profile thresholds, blocked count, histogram

Sidecars carry no timestamps: identical inputs must produce byte-for-byte
identical artifacts (spec: Deterministic terrain artifacts).
"""
import hashlib
import json
import math
import re
import sys
import zipfile
from collections import deque
from pathlib import Path

import numpy as np

from terrain_features import (MAX_ROUGHNESS_WINDOW_M, compute_features,
                              load_heightmap, sample_spacing, samples_to_meters,
                              to_repository_orientation)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_map_data"
OUT = ROOT / "processed_maps"
CONFIG_PATH = Path(__file__).resolve().parent / "terrain_params.json"
EXCLUDED = {"the_falklands"}
BLOCKED = -1.0

# Decal-class segments are surface decorations, not drivable geometry (3.8).
DECAL_RE = re.compile(r"stain|decal|parkinglot|oilstain", re.I)

CLASS_NAMES = {
    0: "unknown",
    1: "smooth_traversable",
    2: "rough_traversable",
    3: "slow",
    4: "extreme_slope",
    5: "water",
    6: "water_candidate",
}
WATER_NONE = 0
WATER_CONFIRMED = 1
WATER_CANDIDATE = 2


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def config_value(config, *keys):
    node = config
    for key in keys:
        node = node[key]
    return node["value"]


def grid_shape(map_size, spacing, cell_size_m):
    """Simulation grid geometry (3.2, 3.6). Never oversample a coarse source:
    if the heightmap spacing exceeds the requested cell size, the grid runs at
    source spacing and the sidecar records degraded_source_resolution."""
    cell_samples = max(1, int(round(cell_size_m / spacing)))
    resolution = int(round(map_size / spacing)) + 1
    cells = (resolution - 1) // cell_samples
    remainder_samples = (resolution - 1) - cells * cell_samples
    return {
        "cell_samples": cell_samples,
        "cells": cells,
        "cell_m": cell_samples * spacing,
        "remainder_samples": remainder_samples,
        "degraded": spacing > cell_size_m,
    }


def aggregate(features, elevation, cells, cell_samples):
    """Block-reduce native features to simulation cells (3.2, D7).

    Ordinary signals are averaged; slope and edge hazards keep their MAXIMUM so
    a narrow ledge cannot be averaged away. The final partial row/column of
    native samples is cropped and recorded in the sidecar.
    """
    limit = cells * cell_samples

    def reduce(array, how):
        blocks = array[:limit, :limit].reshape(cells, cell_samples, cells, cell_samples)
        return blocks.mean(axis=(1, 3)) if how == "mean" else blocks.max(axis=(1, 3))

    aggregated = {
        "slope_deg_mean": reduce(features["slope_deg"], "mean"),
        "slope_deg_max": reduce(features["slope_deg"], "max"),
        "edge_rise_m_max": reduce(features["edge_rise_m"], "max"),
        "edge_grade_max": reduce(features["edge_grade"], "max"),
        "elevation_mean": reduce(elevation, "mean"),
    }
    # Missing roughness means unmeasured coarse-source evidence, never zero.
    if features["roughness_m"] is not None:
        aggregated["roughness_m_mean"] = reduce(features["roughness_m"], "mean")
    return aggregated


def confirmed_water_mask(elevation, sea_level_m):
    """Below-sea-level cells connected to the map boundary (4.1, D6).

    Boundary connection distinguishes the sea from below-sea-level inland
    depressions, which are NOT promoted to confirmed water by elevation alone.
    """
    below = elevation <= sea_level_m
    rows, cols = below.shape
    connected = np.zeros_like(below)
    queue = deque()
    for col in range(cols):
        for row in (0, rows - 1):
            if below[row, col] and not connected[row, col]:
                connected[row, col] = True
                queue.append((row, col))
    for row in range(rows):
        for col in (0, cols - 1):
            if below[row, col] and not connected[row, col]:
                connected[row, col] = True
                queue.append((row, col))
    while queue:
        row, col = queue.popleft()
        for d_row, d_col in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n_row, n_col = row + d_row, col + d_col
            if (0 <= n_row < rows and 0 <= n_col < cols
                    and below[n_row, n_col] and not connected[n_row, n_col]):
                connected[n_row, n_col] = True
                queue.append((n_row, n_col))
    return connected


def candidate_water_mask(elevation, slope_deg, confirmed, sea_level_m,
                         flat_epsilon_deg, min_area_m2, sample_area_m2,
                         basin_margin_m):
    """Flat inland basins above sea level (4.2, D6): candidates only, never
    promoted by flatness alone. A region must be flat, above sea level, not
    confirmed water, at least min_area, and a local basin: its mean elevation
    must sit basin_margin_m BELOW its two-sample border mean. The second ring
    looks past the equal-height shoulder excluded by central differences.
    This is candidate evidence, not a hydrological fill or a water designation.
    The margin keeps
    noise-flat plains and deserts from being flagged as water candidates.
    """
    flat = (slope_deg < flat_epsilon_deg) & (elevation > sea_level_m) & ~confirmed
    rows, cols = flat.shape
    visited = np.zeros_like(flat)
    candidate = np.zeros_like(flat)
    for r_start, c_start in zip(*np.nonzero(flat)):
        if visited[r_start, c_start]:
            continue
        region = []
        border = set()
        queue = deque([(r_start, c_start)])
        visited[r_start, c_start] = True
        while queue:
            row, col = queue.popleft()
            region.append((row, col))
            for d_row, d_col in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n_row, n_col = row + d_row, col + d_col
                if not (0 <= n_row < rows and 0 <= n_col < cols):
                    continue
                if flat[n_row, n_col]:
                    if not visited[n_row, n_col]:
                        visited[n_row, n_col] = True
                        queue.append((n_row, n_col))
                else:
                    border.add((n_row, n_col))
        if len(region) * sample_area_m2 < min_area_m2 or not border:
            continue
        region_set = set(region)
        outer_border = set(border)
        for row, col in border:
            for d_row, d_col in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = (row + d_row, col + d_col)
                if (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols
                        and neighbor not in region_set):
                    outer_border.add(neighbor)
        border_elevations = [elevation[r, c] for r, c in sorted(outer_border)]
        region_mean = sum(elevation[r, c] for r, c in region) / len(region)
        if region_mean < sum(border_elevations) / len(border_elevations) - basin_margin_m:
            for row, col in region:
                candidate[row, col] = True
    return candidate


def rasterize_roads(roads, rows, cols, cell_m):
    """Rasterize explicit road triangles to a cell mask (3.3). Decal-class
    segments are filtered first (3.8). Low-slope non-road cells are never
    promoted to road here; membership comes only from decoded geometry.
    Returns (mask, kept_segments, filtered_decal_segments)."""
    mask = np.zeros((rows, cols), dtype=bool)
    kept = 0
    filtered = 0
    for road in roads:
        if DECAL_RE.search(road.get("name", "")):
            filtered += 1
            continue
        kept += 1
        for triangle in road["triangles"]:
            pts = np.asarray(triangle, dtype=np.float64)
            if pts.shape != (3, 2) or not np.isfinite(pts).all():
                raise ValueError("road triangle must contain three finite x/y points")
            a, b, c = pts
            if abs((b[0] - a[0]) * (c[1] - a[1])
                   - (b[1] - a[1]) * (c[0] - a[0])) < 1e-12:
                continue
            col_f = pts[:, 0] / cell_m
            row_f = pts[:, 1] / cell_m
            c0 = max(0, int(math.floor(col_f.min())))
            c1 = min(cols - 1, int(math.floor(col_f.max())))
            r0 = max(0, int(math.floor(row_f.min())))
            r1 = min(rows - 1, int(math.floor(row_f.max())))
            if c1 < c0 or r1 < r0:
                continue
            cx = (np.arange(c0, c1 + 1) + 0.5) * cell_m
            cy = (np.arange(r0, r1 + 1) + 0.5) * cell_m
            gx, gy = np.meshgrid(cx, cy)
            # Edge-function containment: a point is inside when all three
            # cross products share the triangle's winding sign.
            a, b, c = pts
            d1 = (gx - a[0]) * (b[1] - a[1]) - (gy - a[1]) * (b[0] - a[0])
            d2 = (gx - b[0]) * (c[1] - b[1]) - (gy - b[1]) * (c[0] - b[0])
            d3 = (gx - c[0]) * (a[1] - c[1]) - (gy - c[1]) * (a[0] - c[0])
            inside = ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
            mask[r0:r1 + 1, c0:c1 + 1] |= inside
    return mask, kept, filtered


def static_multiplier(statics, rows, cols, cell_m, footprints, building_mult):
    """Fixed-radius footprint proxy per heuristic class (3.4). Point placement
    is not a collision footprint (known ceiling); cells take the worst
    multiplier of any overlapping static. Passable always (D7 flow design)."""
    mult = np.ones((rows, cols))
    counts = {}
    for item in statics:
        kind = item["class"]
        if kind not in footprints:
            continue
        counts[kind] = counts.get(kind, 0) + 1
        radius_cells = footprints[kind] / cell_m
        c_center = item["x"] / cell_m
        r_center = item["y"] / cell_m
        c0 = max(0, int(math.floor(c_center - radius_cells)))
        c1 = min(cols - 1, int(math.ceil(c_center + radius_cells)))
        r0 = max(0, int(math.floor(r_center - radius_cells)))
        r1 = min(rows - 1, int(math.ceil(r_center + radius_cells)))
        if c1 < c0 or r1 < r0:
            continue
        cy, cx = np.ogrid[r0:r1 + 1, c0:c1 + 1]
        inside = ((cx + 0.5 - c_center) ** 2 + (cy + 0.5 - r_center) ** 2) <= radius_cells ** 2
        region = mult[r0:r1 + 1, c0:c1 + 1]
        region[inside] = np.maximum(region[inside], building_mult)
    return mult, counts


def vegetation_density(vegetation, rows, cols, cell_m, radius_m, dense_count):
    """Density proxy per flow design D2: plants counted within radius_m of each
    cell (summed-area table), dense at or above dense_count. A radius is used
    because single 4 m cells almost never hold enough plants to mean 'forest'.
    Returns (dense mask, dense cell count)."""
    counts = np.zeros((rows, cols), dtype=np.float64)
    for plant in vegetation:
        col = int(plant["x"] // cell_m)
        row = int(plant["y"] // cell_m)
        if 0 <= row < rows and 0 <= col < cols:
            counts[row, col] += 1
    radius = int(round(radius_m / cell_m))
    integral = np.pad(counts, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    rows_idx = np.arange(rows)
    cols_idx = np.arange(cols)
    r0 = np.clip(rows_idx - radius, 0, rows)
    r1 = np.clip(rows_idx + radius + 1, 0, rows)
    c0 = np.clip(cols_idx - radius, 0, cols)
    c1 = np.clip(cols_idx + radius + 1, 0, cols)
    total = (integral[np.ix_(r1, c1)] - integral[np.ix_(r0, c1)]
             - integral[np.ix_(r1, c0)] + integral[np.ix_(r0, c0)])
    dense = total >= dense_count
    return dense, int(dense.sum())


def road_coverage(map_name, decoded_segments):
    """Explicit coverage states (4.3): a missing client archive must never look
    like 'this map has no roads'. Decal-class names are excluded from BOTH sides
    of the comparison: filtering decorations is not an extraction failure (3.8).
    """
    server = RAW / map_name / "server.zip"
    client = RAW / map_name / "client.zip"
    if not server.exists():
        return {"state": "no_server_zip", "referenced_segments": 0}
    with zipfile.ZipFile(server) as archive:
        road_text = next((n for n in archive.namelist()
                          if n.replace("\\", "/").lower().endswith("compiledroads.con")), None)
        referenced = 0
        if road_text:
            text = archive.read(road_text).decode("utf-8", errors="replace")
            names = re.findall(r"^\s*object\.create\s+(\S+)", text, re.I | re.M)
            referenced = sum(1 for name in names if not DECAL_RE.search(name))
    if referenced == 0:
        return {"state": "no_road_definitions", "referenced_segments": 0}
    if not client.exists():
        return {"state": "missing_client_zip", "referenced_segments": referenced}
    if decoded_segments == 0:
        return {"state": "missing_mesh_records", "referenced_segments": referenced}
    if decoded_segments < referenced:
        return {"state": "partial", "referenced_segments": referenced,
                "note": "some referenced meshes missing or undecodable"}
    return {"state": "complete", "referenced_segments": referenced}


def compute_cost(agg, water, road_mask, static_mult, vegetation_dense, config, profile_name):
    """Continuous cost per cell (D5): base * slope * roughness * water *
    obstruction * vegetation, road modifier on members only. The only default
    hard block is the profile's extreme slope/edge condition (3.5)."""
    profile = config["profiles"][profile_name]
    max_slope_deg = profile["max_slope_deg"]["value"]
    full_penalty_deg = profile["slope_full_penalty_deg"]["value"]
    step_max_m = profile["step_max_m"]["value"]
    slope_max_mult = config_value(config, "multipliers", "slope_max")
    road_mult = config_value(config, "multipliers", "road")
    water_mult = config_value(config, "multipliers", "water")
    candidate_mult = config_value(config, "multipliers", "water_candidate")
    vegetation_mult = config_value(config, "multipliers", "vegetation_dense")
    roughness_max = config_value(config, "multipliers", "roughness_max")
    roughness_ref = config_value(config, "grid", "roughness_ref_m")
    roughness_enabled = bool(config_value(config, "grid", "roughness_multiplier_enabled"))
    if roughness_enabled and "roughness_m_mean" not in agg:
        raise ValueError("roughness multiplier enabled but source is too coarse for bounded roughness")

    slope_mult = 1.0 + np.clip(agg["slope_deg_mean"] / full_penalty_deg, 0.0, 1.0) * (slope_max_mult - 1.0)
    if roughness_enabled:
        roughness_mult = 1.0 + np.clip(agg["roughness_m_mean"] / roughness_ref, 0.0, 1.0) * (roughness_max - 1.0)
    else:
        roughness_mult = np.ones_like(slope_mult)
    water_mult_grid = np.ones_like(slope_mult)
    water_mult_grid[water == WATER_CONFIRMED] = water_mult
    water_mult_grid[water == WATER_CANDIDATE] = candidate_mult
    vegetation_mult_grid = np.where(vegetation_dense, vegetation_mult, 1.0)

    cost = (slope_mult * roughness_mult * water_mult_grid
            * static_mult * vegetation_mult_grid)
    cost = np.where(road_mask, cost * road_mult, cost)

    # Hard block AFTER all modifiers: road membership never bypasses an
    # extreme slope or edge hazard (3.5).
    edge_limit = math.tan(math.radians(max_slope_deg))
    blocked = ((agg["slope_deg_max"] > max_slope_deg)
               | (agg["edge_grade_max"] > edge_limit))
    cost = np.where(blocked, BLOCKED, cost)

    classes = classify(agg, water, static_mult, blocked,
                       step_max_m=step_max_m,
                       smooth_slope_deg=config_value(config, "grid", "smooth_slope_deg"),
                       smooth_roughness_m=config_value(config, "grid", "smooth_roughness_m"),
                       full_penalty_deg=full_penalty_deg)
    return cost.astype(np.float32), classes, {
        "blocked_cells": int(blocked.sum()),
        "max_slope_deg": max_slope_deg,
        "slope_full_penalty_deg": full_penalty_deg,
        "step_max_m": step_max_m,
        "edge_grade_limit": edge_limit,
        "roughness_multiplier_enabled": roughness_enabled,
    }


def classify(agg, water, static_mult, blocked, step_max_m, smooth_slope_deg,
             smooth_roughness_m, full_penalty_deg):
    """Diagnostic terrain classes (D5). Road membership is a separate channel
    (road_mask.bin) so a cell's terrain class and road membership coexist
    (spec: Road and terrain coexist)."""
    if "roughness_m_mean" in agg:
        smooth = ((agg["slope_deg_mean"] <= smooth_slope_deg)
                  & (agg["roughness_m_mean"] <= smooth_roughness_m))
        classes = np.where(smooth, 1, 2).astype(np.uint8)
    else:
        # Neither smooth nor rough can be asserted from unmeasured roughness.
        classes = np.zeros(agg["slope_deg_mean"].shape, dtype=np.uint8)
    slow = ((static_mult > 1.0)
            | (agg["edge_rise_m_max"] > step_max_m)
            | (agg["slope_deg_mean"] > full_penalty_deg))
    classes[slow] = 3
    classes[water == WATER_CONFIRMED] = 5
    classes[water == WATER_CANDIDATE] = 6
    classes[blocked] = 4
    return classes


def write_artifacts(map_name, grid, water_mask, road_mask, roads_info, statics_counts,
                    vegetation_dense_count, costs, config, metadata, features,
                    diagnostics):
    """Write the artifact set (3.1). No timestamps: determinism is required."""
    terrain_dir = OUT / map_name / "terrain"
    terrain_dir.mkdir(parents=True, exist_ok=True)
    (terrain_dir / "road_mask.bin").write_bytes(road_mask.astype(np.uint8).tobytes())
    (terrain_dir / "water.bin").write_bytes(water_mask.astype(np.uint8).tobytes())
    diagnostic_info = {}
    for name, array in diagnostics.items():
        filename = name + ".bin"
        (terrain_dir / filename).write_bytes(array.astype("<f4").tobytes())
        diagnostic_info[name] = {
            "file": filename, "dtype": "<f4",
            "min": float(array.min()), "max": float(array.max()),
        }
    for profile_name, (cost, classes, profile_info) in costs.items():
        profile_dir = terrain_dir / profile_name
        profile_dir.mkdir(exist_ok=True)
        (profile_dir / "cost.bin").write_bytes(cost.astype("<f4").tobytes())
        (profile_dir / "classes.bin").write_bytes(classes.tobytes())
        histogram = {CLASS_NAMES[k]: int((classes == k).sum()) for k in sorted(CLASS_NAMES)}
        profile_sidecar = {
            "profile": profile_name,
            "thresholds": profile_info,
            "class_histogram": histogram,
            "cost_stats": {
                "min": float(cost[cost != BLOCKED].min()) if (cost != BLOCKED).any() else None,
                "max": float(cost[cost != BLOCKED].max()) if (cost != BLOCKED).any() else None,
                "blocked_fraction": profile_info["blocked_cells"] / float(cost.size),
            },
        }
        (profile_dir / "sidecar.json").write_text(
            json.dumps(profile_sidecar, indent=2) + "\n", encoding="ascii")
    config_bytes = json.dumps(config, sort_keys=True, separators=(",", ":"),
                              allow_nan=False).encode("ascii")
    metadata_source = metadata.get("heightmap_size_source", "")
    metadata_verification = {
        "state": ("verified_from_heightdata_con"
                  if "heightdata.con" in metadata_source
                  else "unverified_legacy_metadata"),
        "source": metadata_source or "no authoritative heightdata.con provenance recorded",
    }
    sidecar = {
        "map_name": map_name,
        "format_version": "1.0",
        "artifact": "terrain_cost",
        "blocked_sentinel": BLOCKED,
        "diagnostics": diagnostic_info,
        "methods": {
            "elevation": "pixel_value / 65535.0 * height_scale",
            "height_scale_m": float(metadata["height_scale"]),
            "slope": "np.gradient edge_order=1; central interior, one-sided boundary",
            "edge": "eight neighbors; diagonal distance sqrt(2) * spacing",
            "roughness": "least-squares plane residual RMS; replicate interior at boundary",
            "roughness_status": features["roughness_status"],
            "roughness_requested_window_m": config_value(config, "grid", "roughness_window_m"),
            "roughness_max_window_m": MAX_ROUGHNESS_WINDOW_M,
            "roughness_window_samples": features["roughness_window_samples"],
            "roughness_window_m": (features["roughness_window_samples"] * features["spacing"]
                                   if features["roughness_window_samples"] is not None else None),
            "aggregation": "block mean ordinary signals; block max slope and edge hazards",
            "diagnostic_units": "slope degrees; edge rise/roughness/elevation meters; grade m/m; static multiplier; vegetation 0/1",
        },
        "grid": {
            "rows": grid["cells"],
            "cols": grid["cells"],
            "cell_size_m": grid["cell_m"],
            "map_size_m": float(metadata["map_size"]),
            "extent_m": grid["cells"] * grid["cell_m"],
            "requested_cell_size_m": config_value(config, "grid", "cell_size_m"),
            "origin": "top-left; x east, y south; repo world meters",
            "heightmap_orientation": "raw rows vertically flipped once into minimap/image coordinates",
            "source_spacing_m": features["spacing"],
            "source_resolution": features["resolution"],
            "degraded_source_resolution": grid["degraded"],
            "cropped_edge_samples": grid["remainder_samples"],
        },
        "units": {
            "cost": "multiplier of base traversal time; float32 little-endian; -1.0 = blocked",
            "classes": CLASS_NAMES,
            "water": {"0": "none", "1": "confirmed", "2": "candidate"},
            "road_mask": "uint8; 1 = explicit road member (separate from terrain class)",
        },
        "water": {
            "sea_level_m": metadata.get("sea_level_m"),
            "confirmed_cells": int((water_mask == WATER_CONFIRMED).sum()),
            "candidate_cells": int((water_mask == WATER_CANDIDATE).sum()),
            "policy": "confirmed = below sea level and cardinal boundary-connected; candidate = flat inland region below two-sample border mean; candidate-only unless multiplier raised (D6)",
        },
        "roads": roads_info,
        "statics": {"counts_by_class": statics_counts,
                    "footprint": "fixed-radius proxy per class; not collision geometry"},
        "vegetation": {"dense_cells": vegetation_dense_count,
                       "density_radius_m": config_value(config, "vegetation", "density_radius_m"),
                       "dense_count": config_value(config, "vegetation", "dense_count")},
        "surface_material": {
            "status": "unavailable",
            "reason": "material spike NO-GO: detailmap textures are RGB565 color data, not material indices (artifacts/material-spike-001.md)",
        },
        "config": {
            "path": "processor/terrain_params.json",
            "sha256": hashlib.sha256(config_bytes).hexdigest(),
            "hash_encoding": "ASCII JSON, sorted keys, separators comma/colon",
            "values": config,
        },
        "provenance": {
            "heightmap": "processed_maps/%s/heightmap.json.gz" % map_name,
            "metadata": "processed_maps/%s/metadata.json" % map_name,
            "metadata_verification": metadata_verification,
            "obstructions": "processed_maps/%s/obstructions.json" % map_name,
            "orientation": "terrain_features.to_repository_orientation; matches textured minimap and contour convention",
            "movement_thresholds": "see config.values provenance strings; uncalibrated defaults unless labeled",
        },
        "profiles": sorted(costs.keys()),
    }
    (terrain_dir / "sidecar.json").write_text(
        json.dumps(sidecar, indent=2) + "\n", encoding="ascii")


def process_map(map_name, index, total, config):
    print("[%d/%d] Processing %s..." % (index, total, map_name))
    if (not re.fullmatch(r"[a-z0-9_]+", map_name) or map_name in EXCLUDED
            or not (OUT / map_name).resolve().is_relative_to(OUT.resolve())):
        print("  error: invalid or excluded map name")
        return False
    map_dir = OUT / map_name
    try:
        samples, metadata = load_heightmap(map_dir)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print("  error: heightmap/metadata: %s" % error)
        return False
    map_size = float(metadata["map_size"])
    height_scale = float(metadata["height_scale"])
    elevation = to_repository_orientation(
        samples_to_meters(samples, height_scale))
    spacing = sample_spacing(map_size, samples.shape[0])
    grid = grid_shape(map_size, spacing, config_value(config, "grid", "cell_size_m"))
    features = compute_features(elevation, spacing,
                                config_value(config, "grid", "roughness_window_m"))
    if features["roughness_status"] != "available":
        print("  warning: roughness unavailable at %.1f m source spacing; bounded 3-sample window exceeds %.1f m" %
              (spacing, MAX_ROUGHNESS_WINDOW_M))
    features["spacing"] = spacing
    features["resolution"] = int(samples.shape[0])
    agg = aggregate(features, elevation, grid["cells"], grid["cell_samples"])

    sea_level = metadata.get("sea_level_m")
    water_native = np.zeros(samples.shape, dtype=np.uint8)
    if sea_level is not None:
        confirmed = confirmed_water_mask(elevation, float(sea_level))
        candidate = candidate_water_mask(
            elevation, features["slope_deg"], confirmed, float(sea_level),
            config_value(config, "water", "flat_epsilon_deg"),
            config_value(config, "water", "candidate_min_area_m2"),
            spacing * spacing,
            config_value(config, "water", "basin_margin_m"))
        water_native[confirmed] = WATER_CONFIRMED
        water_native[candidate] = WATER_CANDIDATE
    else:
        print("  warning: no sea_level_m; confirmed-water mask empty (candidate pass still runs)")
        candidate = candidate_water_mask(
            elevation, features["slope_deg"], np.zeros(samples.shape, bool),
            float("-inf"),
            config_value(config, "water", "flat_epsilon_deg"),
            config_value(config, "water", "candidate_min_area_m2"),
            spacing * spacing,
            config_value(config, "water", "basin_margin_m"))
        water_native[candidate] = WATER_CANDIDATE
    limit = grid["cells"] * grid["cell_samples"]
    water_blocks = water_native[:limit, :limit].reshape(
        grid["cells"], grid["cell_samples"], grid["cells"], grid["cell_samples"])
    water_grid = np.zeros((grid["cells"], grid["cells"]), dtype=np.uint8)
    for value in (WATER_CONFIRMED, WATER_CANDIDATE):
        fraction = (water_blocks == value).mean(axis=(1, 3))
        water_grid[fraction >= 0.5] = value

    obstructions_path = map_dir / "obstructions.json"
    roads, statics, vegetation = [], [], []
    if obstructions_path.exists():
        obstructions = json.loads(obstructions_path.read_text(encoding="utf-8"))
        roads = obstructions.get("roads", [])
        statics = obstructions.get("statics", [])
        vegetation = obstructions.get("vegetation", [])
    else:
        print("  warning: no obstructions.json; roads/statics/vegetation empty")
    road_mask, kept, filtered = rasterize_roads(roads, grid["cells"], grid["cells"], grid["cell_m"])
    coverage = road_coverage(map_name, kept)
    coverage["segments_kept"] = kept
    coverage["segments_filtered_decal"] = filtered
    coverage["obstruction_source"] = "present" if obstructions_path.exists() else "missing"
    if filtered:
        print("  filtered %d decal-class road segments" % filtered)

    footprints = {kind: config["footprints_m"][kind]["value"] for kind in config["footprints_m"]}
    static_mult, statics_counts = static_multiplier(
        statics, grid["cells"], grid["cells"], grid["cell_m"],
        footprints, config_value(config, "multipliers", "building"))
    dense, dense_count_cells = vegetation_density(
        vegetation, grid["cells"], grid["cells"], grid["cell_m"],
        config_value(config, "vegetation", "density_radius_m"),
        config_value(config, "vegetation", "dense_count"))

    costs = {}
    for profile_name in config["profiles"]:
        costs[profile_name] = compute_cost(agg, water_grid, road_mask, static_mult,
                                           dense, config, profile_name)
    write_artifacts(map_name, grid, water_grid, road_mask, coverage, statics_counts,
                    dense_count_cells, costs, config, metadata, features,
                    dict(agg, static_multiplier=static_mult,
                        vegetation_dense=dense.astype(np.float64)))
    blocked_summary = {name: info["blocked_cells"] for name, (_, _, info) in costs.items()}
    print("  grid=%dx%d cell=%.1fm roads=%d(filtered=%d) water=%d/%d statics=%s dense_veg=%d blocked=%s"
          % (grid["cells"], grid["cells"], grid["cell_m"], kept, filtered,
             int((water_grid == WATER_CONFIRMED).sum()),
             int((water_grid == WATER_CANDIDATE).sum()),
             statics_counts, int(dense.sum()), blocked_summary))
    return True


def main():
    names = sys.argv[1:]
    if not names:
        names = sorted(path.name for path in OUT.iterdir()
                       if path.is_dir() and path.name not in EXCLUDED
                       and ((path / "heightmap.json.gz").exists() or (path / "heightmap.json").exists()))
    config = load_config()
    processed = 0
    failed = []
    for index, name in enumerate(names, 1):
        try:
            success = process_map(name, index, len(names), config)
        except (OSError, ValueError, KeyError, IndexError, TypeError, zipfile.BadZipFile) as error:
            print("  error: %s: %s: %s" % (name, type(error).__name__, error))
            success = False
        processed += int(success)
        if not success:
            failed.append(name)
    print("Summary: %d/%d maps processed" % (processed, len(names)))
    if failed:
        print("Failed maps: %s" % ", ".join(failed))
    return 0 if processed == len(names) else 1


if __name__ == "__main__":
    sys.exit(main())
