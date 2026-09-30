#!/usr/bin/env python3
"""
Extract game-layer data (control points, spawn points, vehicle spawners)
from raw_map_data/<map>/server.zip into processed_maps/<map>/gamelayers.json.

Also extracts heightmapcluster.setSeaWaterLevel from heightdata.con into
processed_maps/<map>/metadata.json as "sea_level_m" (additive field).

Maintainer-side only. Never modifies raw_map_data/. the_falklands excluded.

CONFIRMED COORDINATE TRANSFORM (spike 1.1, see artifacts/spike_asad_khal_zoom.png):
  BF2 gameplayobjects.con absolutePosition is "X/Y/Z" where
    X = east offset from map center (meters)   [+X = east]
    Y = elevation (meters)
    Z = north offset from map center (meters)  [+Z = north]
  Repo world coordinates (meters, top-left origin, y increasing south):
    x_repo = X + map_size / 2
    y_repo = map_size / 2 - Z
  Verified by plotting named control points (northobjective vs southobjective)
  over the processed minimap, and by aligning sea-level water masks with the
  minimap coastline on adak and fools_road (artifacts/spike_water_*.png).

Usage:
  python processor/extract_gamelayers.py              # full extraction, all maps
  python processor/extract_gamelayers.py --plot asad_khal [--layer gpm_cq/32]
                                                      # spike: render debug overlay
"""
import argparse
import gzip
import json
import re
import sys
import zipfile
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print('NumPy not found, installing...')
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'numpy'], check=True)
    import numpy as np

REPO_ROOT = Path(__file__).parent.parent
RAW_DIR = REPO_ROOT / 'raw_map_data'
PROCESSED_DIR = REPO_ROOT / 'processed_maps'
EXCLUDED_MAPS = {'the_falklands'}

# ---------------------------------------------------------------------------
# gameplayobjects.con parser
# ---------------------------------------------------------------------------
# Format (verified against asad_khal gpm_cq/32, PR v1.9):
#   rem [ControlPointTemplate: <name>]          <- comment marker, informational
#   ObjectTemplate.create ControlPoint <name>   <- template block start
#   ObjectTemplate.<prop> <value...>            <- template properties
#   rem [ControlPoint: <name>]
#   Object.create <name>                        <- instance block start
#   Object.absolutePosition X/Y/Z
#   Object.setControlPointId N                  <- spawner instances only
#   Object.layer N
# Blocks are separated by blank lines; instance blocks may be indented and
# wrapped in "if v_arg1 == host" ... "endIf".

RE_TEMPLATE_CREATE = re.compile(r'^\s*ObjectTemplate\.create\s+(\S+)\s+(\S+)')
RE_INSTANCE_CREATE = re.compile(r'^\s*Object\.create\s+(\S+)')
RE_TEMPLATE_PROP = re.compile(r'^\s*ObjectTemplate\.(\S+)\s*(.*)')
RE_INSTANCE_PROP = re.compile(r'^\s*Object\.(?!create\b)(\S+)\s*(.*)')


def _split_slash_values(text):
    """Split 'X/Y/Z' style value strings into floats."""
    return [float(v) for v in text.strip().split('/')]


