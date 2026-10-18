#!/usr/bin/env python3
"""Extract uncalibrated Project Reality vehicle speeds into static JSON.

ROLE: Maintainer-only CLI tool. End users never run this script.
INPUTS:
    - raw_game_data/objects_vehicles_server.zip
    - raw_game_data/objects_common_server.zip
OUTPUTS:
    - calculator/static/data/vehicle_speeds.json
HOW TO RUN:
    python processor/extract_vehicle_speeds.py
DID IT WORK CHECK:
    Writes calculator/static/data/vehicle_speeds.json containing vehicle model records.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = REPO_ROOT / 'raw_game_data' / 'objects_vehicles_server.zip'
# Command vehicles (idf_acv_m557, us_acv_stryker, ...) live outside the
# vehicles archive; they are land vehicles referenced by gamelayers. Air
# templates are scanned separately so helicopter evidence is not silently
# classified as a tracked vehicle.
COMMON_ZIP = REPO_ROOT / 'raw_game_data' / 'objects_common_server.zip'
DEFAULT_OUTPUT = REPO_ROOT / 'calculator' / 'static' / 'data' / 'vehicle_speeds.json'
# These are modeled defaults, not measured game speeds. Keep old names for
# v1 readers; product_id is the additive v2 classification.
CLASS_DEFAULTS = {'jeep': 28, 'truck': 22, 'apc': 16, 'tank': 15, 'boat': 9, 'other': 20}
PRODUCT_DEFAULTS = {'car': 28, 'truck_wheeled': 16, 'tracked': 15, 'boat': 9}
SOURCE = ('objects_vehicles_server.zip (land/sea/civilian) plus objects_common_server.zip '
          '(common/command_post) .tweak extraction, PR v1.9; setMaxSpeed per-axis '
          'forward component is not km/h; single-anchor calibration failed '
          '(see artifacts/vehicle-speed-spike.md); max_speed_ms values are class defaults, uncalibrated')
RE_VECTOR = re.compile(r'^\s*ObjectTemplate\.setMaxSpeed\s+([^\s]+)', re.IGNORECASE | re.MULTILINE)
RE_CREATE = re.compile(r'^\s*ObjectTemplate\.create\s+', re.IGNORECASE | re.MULTILINE)


def classify_template(template, path=''):
    value = (template + ' ' + path).lower()
    if any(k in value for k in ('boat', 'ship', 'water', 'sea', '/sea/', '\\sea\\')):
        return 'boat'
    if any(k in value for k in ('tank', 'tnk')):
        return 'tank'
    if any(k in value for k in ('apc', 'ifv', 'afv')):
        return 'apc'
    if any(k in value for k in ('jeep', 'jep', 'willys', 'hmmwv', '4x4')):
        return 'jeep'
    if any(k in value for k in ('truck', 'trk', 'logistics', 'transport')):
        return 'truck'
    return 'other'


def classify_product(template, text, path=''):
    """Return ``(product_id, reason)`` from rooted propulsion evidence.

    Names are evidence only. A selected root block must contain a primary
    engine type and propulsion fields; uncertainty is excluded explicitly.
    """
    value = (template + ' ' + path).lower()
    starts = list(RE_CREATE.finditer(text))
    boundaries = [m.start() for m in starts] + [len(text)]
    blocks = []
    for index, match in enumerate(starts):
        block = text[boundaries[index]:boundaries[index + 1]]
        lower = ' '.join(block.lower().split())
        if 'playercontrolobject' not in lower or not RE_VECTOR.search(block):
            continue
        engine = re.search(r'setenginetype\s+(\S+)', lower)
        blocks.append((lower, engine.group(1) if engine else ''))
    if not blocks:
        # Some PR vehicle archives declare the active PlayerControlObject with
        # ``activeSafe`` and place the Engine block later in the file. Keep
        # this fallback rooted in archive path + engine evidence; do not use a
        # filename alone to manufacture a product.
        global_engine = re.findall(r'setenginetype\s+(\S+)', text.lower())
        lower_text = text.lower()
        if global_engine and 'setmaxspeed' in lower_text:
            blocks.append((lower_text, global_engine[-1]))
        else:
            return None, 'missing_primary_propulsion'
    root, engine = blocks[0]
    if any(word in value for word in ('depot', 'crate', 'supply', 'weapon', 'deployable')):
        return None, 'excluded_nonmobile_root'
    if any(word in value for word in ('jet', 'airplane', 'fighter')):
        return None, 'excluded_air_root'
    if 'helicopter' in root or 'helicopter' in value:
        return 'helicopter', 'positive_helicopter_root'
    if engine == 'c_etship' or any(word in value for word in ('ship', 'boat', 'lcvp')):
        return 'boat', 'positive_ship_root'
    if engine == 'c_ettank' or 'track' in root or 'tank' in value or 'tnk' in value:
        return 'tracked', 'positive_tracked_propulsion'
    if engine == 'c_etnewcar2' and any(word in value for word in ('truck', 'trk', 'apc', 'ifv', 'afv', 'brdm')):
        return 'truck_wheeled', 'positive_wheeled_propulsion'
    if engine == 'c_etnewcar2' and any(word in value for word in ('jeep', 'jep', 'willys', 'hmmwv', '4x4', 'car')):
        return 'car', 'positive_wheeled_propulsion'
    return None, 'uncertain_root_or_product'


def _forward(value):
    parts = value.split('/')
    if len(parts) != 3:
        return None
    try:
        return float(parts[2]) if '.' in parts[2] else int(parts[2])
    except ValueError:
        return None


def extract_raw_forward(text):
    """Return the primary engine block's z component, or None.

    A movement block has setMaxSpeed plus an engine type and drivetrain field.
    Prefer a PlayerControlObject block and normal vehicle engine types, then
    fall back to the strongest complete movement block. This avoids selecting
    auxiliary/turret vectors or an amphibious secondary engine.
    """
    blocks = []
    starts = list(RE_CREATE.finditer(text))
    boundaries = [m.start() for m in starts] + [len(text)]
    for index in range(len(starts)):
        block = text[boundaries[index]:boundaries[index + 1]]
        speed = RE_VECTOR.search(block)
        if not speed:
            continue
        lower = ' '.join(block.lower().split())
        score = 0
        if 'setenginetype c_etnewcar' in lower or 'setenginetype c_ettank' in lower:
            score += 30
        if 'setenginetype c_etship' in lower:
            score += 20
        if 'settorque' in lower:
            score += 10
        if 'setdifferential' in lower:
            score += 5
        if 'setnumberofgears' in lower or 'setgearratios' in lower:
            score += 5
        if 'playercontrolobject' in lower:
            score += 20
        blocks.append((score, index, _forward(speed.group(1))))
    usable = [item for item in blocks if item[2] is not None]
    if not usable:
        return None
    usable.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return usable[0][2]


def extract_archive(zip_path, prefixes):
    vehicles = {}
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            normalized = name.replace('\\', '/').lower()
            if not normalized.endswith('.tweak') or not normalized.startswith(prefixes):
                continue
            template = Path(name).stem
            text = archive.read(name).decode('latin1', errors='replace')
            raw = extract_raw_forward(text)
            vehicle_class = classify_template(template, normalized)
            product_id, eligibility_reason = classify_product(template, text, normalized)
            vehicles[template] = {
                'max_speed_ms': CLASS_DEFAULTS[vehicle_class] if product_id != 'helicopter' else None,
                'class': vehicle_class,
                'calibrated': False,
                'raw_forward': raw,
                'estimate_method': 'class default (uncalibrated); raw_forward preserved for future calibration',
                'product_id': product_id,
                'eligibility': 'eligible' if product_id else 'unsupported_data',
                'eligibility_reason': eligibility_reason,
                'archive_member': name.replace('\\', '/'),
            }
    return dict(sorted(vehicles.items()))


def referenced_templates():
    refs = set()
    for path in (REPO_ROOT / 'processed_maps').glob('*/gamelayers.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        layers = data.get('layers', [data])
        for layer in layers:
            for spawner in layer.get('vehicle_spawners', []):
                templates = spawner.get('templates', {})
                if isinstance(templates, dict):
                    refs.update(str(v) for v in templates.values())
                elif templates:
                    refs.add(str(templates))
    return refs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_ZIP)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--format-version', choices=('1.0', '2.0'), default='1.0',
                        help='2.0 includes rooted eligibility evidence; 1.0 preserves the legacy file shape')
    args = parser.parse_args(argv)
    if not args.input.is_file():
        print('ERROR: expected vehicle archive at raw_game_data/objects_vehicles_server.zip; maintainers must provide it in the raw_game_data folder.', file=sys.stderr)
        return 2
    vehicles = extract_archive(args.input, ('vehicles/land/', 'vehicles/sea/', 'vehicles/civilian/', 'vehicles/air/'))
    if COMMON_ZIP.is_file():
        vehicles.update(extract_archive(COMMON_ZIP, ('common/command_post/',)))
    vehicles = dict(sorted(vehicles.items()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.format_version == '1.0':
        for entry in vehicles.values():
            for key in ('product_id', 'eligibility', 'eligibility_reason', 'archive_member'):
                entry.pop(key, None)
    payload = {'format_version': args.format_version, 'source': SOURCE, 'vehicles': vehicles}
    args.output.write_text(json.dumps(payload, indent=2) + '\n', encoding='ascii')
    refs = referenced_templates()
    missing = sorted(refs - set(vehicles))
    matched = len(refs) - len(missing)
    print('Extracted {} vehicle templates ({} referenced gamelayer templates matched, {} missing).'.format(len(vehicles), matched, len(missing)))
    print('Missing vehicle templates: {}'.format(', '.join(missing) if missing else 'none'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
