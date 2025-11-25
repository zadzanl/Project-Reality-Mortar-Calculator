#!/usr/bin/env python3
"""Unit tests for contour map generation functions.

Tests the heightmap loading, elevation normalization, resolution matching,
and metadata update functions used by generate_contours.ipynb.
"""

import json
import gzip
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
import numpy as np


# Import functions from the notebook (simulated here since notebook functions
# need to be extracted or the notebook run first)
# For testing, we re-implement the core functions


def load_heightmap(map_path: Path) -> np.ndarray:
    """Load heightmap from compressed JSON file."""
    heightmap_file = map_path / 'heightmap.json.gz'
    
    if not heightmap_file.exists():
        raise FileNotFoundError(f"heightmap.json.gz not found at {heightmap_file}")
    
    with gzip.open(heightmap_file, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    
    resolution = data['resolution']
    heightmap_1d = np.array(data['data'], dtype=np.uint16)
    heightmap_2d = heightmap_1d.reshape((resolution, resolution))
    
    return heightmap_2d


def normalize_elevation(heightmap: np.ndarray, height_scale: float) -> np.ndarray:
    """Convert raw heightmap values to actual elevation in meters.
    
    Formula: elevation_meters = (raw_value / 65535.0) * height_scale
    """
    return (heightmap.astype(np.float64) / 65535.0) * height_scale


def match_minimap_resolution(elevation_array: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    """Resize elevation array to match minimap resolution using bilinear interpolation."""
    from scipy.ndimage import zoom
    
    current_height, current_width = elevation_array.shape
    
    if current_width == target_width and current_height == target_height:
        return elevation_array
    
    zoom_y = target_height / current_height
    zoom_x = target_width / current_width
    
    resized = zoom(elevation_array, (zoom_y, zoom_x), order=1)
    return resized


def update_metadata(map_path: Path, contour_info: dict) -> bool:
    """Update metadata.json with contour map information."""
    metadata_path = map_path / 'metadata.json'
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    metadata['contourmap'] = contour_info
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return True


# ============================================
# Test: Heightmap Loading
# ============================================

class TestHeightmapLoading:
    """Tests for load_heightmap() function."""
    
    def test_load_valid_heightmap(self, tmp_path):
        """Test loading a valid gzipped JSON heightmap."""
        # Create test heightmap data
        resolution = 5
        data = list(range(resolution * resolution))  # 0, 1, 2, ..., 24
        
        heightmap_data = {
            'resolution': resolution,
            'width': resolution,
            'height': resolution,
            'format': 'uint16',
            'data': data,
            'compression': 'none'
        }
        
        # Write gzipped JSON
        heightmap_path = tmp_path / 'heightmap.json.gz'
        with gzip.open(heightmap_path, 'wt', encoding='utf-8') as f:
            json.dump(heightmap_data, f)
        
        # Load and verify
        result = load_heightmap(tmp_path)
        
        assert result.shape == (resolution, resolution)
        assert result.dtype == np.uint16
        assert result[0, 0] == 0
        assert result[0, 4] == 4
        assert result[4, 4] == 24
    
    def test_load_missing_file(self, tmp_path):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_heightmap(tmp_path)
    
    def test_load_corrupted_data(self, tmp_path):
        """Test loading corrupted/invalid data raises error."""
        heightmap_path = tmp_path / 'heightmap.json.gz'
        with gzip.open(heightmap_path, 'wt', encoding='utf-8') as f:
            f.write('not valid json {{{')
        
        with pytest.raises(json.JSONDecodeError):
            load_heightmap(tmp_path)


# ============================================
# Test: Elevation Normalization
# ============================================

class TestElevationNormalization:
    """Tests for normalize_elevation() function."""
    
    def test_min_value_zero(self):
        """Test raw_value=0 gives 0.0m elevation."""
        heightmap = np.array([[0]], dtype=np.uint16)
        height_scale = 300
        
        result = normalize_elevation(heightmap, height_scale)
        
        assert result[0, 0] == 0.0
    
    def test_max_value_full_scale(self):
        """Test raw_value=65535 gives height_scale elevation."""
        heightmap = np.array([[65535]], dtype=np.uint16)
        height_scale = 300
        
        result = normalize_elevation(heightmap, height_scale)
        
        assert result[0, 0] == pytest.approx(300.0, rel=1e-5)
    
    def test_mid_value_half_scale(self):
        """Test raw_value=32768 gives approximately half height_scale."""
        heightmap = np.array([[32768]], dtype=np.uint16)
        height_scale = 300
        
        result = normalize_elevation(heightmap, height_scale)
        
        # 32768 / 65535 * 300 = ~150.0
        expected = (32768 / 65535.0) * 300
        assert result[0, 0] == pytest.approx(expected, rel=1e-5)
    
    def test_array_shape_preserved(self):
        """Test input and output array shapes match."""
        heightmap = np.array([[0, 100], [200, 300]], dtype=np.uint16)
        height_scale = 300
        
        result = normalize_elevation(heightmap, height_scale)
        
        assert result.shape == heightmap.shape
    
    def test_different_height_scales(self):
        """Test normalization with various height_scale values."""
        heightmap = np.array([[65535]], dtype=np.uint16)
        
        for height_scale in [100, 200, 500, 1000]:
            result = normalize_elevation(heightmap, height_scale)
            assert result[0, 0] == pytest.approx(float(height_scale), rel=1e-5)


# ============================================
# Test: Resolution Matching
# ============================================

class TestResolutionMatching:
    """Tests for match_minimap_resolution() function."""
    
    def test_upscaling(self):
        """Test upscaling from 1025x1025 to 2048x2048."""
        elevation = np.random.rand(1025, 1025)
        
        result = match_minimap_resolution(elevation, 2048, 2048)
        
        assert result.shape == (2048, 2048)
    
    def test_downscaling(self):
        """Test downscaling from 2049x2049 to 1024x1024."""
        elevation = np.random.rand(2049, 2049)
        
        result = match_minimap_resolution(elevation, 1024, 1024)
        
        assert result.shape == (1024, 1024)
    
    def test_same_resolution(self):
        """Test no change when resolution already matches."""
        elevation = np.random.rand(2048, 2048)
        
        result = match_minimap_resolution(elevation, 2048, 2048)
        
        assert result.shape == (2048, 2048)
        # Should return same array (or copy with same values)
        np.testing.assert_array_equal(result, elevation)
    
    def test_non_square_target(self):
        """Test handling non-square target dimensions."""
        elevation = np.random.rand(100, 100)
        
        result = match_minimap_resolution(elevation, 200, 150)
        
        assert result.shape == (150, 200)


# ============================================
# Test: Contour Level Calculation
# ============================================

class TestContourLevelCalculation:
    """Tests for contour level calculations."""
    
    def test_thin_levels_5m_interval(self):
        """Test thin levels every 5m for 0-100m range."""
        min_elev = 0
        max_elev = 100
        
        thin_levels = np.arange(min_elev, max_elev + 5, 5)
        
        assert thin_levels[0] == 0
        assert thin_levels[-1] == 100
        assert len(thin_levels) == 21  # 0, 5, 10, ..., 100
        assert np.all(np.diff(thin_levels) == 5)
    
    def test_thick_levels_15m_interval(self):
        """Test thick levels every 15m for 0-300m range."""
        min_elev = 0
        max_elev = 300
        
        thick_levels = np.arange(min_elev, max_elev + 15, 15)
        
        assert thick_levels[0] == 0
        assert thick_levels[-1] == 300
        assert len(thick_levels) == 21  # 0, 15, 30, ..., 300
        assert np.all(np.diff(thick_levels) == 15)
    
    def test_levels_with_offset_elevation(self):
        """Test levels when min elevation is not zero."""
        min_elev = 50
        max_elev = 200
        
        thin_levels = np.arange(min_elev, max_elev + 5, 5)
        thick_levels = np.arange(min_elev, max_elev + 15, 15)
        
        assert thin_levels[0] == 50
        assert thick_levels[0] == 50


# ============================================
# Test: Metadata Update
# ============================================

class TestMetadataUpdate:
    """Tests for update_metadata() function."""
    
    def test_adds_contourmap_field(self, tmp_path):
        """Test that contourmap field is added to metadata."""
        # Create initial metadata
        initial_metadata = {
            'map_name': 'test_map',
            'map_size': 2048,
            'height_scale': 300,
            'grid_scale': 157.54,
            'heightmap_resolution': 1025,
            'processed_at': '2025-01-01T00:00:00Z',
            'format_version': '1.0'
        }
        
        metadata_path = tmp_path / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(initial_metadata, f)
        
        # Add contourmap info
        contour_info = {
            'file': 'contourmap.png',
            'resolution': '2048x2048',
            'generated_at': '2025-01-02T00:00:00Z',
            'thin_interval_m': 5,
            'thick_interval_m': 15
        }
        
        result = update_metadata(tmp_path, contour_info)
        
        assert result is True
        
        # Read and verify
        with open(metadata_path, 'r', encoding='utf-8') as f:
            updated = json.load(f)
        
        assert 'contourmap' in updated
        assert updated['contourmap']['file'] == 'contourmap.png'
        assert updated['contourmap']['resolution'] == '2048x2048'
        assert updated['contourmap']['thin_interval_m'] == 5
        assert updated['contourmap']['thick_interval_m'] == 15
    
    def test_preserves_existing_fields(self, tmp_path):
        """Test that existing fields are preserved after update."""
        initial_metadata = {
            'map_name': 'test_map',
            'map_size': 2048,
            'height_scale': 300,
            'custom_field': 'should be preserved'
        }
        
        metadata_path = tmp_path / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(initial_metadata, f)
        
        contour_info = {'file': 'contourmap.png'}
        update_metadata(tmp_path, contour_info)
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            updated = json.load(f)
        
        assert updated['map_name'] == 'test_map'
        assert updated['map_size'] == 2048
        assert updated['height_scale'] == 300
        assert updated['custom_field'] == 'should be preserved'
    
    def test_valid_json_after_update(self, tmp_path):
        """Test that JSON is valid after update."""
        initial_metadata = {'map_name': 'test_map'}
        
        metadata_path = tmp_path / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(initial_metadata, f)
        
        contour_info = {'file': 'contourmap.png'}
        update_metadata(tmp_path, contour_info)
        
        # Should not raise
        with open(metadata_path, 'r', encoding='utf-8') as f:
            updated = json.load(f)
        
        assert isinstance(updated, dict)


# ============================================
# Run tests
# ============================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
