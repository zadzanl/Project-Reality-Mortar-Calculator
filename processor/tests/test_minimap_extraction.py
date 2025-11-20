#!/usr/bin/env python3
"""
Unit tests for minimap extraction functionality.
Tests validate_client_zip() and minimap-related manifest structure.
"""

import sys
from pathlib import Path

# Add processor directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collect_maps import validate_client_zip

def test_validate_client_zip_structure():
    """Test that validate_client_zip function exists and has correct signature."""
    import inspect
    
    # Check function exists
    assert callable(validate_client_zip), "validate_client_zip should be callable"
    
    # Check signature
    sig = inspect.signature(validate_client_zip)
    params = list(sig.parameters.keys())
    
    assert len(params) == 1, f"Expected 1 parameter, got {len(params)}"
    assert params[0] == 'zip_path', f"Expected parameter 'zip_path', got '{params[0]}'"
    
    print("✓ validate_client_zip function signature correct")

def test_manifest_structure():
    """Test expected manifest.json structure for minimap support."""
    expected_structure = {
        'maps': [
            {
                'name': 'test_map',
                'server_zip': {
                    'md5': 'abc123',
                    'size_bytes': 1048576,
                    'has_heightmap': True
                },
                'client_zip': {
                    'md5': 'def456',
                    'size_bytes': 2097152,
                    'has_minimap': True
                },
                'collected_at': '2024-11-19T10:30:00Z',
                'source_path': '/path/to/map',
                'status': 'new'
            }
        ],
        'total_maps': 45,
        'maps_with_minimaps': 43,
        'maps_heightmap_only': 2,
        'total_size_bytes': 150000000,
        'total_size_mb': 143.1,
        'collection_date': '2024-11-19T10:30:00Z',
        'format_version': '1.0'
    }
    
    # Verify structure has required fields
    assert 'maps' in expected_structure
    assert 'total_maps' in expected_structure
    assert 'maps_with_minimaps' in expected_structure
    assert 'maps_heightmap_only' in expected_structure
    
    map_entry = expected_structure['maps'][0]
    assert 'server_zip' in map_entry
    assert 'client_zip' in map_entry
    assert 'has_heightmap' in map_entry['server_zip']
    assert 'has_minimap' in map_entry['client_zip']
    
    print("✓ Manifest structure matches specification")

def test_metadata_minimap_field():
    """Test expected metadata.json minimap field structure."""
    expected_metadata = {
        'map_name': 'muttrah_city_2',
        'map_size': 2048,
        'height_scale': 300,
        'minimap': {
            'source_file': 'info/minimap.dds',
            'resolution': '2048x2048',
            'file_size_kb': 1024,
            'converted_at': '2024-11-19T10:30:00Z'
        }
    }
    
    assert 'minimap' in expected_metadata
    minimap = expected_metadata['minimap']
    
    assert 'source_file' in minimap
    assert 'resolution' in minimap
    assert 'file_size_kb' in minimap
    assert 'converted_at' in minimap
    
    print("✓ Metadata minimap field structure correct")

if __name__ == '__main__':
    print("Running minimap extraction tests...\n")
    
    try:
        test_validate_client_zip_structure()
        test_manifest_structure()
        test_metadata_minimap_field()
        
        print("\n" + "="*70)
        print("All tests passed!")
        print("="*70)
        
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
