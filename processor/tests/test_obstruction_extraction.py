import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from extract_obstructions import bf2_to_repo, classify, parse_roads, parse_statics, parse_vegetation


class FakeClient:
    def __init__(self, data):
        self.data = data

    def namelist(self):
        return list(self.data)

    def read(self, name):
        return self.data[name]


def test_parsers_transform_and_malformed_blocks():
    statics = """
Object.create house_small
Object.absolutePosition 10/20/-30
Object.rotation 0/45/0
Object.create broken
Object.absolutePosition nope
Object.create fence_piece
Object.absolutePosition -10/20/30
Object.rotation 0/90/0
"""
    parsed = parse_statics(statics, 100)
    assert len(parsed) == 2
    assert parsed[0]["class"] == "building"
    assert parsed[0]["x"] == 60.0 and parsed[0]["y"] == 80.0
    assert parsed[0]["rotation_deg"] == 45.0
    assert parsed[1]["class"] == "fence"
    assert classify("unknown_object") == "unclassified"

    vegetation = """
Object.create olive
Object.absoluteTransformation [1/0/0/0][0/1/0/0][0/0/1/0][-10/4/20/1]
Object.create malformed
Object.absoluteTransformation [1/0/0/0]
"""
    plants = parse_vegetation(vegetation, 100)
    assert len(plants) == 1
    assert plants[0]["x"] == 40.0 and plants[0]["y"] == 30.0


def test_road_fixture_and_missing_mesh_are_skipped():
    compiled = """
Object.create dirtroad
Object.geometry.loadMesh Levels\\demo\\Roads\\road_compiled.mesh
Object.absolutePosition 0/0/0
Object.create malformed
Object.geometry.loadMesh Levels\\demo\\Roads\\missing_compiled.mesh
"""
    # Header/vertex details are tested by bf2_road_mesh.py; this parser test
    # verifies missing records do not abort the obstruction extraction.
    roads = parse_roads(compiled, FakeClient({}), "demo", 100, lambda message: None)
    assert roads == []
    assert bf2_to_repo(0, 25, 100) == (50.0, 25.0)
