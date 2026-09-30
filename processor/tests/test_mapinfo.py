import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from bf2_mapinfo import parse_heightdata


def test_primary_heightdata_values_are_authoritative():
    info = parse_heightdata("""
heightmapcluster.setHeightmapSize 1024
rem --- primary ---
heightmap.setSize 513 513
heightmap.setScale 2/0.0025/2
rem --- secondary ---
heightmap.setScale 4/0.64/4
heightmapcluster.setSeaWaterLevel 49
""")
    assert info["map_size"] == 1024
    assert info["heightmap_resolution"] == 513
    assert abs(info["height_scale"] - 163.8375) < 1e-6
    assert info["sea_level_m"] == 49.0


def test_missing_fields_are_reported_as_none():
    assert parse_heightdata("heightmapcluster.create Map") == {
        "map_size": None,
        "height_scale": None,
        "heightmap_resolution": None,
        "sea_level_m": None,
    }