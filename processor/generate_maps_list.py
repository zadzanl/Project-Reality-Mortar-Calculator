#!/usr/bin/env python3
"""Generate repository-root mapsList.json from processed_maps directory.

ROLE: Maintainer-only utility for Android/offline releases.
INPUTS:
    - processed_maps/<map>/metadata.json
OUTPUTS:
    - mapsList.json (repository root manifest for mobile app)
HOW TO RUN:
    python processor/generate_maps_list.py
DID IT WORK CHECK:
    Prints 'Generated mapsList.json with <count> maps'.
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
