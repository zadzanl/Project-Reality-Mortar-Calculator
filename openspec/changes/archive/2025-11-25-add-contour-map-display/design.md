# Design: Contour Map Generation and Display

## Context

The mortar calculator displays maps using Leaflet.js with `minimap.png` as a base layer. Users need elevation context to make tactical decisions. This change adds contour map generation and a layer toggle system.

**Constraints:**
- Offline operation required (no external APIs)
- Must use ONLY ASCII characters in all code and output
- Processing runs in Jupyter notebook (Google Colab or local)
- Output must be PNG format for Leaflet compatibility
- Contour maps are precomputed (NOT generated at runtime)

## Goals / Non-Goals

**Goals:**
- Generate military-style contour maps from heightmap data
- Match minimap.png resolution for pixel-perfect overlay
- Allow users to toggle between terrain and contour views
- Support simultaneous display of both layers
- Update metadata.json with contour map path

**Non-Goals:**
- Real-time contour generation in browser
- 3D terrain visualization
- Custom contour interval configuration in UI

## Decisions

### Decision 1: Contour Generation Library

**Choice:** Use `matplotlib` with `contour()` and `contourf()` functions.

**Alternatives considered:**
- OpenCV `findContours()` - Lower level, more complex for labeled contours
- Custom implementation - Too time-consuming, reinvents the wheel
- Pillow only - No built-in contour support

**Rationale:** Matplotlib provides contour labeling, line thickness control, and color map support out of the box. It is already commonly available in Colab environments.

### Decision 2: Color Scheme

**Choice:** Blue (sea level) -> Green (lowland) -> Yellow (highland) -> Red (peaks)

