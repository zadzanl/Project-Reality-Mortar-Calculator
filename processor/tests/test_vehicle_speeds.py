import json
import subprocess
import sys
from pathlib import Path

import pytest

from processor.extract_vehicle_speeds import (classify_product, classify_template,
                                               extract_raw_forward)


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


def test_product_classification_requires_rooted_positive_evidence():
    root = ('ObjectTemplate.create PlayerControlObject m35\n'
            'ObjectTemplate.setMaxSpeed 0/0/60\n'
            'ObjectTemplate.setEngineType c_ETNewCar2\n'
            'ObjectTemplate.setTorque 1\n')
    assert classify_product('m35_truck', root, 'vehicles/land') == (
        'truck_wheeled', 'positive_wheeled_propulsion')
    assert classify_product('mystery', root, 'vehicles/land')[0] is None
    assert classify_product('depot_truck', root, 'vehicles/land')[0] is None


def test_helicopter_positive_evidence_is_not_tracked():
    text = ('ObjectTemplate.create PlayerControlObject c_ETHelicopter\n'
            'ObjectTemplate.setMaxSpeed 0/0/80\n'
            'ObjectTemplate.setEngineType c_ETHelicopter\n')
    assert classify_product('ah1_helicopter', text, 'vehicles/air/ah1_helicopter.tweak') == (
        'helicopter', 'positive_helicopter_root')


def test_v2_catalog_preserves_exclusion_evidence(tmp_path):
    from processor.extract_vehicle_speeds import main
    import zipfile
    archive = tmp_path / 'objects_vehicles_server.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('vehicles/land/test_car.tweak',
                   'ObjectTemplate.create PlayerControlObject test_car\n'
                   'ObjectTemplate.setMaxSpeed 0/0/60\n'
                   'ObjectTemplate.setEngineType c_ETNewCar2\n'
                   'ObjectTemplate.setTorque 1\n')
        z.writestr('vehicles/land/depot_crate.tweak',
                   'ObjectTemplate.create PlayerControlObject depot_crate\n'
                   'ObjectTemplate.setMaxSpeed 0/0/60\n'
                   'ObjectTemplate.setEngineType c_ETNewCar2\n')
    output = tmp_path / 'vehicle_speeds.json'
    assert main(['--format-version', '2.0', '--input', str(archive),
                 '--output', str(output)]) == 0
    data = json.loads(output.read_text(encoding='ascii'))
    assert data['format_version'] == '2.0'
    assert data['vehicles']['test_car']['product_id'] == 'car'
    assert data['vehicles']['depot_crate']['eligibility'] == 'unsupported_data'