def parse_gameplayobjects(content):
    """Parse one gameplayobjects.con file.

    Returns dict with keys:
      control_points:   [{name, id, team, unable_to_change_team, x, y, z, layer}]
      spawn_points:     [{name, group, control_point_id, x, y, z, layer}]
      vehicle_spawners: [{name, team, team_on_vehicle, templates, control_point_id,
                          x, y, z, layer}]
    Positions are raw BF2 center-origin values (x=X, y=elevation, z=Z);
    convert with bf2_to_repo().
    """
    templates = {}   # name -> {class, props: {prop: [values...]}}
    instances = {}   # name -> {props: {prop: [values...]}}

    current_kind = None   # 'template' | 'instance' | None
    current_name = None

    for line in content.splitlines():
        m = RE_TEMPLATE_CREATE.match(line)
        if m:
            current_kind = 'template'
            current_name = m.group(2)
            templates[current_name] = {'class': m.group(1), 'props': {}}
            continue
        m = RE_INSTANCE_CREATE.match(line)
        if m:
            current_kind = 'instance'
            current_name = m.group(1)
            instances[current_name] = {'props': {}}
            continue
        if current_kind == 'template':
            m = RE_TEMPLATE_PROP.match(line)
            if m and current_name in templates:
                templates[current_name]['props'].setdefault(m.group(1), []).append(m.group(2).strip())
        elif current_kind == 'instance':
            m = RE_INSTANCE_PROP.match(line)
            if m and current_name in instances:
                instances[current_name]['props'].setdefault(m.group(1), []).append(m.group(2).strip())

    control_points = []
    spawn_points = []
    vehicle_spawners = []

    for name, tpl in templates.items():
        props = tpl['props']
        inst = instances.get(name, {'props': {}})
        iprops = inst['props']

        pos = None
        if 'absolutePosition' in iprops:
            try:
                vals = _split_slash_values(iprops['absolutePosition'][0])
            except ValueError:
                vals = []
            if len(vals) == 3:
                pos = vals
        layer = None
        if 'layer' in iprops:
            try:
                layer = int(iprops['layer'][0])
            except ValueError:
                layer = None

        if tpl['class'] == 'ControlPoint':
            cp = {
                'name': name,
                'id': _int_prop(props, 'controlPointId'),
                'team': _int_prop(props, 'team'),
                'unable_to_change_team': _int_prop(props, 'unableToChangeTeam') == 1,
            }
            if pos:
                cp['x'], cp['y'], cp['z'] = pos
            if layer is not None:
                cp['layer'] = layer
            control_points.append(cp)
        elif tpl['class'] == 'SpawnPoint':
            sp = {
                'name': name,
                'group': _int_prop(props, 'setGroup'),
                'control_point_id': _int_prop(props, 'setControlPointId'),
            }
            if pos:
                sp['x'], sp['y'], sp['z'] = pos
            if layer is not None:
                sp['layer'] = layer
            spawn_points.append(sp)
        elif tpl['class'] == 'ObjectSpawner':
            # setObjectTemplate lines look like: "2 idf_trk_logistics" (team, template).
            # A spawner may have one per team.
            team_templates = {}
            for raw in props.get('setObjectTemplate', []):
                parts = raw.split()
                if len(parts) == 2:
                    team_templates[parts[0]] = parts[1]
            vs = {
                'name': name,
                'team': _int_prop(props, 'team'),
                'team_on_vehicle': _int_prop(props, 'teamOnVehicle'),
                'templates': team_templates,
                'control_point_id': _int_prop(iprops, 'setControlPointId'),
            }
            if pos:
                vs['x'], vs['y'], vs['z'] = pos
            if layer is not None:
                vs['layer'] = layer
            vehicle_spawners.append(vs)

    return {
        'control_points': control_points,
        'spawn_points': spawn_points,
        'vehicle_spawners': vehicle_spawners,
    }


