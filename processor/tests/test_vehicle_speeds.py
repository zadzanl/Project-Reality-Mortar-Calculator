import json
import subprocess
import sys
from pathlib import Path

import pytest

from processor.extract_vehicle_speeds import classify_template, extract_raw_forward


def test_primary_block_is_not_first_or_max():
    fixture = '''
ObjectTemplate.create ObjectTemplate helper
ObjectTemplate.setMaxSpeed 0/0/999
ObjectTemplate.setEngineType c_ETShip

ObjectTemplate.create PlayerControlObject vehicle
ObjectTemplate.setMaxSpeed 4/0/10
ObjectTemplate.setEngineType c_ETTank
ObjectTemplate.setTorque 200
ObjectTemplate.setDifferential 4.5
ObjectTemplate.setNumberOfGears 5

ObjectTemplate.create ObjectTemplate turret
ObjectTemplate.setMaxSpeed 0/0/500
ObjectTemplate.setEngineType c_ETNewCar2
ObjectTemplate.setTorque 1
'''
    assert extract_raw_forward(fixture) == 10


def test_class_keywords():
    assert classify_template('us_jep_willysmb', 'vehicles/land') == 'jeep'
    assert classify_template('idf_trk_logistics', 'vehicles/land') == 'truck'
    assert classify_template('us_apc_m113', 'vehicles/land') == 'apc'
    assert classify_template('us_tnk_m1a1', 'vehicles/land') == 'tank'
    assert classify_template('us_shp_lcvp', 'vehicles/sea') == 'boat'
    assert classify_template('mystery', 'vehicles/land') == 'other'


def test_missing_zip_error(tmp_path):
    script = Path(__file__).parents[1] / 'extract_vehicle_speeds.py'
    result = subprocess.run([sys.executable, str(script), '--input', str(tmp_path / 'missing.zip')], text=True, capture_output=True)
    assert result.returncode == 2
    assert 'raw_game_data/objects_vehicles_server.zip' in result.stderr
    assert 'raw_game_data folder' in result.stderr


def test_json_schema_shape(tmp_path):
    from processor.extract_vehicle_speeds import main
    archive = tmp_path / 'objects_vehicles_server.zip'
    import zipfile
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('vehicles/land/test_truck.tweak', 'ObjectTemplate.create PlayerControlObject test_truck\nObjectTemplate.setMaxSpeed 0/0/60\nObjectTemplate.setEngineType c_ETNewCar2\nObjectTemplate.setTorque 1\n')
    output = tmp_path / 'vehicle_speeds.json'
    assert main(['--input', str(archive), '--output', str(output)]) == 0
    data = json.loads(output.read_text(encoding='ascii'))
    assert set(data) == {'format_version', 'source', 'vehicles'}
    entry = data['vehicles']['test_truck']
    assert set(entry) == {'max_speed_ms', 'class', 'calibrated', 'raw_forward', 'estimate_method'}
    assert entry['class'] == 'truck'
    assert entry['raw_forward'] == 60
    assert entry['calibrated'] is False
