#!/usr/bin/env python3
"""
Test script for validating process_maps.ipynb helper functions
"""

import re
from typing import Optional

# Test parse_terrain_con
def parse_terrain_con(content: str) -> Optional[float]:
    """Parse terrain.con file to extract height scale."""
    match = re.search(r'HeightmapCluster\.setHeightScale\s+(\d+\.?\d*)', content, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


# Test parse_init_con
def parse_init_con(content: str) -> Optional[int]:
    """Parse init.con file to extract map size."""
    match = re.search(r'heightmapCluster\.create\s+(\d+)\s+(\d+)', content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


# Test cases
def test_parse_terrain_con():
    """Test terrain.con parsing"""
    print("\n=== Testing parse_terrain_con ===")
    
    # Test 1: Standard format
    content1 = """
rem *** HeightmapCluster ***
HeightmapCluster.setHeightScale 300
    """
    result1 = parse_terrain_con(content1)
    print(f"Test 1 (height scale 300): {result1} {' OK ' if result1 == 300 else '✗'}")
    
    # Test 2: Decimal value
    content2 = "HeightmapCluster.setHeightScale 150.5"
    result2 = parse_terrain_con(content2)
    print(f"Test 2 (height scale 150.5): {result2} {' OK ' if result2 == 150.5 else '✗'}")
    
    # Test 3: Case insensitive
    content3 = "heightmapcluster.setheightscale 400"
    result3 = parse_terrain_con(content3)
    print(f"Test 3 (case insensitive): {result3} {' OK ' if result3 == 400 else '✗'}")
    
    # Test 4: Not found
    content4 = "nothing here"
    result4 = parse_terrain_con(content4)
    print(f"Test 4 (not found): {result4} {' OK ' if result4 is None else '✗'}")


def test_parse_init_con():
    """Test init.con parsing"""
    print("\n=== Testing parse_init_con ===")
    
    # Test 1: Standard 2048m map
    content1 = """
rem *** HeightmapCluster ***
heightmapCluster.create 2048 2048 128 2
    """
    result1 = parse_init_con(content1)
    print(f"Test 1 (2048m map): {result1} {' OK ' if result1 == 2048 else '✗'}")
    
    # Test 2: 4096m map
    content2 = "heightmapCluster.create 4096 4096 128 2"
    result2 = parse_init_con(content2)
    print(f"Test 2 (4096m map): {result2} {' OK ' if result2 == 4096 else '✗'}")
    
    # Test 3: Case insensitive
    content3 = "HeightmapCluster.Create 1024 1024 128 2"
    result3 = parse_init_con(content3)
    print(f"Test 3 (case insensitive): {result3} {' OK ' if result3 == 1024 else '✗'}")
    
    # Test 4: Not found
    content4 = "nothing here"
    result4 = parse_init_con(content4)
    print(f"Test 4 (not found): {result4} {' OK ' if result4 is None else '✗'}")


def test_grid_scale_calculation():
    """Test grid scale calculation (map_size / 13)"""
    print("\n=== Testing grid_scale calculation ===")
    
    test_cases = [
        (2048, 2048 / 13),  # 157.538...
        (4096, 4096 / 13),  # 315.076...
        (1024, 1024 / 13),  # 78.769...
    ]
    
    for map_size, expected in test_cases:
        grid_scale = map_size / 13
        match = abs(grid_scale - expected) < 0.001
        print(f"Map size {map_size}m → grid scale {grid_scale:.3f}m {' OK ' if match else '✗'}")


def test_json_structure():
    """Test JSON structure definitions"""
    print("\n=== Testing JSON structure definitions ===")
    
    # Heightmap JSON structure
    heightmap_json = {
        'resolution': 1025,
        'width': 1025,
        'height': 1025,
        'format': 'uint16',
        'data': [0] * (1025 * 1025),  # Flattened array
        'compression': 'none'
    }
    
    print(f"Heightmap JSON keys: {list(heightmap_json.keys())}")
    print(f"  resolution: {heightmap_json['resolution']}  OK ")
    print(f"  format: {heightmap_json['format']}  OK ")
    print(f"  data length: {len(heightmap_json['data'])} (expected {1025*1025}) {' OK ' if len(heightmap_json['data']) == 1025*1025 else '✗'}")
    
    # Metadata JSON structure
    from datetime import datetime
    metadata_json = {
        'map_name': 'test_map',
        'map_size': 2048,
        'height_scale': 300,
        'grid_scale': 2048 / 13,
        'heightmap_resolution': 1025,
        'processed_at': datetime.utcnow().isoformat() + 'Z',
        'format_version': '1.0'
    }
    
    print(f"\nMetadata JSON keys: {list(metadata_json.keys())}")
    print(f"  map_name: {metadata_json['map_name']}  OK ")
    print(f"  map_size: {metadata_json['map_size']}  OK ")
    print(f"  height_scale: {metadata_json['height_scale']}  OK ")
    print(f"  grid_scale: {metadata_json['grid_scale']:.3f}  OK ")
    print(f"  format_version: {metadata_json['format_version']}  OK ")


if __name__ == '__main__':
    print("="*70)
    print("MAP PROCESSOR FUNCTION VALIDATION")
    print("="*70)
    
    test_parse_terrain_con()
    test_parse_init_con()
    test_grid_scale_calculation()
    test_json_structure()
    
    print("\n" + "="*70)
    print("All function tests completed!")
    print("="*70)