def _int_prop(props, key):
    vals = props.get(key)
    if not vals:
        return None
    try:
        return int(vals[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Coordinate transform (confirmed by spike 1.1; see module docstring)
# ---------------------------------------------------------------------------

def bf2_to_repo(x, z, map_size):
    """BF2 center-origin (X east, Z north) -> repo top-left origin (x east, y south)."""
    return x + map_size / 2.0, map_size / 2.0 - z


# ---------------------------------------------------------------------------
# Sea level
# ---------------------------------------------------------------------------

RE_SEA_LEVEL = re.compile(r'heightmapcluster\.setSeaWaterLevel\s+(-?[\d.]+)', re.IGNORECASE)


def parse_sea_level(heightdata_content):
    m = RE_SEA_LEVEL.search(heightdata_content or '')
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Extraction driver
# ---------------------------------------------------------------------------

RE_LAYER_PATH = re.compile(r'gamemodes/([^/]+)/([^/]+)/gameplayobjects\.con$', re.IGNORECASE)


def extract_map(map_name, raw_dir=RAW_DIR, processed_dir=PROCESSED_DIR):
    """Extract all layers for one map. Returns (layers, errors)."""
    zip_path = raw_dir / map_name / 'server.zip'
    if not zip_path.exists():
        return None, ['no server.zip']

    layers = []
    errors = []
    sea_level = None
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            lm = RE_LAYER_PATH.match(name.replace('\\', '/'))
            if lm:
                mode, size = lm.group(1), lm.group(2)
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    parsed = parse_gameplayobjects(content)
                    layers.append({
                        'mode': mode,
                        'size': int(size),
                        **parsed,
                    })
                except Exception as exc:  # keep going per spec
                    errors.append('{} {}: {}'.format(mode, size, exc))
            elif name.lower().endswith('heightdata.con'):
                try:
                    sea_level = parse_sea_level(zf.read(name).decode('utf-8', errors='ignore'))
                except Exception as exc:
                    errors.append('heightdata.con: {}'.format(exc))

    # Convert positions to repo coordinates using map_size from metadata.
    meta_path = processed_dir / map_name / 'metadata.json'
    metadata = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    map_size = metadata.get('map_size')
    if map_size is None:
        errors.append('no metadata.json map_size; positions left in BF2 coordinates')
    else:
        for layer in layers:
            for group in ('control_points', 'spawn_points', 'vehicle_spawners'):
                for obj in layer[group]:
                    if 'x' in obj:
                        # Pop elevation BEFORE writing repo y, or the repo y
                        # overwrites the BF2 elevation stored under 'y'.
                        elevation = obj.pop('y')
                        rx, ry = bf2_to_repo(obj.pop('x'), obj.pop('z'), map_size)
                        obj['x'] = round(rx, 3)
                        obj['y'] = round(ry, 3)
                        obj['elevation_m'] = elevation

    return {'layers': layers, 'sea_level_m': sea_level, 'metadata': metadata}, errors


def write_outputs(map_name, result, processed_dir=PROCESSED_DIR):
    out_dir = processed_dir / map_name
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = {
        'map_name': map_name,
        'format_version': '1.0',
        'layers': result['layers'],
    }
    with open(out_dir / 'gamelayers.json', 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1)

    # Sea level: additive metadata field, preserve everything else.
    if result['sea_level_m'] is not None:
        metadata = result['metadata']
        metadata['sea_level_m'] = result['sea_level_m']
        with open(out_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    else:
        print('  WARNING: no setSeaWaterLevel found; metadata unchanged')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plot', metavar='MAP', help='spike mode: render debug overlay for one map')
    ap.add_argument('--layer', default='gpm_cq/32', help='layer for --plot (default gpm_cq/32)')
    ap.add_argument('--out', metavar='PNG', help='output path for --plot')
    args = ap.parse_args()

    if args.plot:
        return plot_spike(args.plot, args.layer, args.out)

    maps = sorted(
        p.name for p in RAW_DIR.iterdir()
        if p.is_dir() and p.name not in EXCLUDED_MAPS
    )
    total = len(maps)
    processed = 0
    all_errors = {}
    for i, map_name in enumerate(maps, 1):
        print('[{}/{}] Processing {}...'.format(i, total, map_name))
        result, errors = extract_map(map_name)
        if result is None:
            all_errors[map_name] = errors
            continue
        write_outputs(map_name, result)
        processed += 1
        if errors:
            all_errors[map_name] = errors

    print()
    print('Summary: {}/{} maps processed.'.format(processed, total))
    if all_errors:
        print('Errors:')
        for map_name, errs in all_errors.items():
            for e in errs:
                print('  {}: {}'.format(map_name, e))
    return 0


# ---------------------------------------------------------------------------
# Spike 1.1: visual verification of the coordinate transform
# ---------------------------------------------------------------------------

def plot_spike(map_name, layer_spec, out_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image

    zip_path = RAW_DIR / map_name / 'server.zip'
    minimap_path = PROCESSED_DIR / map_name / 'minimap.png'
    metadata = json.loads((PROCESSED_DIR / map_name / 'metadata.json').read_text(encoding='utf-8'))
    map_size = metadata['map_size']
    height_scale = metadata['height_scale']

    mode, size = layer_spec.split('/')
    with zipfile.ZipFile(zip_path, 'r') as zf:
        content = zf.read('gamemodes/{}/{}/gameplayobjects.con'.format(mode, size)).decode('utf-8', errors='ignore')
        sea_level = parse_sea_level(zf.read('heightdata.con').decode('utf-8', errors='ignore'))
    parsed = parse_gameplayobjects(content)

    minimap = Image.open(minimap_path).convert('RGB')
    w, h = minimap.size
    scale = w / map_size  # px per meter

    # Heightmap water mask (elevation <= sea level).
    with gzip.open(PROCESSED_DIR / map_name / 'heightmap.json.gz', 'rt') as f:
        hm_doc = json.load(f)
    hm = np.array(hm_doc['data'], dtype=np.float64).reshape(hm_doc['resolution'], hm_doc['resolution'])
    elevation = hm / 65535.0 * height_scale
    water = elevation <= sea_level if sea_level is not None else np.zeros_like(elevation, dtype=bool)

    fig, axes = plt.subplots(1, 3, figsize=(30, 10))
    candidates = [
        ('candidate A: y = Z + size/2 (+Z = south)', lambda x, z: (x + map_size / 2, z + map_size / 2)),
        ('candidate B: y = size/2 - Z (+Z = north)', lambda x, z: (x + map_size / 2, map_size / 2 - z)),
    ]
    for ax, (title, fn) in zip(axes[:2], candidates):
        ax.imshow(minimap)
        ax.set_title(title, fontsize=10)
        for cp in parsed['control_points']:
            if 'x' not in cp:
                continue
            rx, ry = fn(cp['x'], cp['z'])
            color = {1: 'red', 2: 'blue'}.get(cp.get('team'), 'yellow')
            ax.plot(rx * scale, ry * scale, 'o', color=color, markersize=12, markeredgecolor='white')
            label = cp['name'].replace('cpname_{}_{}_'.format(map_name, _layer_tag(mode, size)), '')
            ax.annotate('{} (id {})'.format(label, cp['id']), (rx * scale, ry * scale),
                        color='white', fontsize=8,
                        xytext=(8, 8), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.2', fc='black', alpha=0.6))
        for sp in parsed['spawn_points']:
            if 'x' not in sp:
                continue
            rx, ry = fn(sp['x'], sp['z'])
            ax.plot(rx * scale, ry * scale, '^', color='lime', markersize=6)
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)

    ax = axes[2]
    ax.imshow(minimap)
    overlay = np.zeros((*water.shape, 4))
    overlay[water] = [0, 0.4, 1, 0.55]
    ax.imshow(overlay, extent=(0, w, h, 0), interpolation='nearest')
    ax.set_title('water mask: elevation <= {} m (sea level)'.format(sea_level), fontsize=10)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)

    if out_path is None:
        out_path = REPO_ROOT / 'openspec' / 'changes' / 'add-opening-flow-simulator' / 'artifacts' / 'spike_{}.png'.format(map_name)
    fig.tight_layout()
    fig.savefig(out_path, dpi=80)
    print('Spike overlay written to', out_path)
    print('control points: {}, spawn points: {}, spawners: {}'.format(
        len(parsed['control_points']), len(parsed['spawn_points']), len(parsed['vehicle_spawners'])))
    print('sea_level_m:', sea_level, '| water cells: {:.1f}% of heightmap'.format(100.0 * water.mean()))
    return 0


def _layer_tag(mode, size):
    # cpname_asad_khal_aas32_... -> mode gpm_cq size 32 gives tag "aas32"
    tags = {'gpm_cq': 'aas', 'gpm_coop': 'coop', 'gpm_skirmish': 'skirmish', 'gpm_gungame': 'gungame'}
    return '{}{}'.format(tags.get(mode, mode), size)


if __name__ == '__main__':
    sys.exit(main())
