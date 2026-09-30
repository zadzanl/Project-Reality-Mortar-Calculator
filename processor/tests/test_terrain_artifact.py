import json
import sys

import numpy as np
import pytest

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from terrain_artifact import load_terrain_artifact


def test_loader_returns_flow_contract(tmp_path):
    root = tmp_path / "terrain"
    profile = root / "infantry"
    profile.mkdir(parents=True)
    sidecar = {"format_version": "1.0", "artifact": "terrain_cost",
               "profiles": ["infantry"], "blocked_sentinel": -1.0,
               "grid": {"rows": 2, "cols": 2, "cell_size_m": 4.0,
                         "origin": "top-left; x east, y south; repo world meters"},
               "roads": {"state": "missing_client_zip"},
               "provenance": {"heightmap": "fixture"}, "config": {"sha256": "x"}}
    (root / "sidecar.json").write_text(json.dumps(sidecar), encoding="ascii")
    np.array([1, 2, 3, 4], dtype="<f4").tofile(profile / "cost.bin")
    np.array([1, 1, 2, 2], dtype=np.uint8).tofile(profile / "classes.bin")
    np.zeros(4, dtype=np.uint8).tofile(root / "road_mask.bin")
    np.zeros(4, dtype=np.uint8).tofile(root / "water.bin")
    result = load_terrain_artifact(root)
    assert result["costs"].shape == (2, 2)
    assert result["passability_sentinel"] == -1.0
    assert result["source_coverage"]["state"] == "missing_client_zip"


def test_loader_rejects_wrong_grid_length(tmp_path):
    root = tmp_path / "terrain"
    profile = root / "infantry"
    profile.mkdir(parents=True)
    sidecar = {"format_version": "1.0", "artifact": "terrain_cost",
               "profiles": ["infantry"], "blocked_sentinel": -1.0,
               "grid": {"rows": 2, "cols": 2, "cell_size_m": 4.0,
                         "origin": "top-left; x east, y south; repo world meters"},
               "roads": {}, "provenance": {}, "config": {}}
    (root / "sidecar.json").write_text(json.dumps(sidecar), encoding="ascii")
    for path in (profile / "cost.bin", profile / "classes.bin",
                 root / "road_mask.bin", root / "water.bin"):
        path.write_bytes(b"\x00")
    with pytest.raises(ValueError, match="expected 16 bytes"):
        load_terrain_artifact(root)