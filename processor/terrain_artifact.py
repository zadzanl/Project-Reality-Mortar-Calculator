#!/usr/bin/env python3
"""Read terrain artifacts without recalculating terrain physics.

Known ceiling: v1 grids only, loaded in memory. Larger worlds need chunked
storage and an explicitly versioned contract, not silent byte reinterpretation.
"""
import json
import re
from pathlib import Path

import numpy as np


BLOCKED = -1.0


def load_terrain_artifact(path, profile="infantry"):
    """Load and validate the later flow solver's terrain input contract."""
    root = Path(path)
    sidecar = json.loads((root / "sidecar.json").read_text(encoding="ascii"))
    if sidecar.get("format_version") != "1.0" or sidecar.get("artifact") != "terrain_cost":
        raise ValueError("unsupported terrain artifact format")
    if not re.fullmatch(r"[a-z0-9_]+", profile) or profile not in sidecar["profiles"]:
        raise ValueError("unknown or invalid terrain profile")
    grid = sidecar["grid"]
    rows, cols = grid["rows"], grid["cols"]
    if any(type(n) is not int or n <= 0 for n in (rows, cols)):
        raise ValueError("terrain dimensions must be positive integers")
    cell_size = float(grid["cell_size_m"])
    if not np.isfinite(cell_size) or cell_size <= 0:
        raise ValueError("terrain cell size must be finite and positive")
    if sidecar.get("blocked_sentinel") != BLOCKED:
        raise ValueError("unsupported blocked sentinel")
    if grid.get("origin") != "top-left; x east, y south; repo world meters":
        raise ValueError("unsupported terrain grid origin")

    def read_grid(filename, dtype):
        file_path = (root / filename).resolve()
        if not file_path.is_relative_to(root.resolve()):
            raise ValueError("terrain grid path escapes artifact directory")
        expected_bytes = rows * cols * np.dtype(dtype).itemsize
        if file_path.stat().st_size != expected_bytes:
            raise ValueError("%s: expected %d bytes" % (filename, expected_bytes))
        # Explicit endian and shape: raw fromfile stores neither in the file.
        # https://numpy.org/doc/stable/reference/generated/numpy.fromfile.html
        values = np.fromfile(file_path, dtype=dtype).reshape(rows, cols)
        if not np.isfinite(values).all():
            raise ValueError("non-finite terrain grid: " + filename)
        return values

    costs = read_grid(profile + "/cost.bin", "<f4")
    classes = read_grid(profile + "/classes.bin", "u1")
    road = read_grid("road_mask.bin", "u1")
    water = read_grid("water.bin", "u1")
    if not ((costs > 0) | (costs == BLOCKED)).all():
        raise ValueError("terrain cost must be positive or blocked (-1)")
    if (classes > 6).any() or (road > 1).any() or (water > 2).any():
        raise ValueError("invalid terrain class or mask value")
    if not np.array_equal(classes == 4, costs == BLOCKED):
        raise ValueError("blocked costs and extreme-slope classes disagree")
    diagnostics = {}
    for name, info in sidecar.get("diagnostics", {}).items():
        if info["dtype"] != "<f4":
            raise ValueError("unsupported diagnostic dtype")
        diagnostics[name] = read_grid(info["file"], "<f4")
    return {
        "rows": rows,
        "cols": cols,
        "origin": grid["origin"],
        "cell_size_m": cell_size,
        "grid": grid,
        "sidecar": sidecar,
        "diagnostics": diagnostics,
        "costs": costs.reshape(rows, cols),
        "classes": classes.reshape(rows, cols),
        "road_mask": road.reshape(rows, cols),
        "water": water.reshape(rows, cols),
        "passability_sentinel": BLOCKED,
        "source_coverage": sidecar["roads"],
        "provenance": sidecar["provenance"],
        "config": sidecar["config"],
    }