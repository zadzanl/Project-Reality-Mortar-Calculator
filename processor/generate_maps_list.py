#!/usr/bin/env python3
"""
Auto-generate mapsList.json from processed_maps directory contents.

This script scans the processed_maps/ directory for subdirectories
containing metadata.json files, then generates a JSON file listing
all available maps in the correct format for the Flask /maps/list endpoint.
"""
import json
from pathlib import Path


def generate_maps_list():
    """Generate mapsList.json from processed_maps directory."""
    # Get paths
    repo_root = Path(__file__).parent.parent
    processed_maps_dir = repo_root / 'processed_maps'
    output_file = repo_root / 'mapsList.json'

    # Scan for maps
    maps = []
    if processed_maps_dir.is_dir():
        for item in processed_maps_dir.iterdir():
            if item.is_dir():
                metadata_file = item / 'metadata.json'
                if metadata_file.is_file():
                    maps.append({
                        'name': item.name,
                        'path': item.name
                    })
                else:
                    print(f'Skipped {item.name}: no metadata.json')
    else:
        print(f'Warning: {processed_maps_dir} does not exist')

    # Sort alphabetically
    maps.sort(key=lambda x: x['name'])

    # Create output structure (match Flask /maps/list schema)
    output = {
        'count': len(maps),
        'maps': maps
    }

    # Write to file with 4-space indentation
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=4)

    print(f'Generated mapsList.json with {len(maps)} maps')


if __name__ == '__main__':
    generate_maps_list()
