#!/usr/bin/env python3
"""
Process a single map from raw_map_data to processed_maps for testing
"""
import zipfile
from pathlib import Path
import json
import re
import subprocess
import sys

# Ensure numpy is available
try:
    import numpy as np
except ImportError:
    print('NumPy not found, installing...')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'numpy'], check=True)
    import numpy as np


def extract_heightmap_raw(zip_path: Path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        heightmap_file = None
        for name in zf.namelist():
            if 'heightmapprimary.raw' in name.lower():
                heightmap_file = name
                break
        if not heightmap_file:
            raise Exception('heightmapprimary.raw not found')
        raw_data = zf.read(heightmap_file)
        num_pixels = len(raw_data) // 2
        resolution = int(np.sqrt(num_pixels))
        heightmap_1d = np.frombuffer(raw_data, dtype='<u2')
        heightmap_2d = heightmap_1d.reshape((resolution, resolution))
        return heightmap_2d


def extract_config_files(zip_path: Path):
    init_con = None
    terrain_con = None
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('init.con'):
                init_con = zf.read(name).decode('utf-8', errors='ignore')
            elif name.endswith('terrain.con'):
                terrain_con = zf.read(name).decode('utf-8', errors='ignore')
    return init_con, terrain_con


def parse_init_con(content: str):
    if not content:
        return None
    match = re.search(r'heightmapCluster\.create\s+(\d+)\s+(\d+)', content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_terrain_con(content: str):
    if not content:
        return None
    match = re.search(r'HeightmapCluster\.setHeightScale\s+(\d+\.?\d*)', content, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def convert_to_json(heightmap: np.ndarray, output_json: Path):
    resolution = heightmap.shape[0]
    data = {
        'resolution': resolution,
        'width': resolution,
        'height': resolution,
        'format': 'uint16',
        'data': heightmap.flatten().tolist(),
        'compression': 'none'
    }
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))


def generate_metadata(map_name: str, heightmap: np.ndarray, map_size: int, height_scale: float, output_path: Path):
    resolution = heightmap.shape[0]
    meters_per_pixel = map_size / (resolution - 1)
    grid_scale = map_size / 13
    metadata = {
        'map_name': map_name,
        'map_size': map_size,
        'height_scale': height_scale,
        'grid_scale': grid_scale,
        'heightmap_resolution': resolution,
        'meters_per_pixel': meters_per_pixel,
        'processed_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'format_version': '1.0'
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)


if __name__ == '__main__':
    repo_root = Path(__file__).parent.parent
    raw_dir = repo_root / 'raw_map_data'
    processed_dir = repo_root / 'processed_maps'
    processed_dir.mkdir(exist_ok=True)

    map_name = 'adak'
    zip_path = raw_dir / map_name / 'server.zip'
    if not zip_path.exists():
        print('Zip file not found:', zip_path)
        sys.exit(1)

    print('Processing map:', map_name)
    heightmap = extract_heightmap_raw(zip_path)
    print('resolution:', heightmap.shape)
    init_con, terrain_con = extract_config_files(zip_path)
    map_size = parse_init_con(init_con) or (2048 if heightmap.shape[0] == 1025 else 4096)
    height_scale = parse_terrain_con(terrain_con) or 300
    print('map_size:', map_size, 'height_scale:', height_scale)

    out_dir = processed_dir / map_name
    out_dir.mkdir(exist_ok=True, parents=True)
    heightmap_json_path = out_dir / 'heightmap.json'
    convert_to_json(heightmap, heightmap_json_path)
    
    # Compress heightmap to .gz format
    print('Compressing heightmap...')
    import gzip
    original_data = heightmap_json_path.read_text()
    with gzip.open(out_dir / 'heightmap.json.gz', 'wt', compresslevel=9) as f:
        f.write(original_data)
    # Delete uncompressed version
    heightmap_json_path.unlink()
    print('Heightmap compressed to .json.gz')
    
    generate_metadata(map_name, heightmap, map_size, height_scale, out_dir / 'metadata.json')

    print('Done. Output directory:', out_dir)
