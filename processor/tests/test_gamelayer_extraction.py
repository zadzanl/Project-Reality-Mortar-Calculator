import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from extract_gamelayers import bf2_to_repo, extract_map, parse_gameplayobjects, parse_sea_level

# Verbatim-format fixture excerpts in the PR v1.9 gameplayobjects.con layout
# (see extract_gamelayers.py module docstring). Road-record and static-object
# fixtures live in test_obstruction_extraction.py; those parsers are part of
# extract_obstructions.py, not this module.

GAMEPLAYOBJECTS = """
rem [ControlPointTemplate: idfbase]
ObjectTemplate.create ControlPoint idfbase
ObjectTemplate.controlPointId 1
ObjectTemplate.team 1
ObjectTemplate.unableToChangeTeam 1

rem [ControlPoint: idfbase]
Object.create idfbase
Object.absolutePosition 357.5/59.5/-374.2
Object.layer 1

rem [SpawnPointTemplate: idfbase_spawn_0]
ObjectTemplate.create SpawnPoint idfbase_spawn_0
ObjectTemplate.setGroup 1
ObjectTemplate.setControlPointId 1

rem [SpawnPoint: idfbase_spawn_0]
Object.create idfbase_spawn_0
Object.absolutePosition 350/59/-370
Object.layer 1

rem [ObjectSpawnerTemplate: idfbase_trk]
ObjectTemplate.create ObjectSpawner idfbase_trk
ObjectTemplate.team 1
ObjectTemplate.teamOnVehicle 1
ObjectTemplate.setObjectTemplate 1 idf_trk_logistics
ObjectTemplate.setObjectTemplate 2 mec_trk_logistics

rem [ObjectSpawner: idfbase_trk]
Object.create idfbase_trk
Object.absolutePosition 355/59.2/-372
Object.setControlPointId 1
Object.layer 1
"""

MALFORMED = """
ObjectTemplate.create ControlPoint good_cp
ObjectTemplate.controlPointId 7
ObjectTemplate.team 2

Object.create good_cp
Object.absolutePosition 10/20/30
Object.layer 1

ObjectTemplate.create ControlPoint broken_pos
ObjectTemplate.controlPointId 8

Object.create broken_pos
Object.absolutePosition nope
Object.layer abc

ObjectTemplate.create UnknownClass whatever
ObjectTemplate.team 1

Object.create whatever
Object.absolutePosition 1/2/3
"""


def test_control_point_ids_teams_positions_survive():
    parsed = parse_gameplayobjects(GAMEPLAYOBJECTS)
    assert len(parsed['control_points']) == 1
    cp = parsed['control_points'][0]
    assert cp['name'] == 'idfbase'
    assert cp['id'] == 1
    assert cp['team'] == 1
    assert cp['unable_to_change_team'] is True
    assert cp['x'] == 357.5 and cp['y'] == 59.5 and cp['z'] == -374.2
    assert cp['layer'] == 1


def test_spawn_point_numeric_linkage_survives():
    parsed = parse_gameplayobjects(GAMEPLAYOBJECTS)
    assert len(parsed['spawn_points']) == 1
    sp = parsed['spawn_points'][0]
    assert sp['group'] == 1
    assert sp['control_point_id'] == 1
    cp_ids = [cp['id'] for cp in parsed['control_points']]
    assert sp['control_point_id'] in cp_ids


def test_vehicle_spawner_templates_and_linkage_survive():
    parsed = parse_gameplayobjects(GAMEPLAYOBJECTS)
    assert len(parsed['vehicle_spawners']) == 1
    vs = parsed['vehicle_spawners'][0]
    assert vs['team'] == 1
    assert vs['team_on_vehicle'] == 1
    assert vs['templates'] == {'1': 'idf_trk_logistics', '2': 'mec_trk_logistics'}
    assert vs['control_point_id'] == 1
    cp_ids = [cp['id'] for cp in parsed['control_points']]
    assert vs['control_point_id'] in cp_ids


def test_malformed_sections_skipped_without_crashing():
    parsed = parse_gameplayobjects(MALFORMED)
    names = [cp['name'] for cp in parsed['control_points']]
    assert names == ['good_cp', 'broken_pos']
    broken = parsed['control_points'][1]
    assert broken['id'] == 8
    assert 'x' not in broken
    assert 'layer' not in broken


def test_bf2_to_repo_transform():
    x, y = bf2_to_repo(357.5, -374.2, 1024)
    assert x == 869.5
    assert y == 886.2


def test_parse_sea_level():
    assert parse_sea_level('heightmapcluster.setSeaWaterLevel 49') == 49.0
    assert parse_sea_level('rem no sea level here') is None
    assert parse_sea_level(None) is None


def test_extract_map_end_to_end_preserves_elevation(tmp_path):
    raw_dir = tmp_path / 'raw_map_data'
    proc_dir = tmp_path / 'processed_maps'
    (raw_dir / 'fake_map').mkdir(parents=True)
    (proc_dir / 'fake_map').mkdir(parents=True)
    (proc_dir / 'fake_map' / 'metadata.json').write_text(
        json.dumps({'map_size': 1024, 'height_scale': 163.8375}), encoding='utf-8')

    zip_path = raw_dir / 'fake_map' / 'server.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('gamemodes/gpm_cq/32/gameplayobjects.con', GAMEPLAYOBJECTS)
        zf.writestr('heightdata.con', 'heightmapcluster.setSeaWaterLevel 49')

    result, errors = extract_map('fake_map', raw_dir=raw_dir, processed_dir=proc_dir)
    assert errors == []
    assert result['sea_level_m'] == 49.0
    assert len(result['layers']) == 1
    layer = result['layers'][0]
    assert layer['mode'] == 'gpm_cq' and layer['size'] == 32

    cp = layer['control_points'][0]
    # Regression: elevation must survive the repo-y overwrite (key-order bug).
    assert cp['x'] == 869.5
    assert cp['y'] == 886.2
    assert cp['elevation_m'] == 59.5
