#!/usr/bin/env python3
"""
Compress heightmap JSON files with gzip for reduced distribution size.

This script finds all heightmap.json files in processed_maps/ and creates
compressed .json.gz versions using gzip level 9 (maximum compression).

Usage:
    python compress_heightmaps.py
"""

import gzip
import pathlib
import sys

def compress_heightmaps():
    """Compress all heightmap.json files in processed_maps directory."""
    
    processed_maps_dir = pathlib.Path('processed_maps')
    
    if not processed_maps_dir.is_dir():
        print("ERROR: processed_maps directory not found")
        print(f"Expected location: {processed_maps_dir.absolute()}")
        sys.exit(1)
    
    # Find all heightmap.json files
    heightmap_files = list(processed_maps_dir.rglob('heightmap.json'))
    
    if not heightmap_files:
        print("WARNING: No heightmap.json files found")
        sys.exit(0)
    
    print(f"Found {len(heightmap_files)} heightmap files")
    print("Compressing with gzip level 9 (maximum)...\n")
    
    total_original_size = 0
    total_compressed_size = 0
    
    for json_file in heightmap_files:
        # Read original file
        original_data = json_file.read_text()
        original_size = len(original_data)
        
        # Compress with gzip level 9
        output_file = json_file.with_suffix('.json.gz')
        with gzip.open(output_file, 'wt', compresslevel=9) as f:
            f.write(original_data)
        
        compressed_size = output_file.stat().st_size
        ratio = compressed_size / original_size
        saved = (1 - ratio) * 100
        
        # Update totals
        total_original_size += original_size
        total_compressed_size += compressed_size
        
        # Print progress
        map_name = json_file.parent.name
        print(f"  {map_name:30} {original_size/1024/1024:>6.1f}MB -> {compressed_size/1024/1024:>6.1f}MB  (saved {saved:>5.1f}%)")
    
    # Print summary
    print("\n" + "="*80)
    total_ratio = total_compressed_size / total_original_size
    total_saved = (1 - total_ratio) * 100
    print(f"Total: {total_original_size/1024/1024:.1f}MB -> {total_compressed_size/1024/1024:.1f}MB")
    print(f"Overall compression: {total_saved:.1f}% savings")
    print("="*80)
    print(f"\nCompressed {len(heightmap_files)} files successfully!")

if __name__ == '__main__':
    compress_heightmaps()