**Implementation:** Create custom matplotlib colormap with these gradient stops:
- 0.0: Blue (#0000FF) - sea level / lowest elevation
- 0.33: Green (#00FF00) - lowland
- 0.66: Yellow (#FFFF00) - highland
- 1.0: Red (#FF0000) - peaks / highest elevation

### Decision 3: Contour Line Intervals (Normalized Elevation)

**Choice:** 
- Thin lines: Every 5 meters of elevation change
- Thick lines: Every 15 meters of elevation change
- Labels: On thick lines only, at regular spacing along the line

**Elevation Normalization Formula:**
```
elevation_meters = (raw_value / 65535.0) * height_scale
```
Where:
- `raw_value` = uint16 value from heightmap (0-65535)
- `height_scale` = maximum elevation from metadata.json (e.g., 300 meters)
- `elevation_meters` = actual elevation in meters

**Contour Level Calculation:**
```python
min_elev = elevation_array.min()
max_elev = elevation_array.max()
thin_levels = np.arange(min_elev, max_elev + 5, 5)    # Every 5m
thick_levels = np.arange(min_elev, max_elev + 15, 15)  # Every 15m
```

**Rationale:** Matches military topographic map standards. 5m provides detail, 15m provides quick reference points.

### Decision 4: Resolution Matching and Interpolation

**Choice:** Upscale heightmap to match minimap resolution using bilinear interpolation.

**Problem:** Heightmap resolution (1025x1025 or 2049x2049) may differ from minimap resolution (1024x1024, 2048x2048, or 4096x4096).

**Solution:**
1. Read minimap.png dimensions
2. If heightmap resolution differs, use `scipy.ndimage.zoom()` or `numpy` interpolation
3. Generate contour at minimap resolution
4. Output PNG matches minimap pixel-for-pixel

**Interpolation Method:** Bilinear interpolation preserves smooth terrain transitions.

### Decision 5: Layer System Architecture

**Choice:** Two independent Leaflet `ImageOverlay` layers with checkbox controls.

**Implementation:**
- `terrainLayer`: Loads `minimap.png`, z-index lower
- `contourLayer`: Loads `contourmap.png`, z-index higher
- When both ON: Reduce contour layer opacity to 0.7
- When contour only: Full opacity (1.0)

### Decision 6: Metadata Update

**Choice:** Add `contourmap` field to `metadata.json` after generation.

**Updated metadata.json structure:**
```json
{
  "map_name": "korengal",
  "map_size": 2048,
  "height_scale": 300,
  "grid_scale": 157.538,
  "heightmap_resolution": 1025,
  "processed_at": "2025-11-19T08:56:23.801194Z",
  "format_version": "1.0",
  "contourmap": {
    "file": "contourmap.png",
    "resolution": "2048x2048",
    "generated_at": "2025-11-25T12:00:00.000000Z",
    "thin_interval_m": 5,
    "thick_interval_m": 15
  }
}
```

### Decision 7: UI Checkbox Placement

**Choice:** Place layer checkboxes below the hint box, aligned with "Show Grid" checkbox.

**HTML Structure:**
```html
<div class="calculator__hint">
  <small><strong>Tip:</strong> Click map to place target...</small>
</div>

<div class="calculator__grid-toggle">
  <label>
    <input type="checkbox" id="grid-labels-toggle">
    <span>Show Grid</span>
  </label>
</div>

<!-- NEW: Layer toggle section -->
<div class="calculator__layer-toggles">
  <label>
    <input type="checkbox" id="terrain-layer-toggle" checked>
    <span>Terrain Map</span>
  </label>
  <label>
    <input type="checkbox" id="contour-layer-toggle">
    <span>Contour Map</span>
  </label>
</div>
```

## Data Flow

```
heightmap.json.gz
       |
       v
[generate_contours.ipynb]
       |
       +-- Read and decompress heightmap (uint16 array)
       +-- Read metadata.json for height_scale
       +-- Read minimap.png for target resolution
       +-- Normalize elevation: (raw / 65535) * height_scale
       +-- Interpolate heightmap to match minimap resolution
       +-- Generate filled contour (heat map background)
       +-- Generate thin contour lines (every 5m elevation)
       +-- Generate thick contour lines (every 15m elevation)
       +-- Add elevation labels on thick lines
       +-- Save as contourmap.png (same resolution as minimap)
       +-- Update metadata.json with contourmap info
       |
       v
  processed_maps/<map_name>/
       +-- contourmap.png (NEW)
       +-- metadata.json (UPDATED)
       |
       v
[Web UI - Leaflet]
       |
       +-- Load minimap.png as terrainLayer
       +-- Load contourmap.png as contourLayer
       +-- Toggle visibility via checkboxes
```

## File Structure

```
processor/
    generate_contours.ipynb        # NEW: Contour generation notebook
    tests/
        test_contour_generation.py # NEW: Unit tests for contour generation

processed_maps/
    [map_name]/
        heightmap.json.gz          # Existing
        metadata.json              # MODIFIED: Add contourmap field
        minimap.png                # Existing
        contourmap.png             # NEW: Generated contour map

calculator/
    templates/
        index.html                 # MODIFIED: Add layer checkboxes
    static/
        js/
            app.js                 # MODIFIED: Layer toggle logic
        css/
            styles.css             # MODIFIED: Checkbox styling
    tests/
        test_layer_toggle.js       # NEW: UI layer toggle tests (if applicable)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large PNG file sizes | Use PNG compression, match minimap resolution |
| Slow contour generation | Process all maps in batch, precompute once |
| Label text rendering issues | Use matplotlib's built-in clabel with ASCII only |
| Color contrast issues | Test on multiple maps, use proven color scheme |
| Resolution mismatch | Interpolate heightmap to match minimap exactly |
| Metadata corruption | Validate JSON after update, backup original |

## Migration Plan

1. Create `generate_contours.ipynb` notebook
2. Create unit tests for contour generation
3. Run notebook to generate `contourmap.png` for all maps
4. Verify metadata.json updated for all maps
5. Update UI with layer checkboxes
6. Add UI tests for layer toggle
7. Commit processed maps with new contour images

**Rollback:** Delete `contourmap.png` files, remove `contourmap` field from metadata.json, revert UI changes. No data loss risk.

## Open Questions

None - all questions resolved in requirements gathering.

