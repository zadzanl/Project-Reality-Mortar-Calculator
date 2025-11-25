# Proposal: Add Contour Map Display

## Why

Players need terrain elevation information to plan mortar positions effectively. The current minimap shows satellite imagery but lacks elevation data. A contour map helps players identify hills, valleys, and elevation changes at a glance.

## What Changes

1. **New Processing Notebook:** Create `processor/generate_contours.ipynb` to convert `heightmap.json.gz` into `contourmap.png` for each map.

2. **Contour Map Generation (Precomputed):**
   - Contour maps are precomputed at build time (NOT generated at runtime)
   - Output saved to `processed_maps/<map_name>/contourmap.png`
   - Update `metadata.json` to include contour map path
   - Resolution must match `minimap.png` quality (interpolate heightmap if needed)

3. **Contour Map Style:**
   - Elevation heat map background (blue -> green -> yellow -> red)
   - Thin contour lines every 5 meters of elevation change
   - Thick contour lines every 15 meters of elevation change
   - Elevation values normalized to actual meters using height_scale
   - Elevation labels on thick lines at regular spacing
   - Military topographic map styling

4. **UI Layer Controls:** Add two checkboxes in the results panel:
   - Location: Below the hint box ("Tip: Click map to place target...")
   - Alignment: Same style and alignment as existing "Show Grid" checkbox
   - "Terrain Map" checkbox (defaults ON) - shows `minimap.png`
   - "Contour Map" checkbox (defaults OFF) - shows `contourmap.png`
   - Both layers can display simultaneously (contour overlays minimap)
   - Contour opacity reduces to 70% when both layers are ON

5. **Tests:** Add unit tests for contour generation and UI layer toggle functionality.

## Impact

- **Affected specs:** `map-processor`, `calculator-ui`
- **Affected code:**
  - New file: `processor/generate_contours.ipynb`
  - New file: `processor/tests/test_contour_generation.py`
  - Modified: `calculator/templates/index.html` (add checkboxes)
  - Modified: `calculator/static/js/app.js` (layer toggle logic)
  - Modified: `calculator/static/css/styles.css` (checkbox styling)
- **Modified data files:** `processed_maps/[map_name]/metadata.json` (add contour path)
- **New output files:** `processed_maps/[map_name]/contourmap.png` for each map

## Terms and Definitions

- **Contour line:** A line on a map connecting points of equal elevation.
- **Contour interval:** The elevation difference between adjacent contour lines (5m for thin, 15m for thick).
- **Heightmap:** A grayscale image where pixel brightness represents terrain height.
- **Heat map:** A colored visualization where colors represent data values (here: elevation).
- **Overlay:** A transparent or semi-transparent layer displayed on top of another image.
- **Interpolation:** Filling in missing data points between known values to increase resolution.
- **Normalized elevation:** Raw heightmap values (0-65535) converted to actual meters using height_scale.
- **Precomputed:** Generated once during processing, then loaded at runtime (not calculated live).

