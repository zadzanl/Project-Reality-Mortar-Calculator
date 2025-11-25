# Tasks: Add Contour Map Display

## Before You Start (Required Reading)

Read these files to understand the codebase:

1. **`openspec/project.md`** - Read the "Tech Stack" and "Code Style Rules" sections.
2. **`processor/process_maps.ipynb`** - Study how heightmaps are loaded and processed.
3. **`calculator/static/js/app.js`** - Study the `initializeLeafletMap()` function and layer handling.
4. **`calculator/templates/index.html`** - Find the "Show Grid" checkbox location and the hint box above it.
5. **`processed_maps/[any_map]/metadata.json`** - Understand the metadata structure.
6. **`processed_maps/[any_map]/minimap.png`** - Check typical minimap resolution (1024x1024, 2048x2048, etc.).

## Critical Rules

- **ONLY ASCII CHARACTERS:** All code, comments, labels, and output must use ASCII characters only. Do NOT use Unicode symbols, special characters, or emojis.
- **Offline operation:** Do NOT add external API calls or CDN links.
- **Follow existing code style:** Match indentation, naming, and patterns in existing files.
- **Precomputed output:** Contour maps are generated ONCE during processing, then loaded at runtime.

---

## 1. Create Contour Generation Notebook

### 1.1 Create notebook file structure
- [x] Create new file: `processor/generate_contours.ipynb`
- [x] Add markdown cell: Title and purpose description
- [x] Add code cell: Imports (numpy, matplotlib, scipy, gzip, json, pathlib, PIL)

### 1.2 Implement heightmap loading function
- [x] Create function `load_heightmap(map_path)` that:
  - Reads `heightmap.json.gz` using gzip
  - Parses JSON and extracts `data` array
  - Reshapes to 2D array using `resolution` field
  - Returns numpy array of uint16 values (0-65535)

### 1.3 Implement elevation normalization function
- [x] Create function `normalize_elevation(heightmap, height_scale)` that:
  - Applies formula: `elevation_meters = (raw_value / 65535.0) * height_scale`
  - `raw_value` is uint16 (0-65535), `height_scale` is from metadata.json
  - Returns numpy array of elevation in meters

### 1.4 Implement resolution matching function
- [x] Create function `match_minimap_resolution(elevation_array, target_width, target_height)` that:
  - Uses scipy.ndimage.zoom or numpy interpolation
  - Upscales or downscales elevation array to match minimap.png dimensions
  - Uses bilinear interpolation to fill in-between points
  - Returns resized elevation array

### 1.5 Implement custom colormap
- [x] Create function `create_terrain_colormap()` that:
  - Creates matplotlib LinearSegmentedColormap
  - Gradient stops:
    - 0.0: Blue (#0000FF) - sea level / lowest
    - 0.33: Green (#00FF00) - lowland
    - 0.66: Yellow (#FFFF00) - highland
    - 1.0: Red (#FF0000) - peaks / highest
  - Returns colormap object

### 1.6 Implement contour generation function
- [x] Create function `generate_contour_image(elevation_array, output_path, target_resolution)` that:
  - Creates matplotlib figure at exact target resolution (match minimap.png)
  - Draws filled contour (heat map) using custom colormap
  - Calculates contour levels based on actual elevation range:
    - `thin_levels = np.arange(min_elev, max_elev + 5, 5)` (every 5m)
    - `thick_levels = np.arange(min_elev, max_elev + 15, 15)` (every 15m)
  - Draws thin contour lines every 5 meters (linewidth=0.5, color=dark gray)
  - Draws thick contour lines every 15 meters (linewidth=1.5, color=black)
  - Adds elevation labels on thick lines using `clabel()`:
    - Labels at regular spacing along lines
    - Use ASCII digits only (no Unicode)
    - Font size readable at normal zoom
  - Removes axes, margins, and padding (full-bleed image)
  - Saves as PNG with exact target resolution

### 1.7 Implement metadata update function
- [x] Create function `update_metadata(map_path, contour_info)` that:
  - Reads existing `metadata.json`
  - Adds `contourmap` field with:
    - `file`: "contourmap.png"
    - `resolution`: "{width}x{height}"
    - `generated_at`: ISO 8601 timestamp
    - `thin_interval_m`: 5
    - `thick_interval_m`: 15
  - Writes updated JSON back to file
  - Preserves existing fields

### 1.8 Implement batch processing loop
- [x] Create cell that:
  - Discovers all map folders in `processed_maps/`
  - For each map:
    1. Load heightmap.json.gz
    2. Read metadata.json for height_scale
    3. Read minimap.png for target resolution (or use default if missing)
    4. Normalize elevation to meters
    5. Interpolate to match minimap resolution
    6. Generate contour image
    7. Save to `processed_maps/<map_name>/contourmap.png`
    8. Update metadata.json
  - Displays progress: "[1/45] Processing map_name..."
  - Handles errors gracefully (log and continue)
  - Reports summary at end (processed count, errors)

### 1.9 Test notebook execution
- [x] Run notebook on 3 sample maps (small, medium, large height_scale)
- [x] Verify `contourmap.png` is created in each map folder
- [x] Verify image dimensions match minimap.png exactly
- [x] Verify contour lines are visible and labels are readable
- [x] Verify metadata.json contains new `contourmap` field

---

## 2. Create Unit Tests for Contour Generation

### 2.1 Create test file
- [x] Create new file: `processor/tests/test_contour_generation.py`
- [x] Add imports: pytest, numpy, json, pathlib, tempfile

### 2.2 Test heightmap loading
- [x] Test `load_heightmap()` with valid gzipped JSON
- [x] Test `load_heightmap()` with missing file (expect error handling)
- [x] Test `load_heightmap()` with corrupted data (expect error handling)

### 2.3 Test elevation normalization
- [x] Test `normalize_elevation()` with known values:
  - Input: raw_value=0, height_scale=300 -> Output: 0.0m
  - Input: raw_value=65535, height_scale=300 -> Output: 300.0m
  - Input: raw_value=32768, height_scale=300 -> Output: ~150.0m
- [x] Test array input/output shapes match

### 2.4 Test resolution matching
- [x] Test `match_minimap_resolution()` upscaling (1025x1025 -> 2048x2048)
- [x] Test `match_minimap_resolution()` downscaling (2049x2049 -> 1024x1024)
- [x] Verify output dimensions match target exactly

### 2.5 Test contour level calculation
- [x] Test thin levels (5m interval) for elevation range 0-100m
- [x] Test thick levels (15m interval) for elevation range 0-300m
- [x] Verify level arrays are correct

### 2.6 Test metadata update
- [x] Test `update_metadata()` adds contourmap field
- [x] Test existing fields are preserved
- [x] Test JSON is valid after update

---

## 3. Update Web UI Layer Controls

### 3.1 Add layer toggle checkboxes to HTML
- [x] Open `calculator/templates/index.html`
- [x] Find the hint div: `<div class="calculator__hint">` with the "Tip: Click map..." text
- [x] Find the grid toggle div: `<div class="calculator__grid-toggle">`
- [x] Add new div AFTER grid toggle div with two checkboxes:
  ```html
  <div class="calculator__layer-toggles" style="margin-top: 0.75rem;">
    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
      <input type="checkbox" id="terrain-layer-toggle" checked style="cursor: pointer;">
      <span style="font-size: 0.875rem;">Terrain Map</span>
    </label>
    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin-top: 0.5rem;">
      <input type="checkbox" id="contour-layer-toggle" style="cursor: pointer;">
      <span style="font-size: 0.875rem;">Contour Map</span>
    </label>
  </div>
  ```
- [x] Use same styling pattern as existing "Show Grid" checkbox
- [x] Ensure alignment matches "Show Grid" checkbox

### 3.2 Add layer state to application state
- [x] Open `calculator/static/js/app.js`
- [x] Add to `state` object:
  ```javascript
  terrainLayer: null,      // Leaflet ImageOverlay for minimap
  contourLayer: null,      // Leaflet ImageOverlay for contour
  terrainVisible: true,    // Terrain checkbox state (default ON)
  contourVisible: false    // Contour checkbox state (default OFF)
  ```

### 3.3 Modify map initialization to create layers
- [x] In `initializeLeafletMap()` function:
  - Create `terrainLayer` as ImageOverlay loading `/maps/${mapName}/minimap.png`
  - Create `contourLayer` as ImageOverlay loading `/maps/${mapName}/contourmap.png`
  - Set terrain layer z-index lower than contour layer
  - Add terrain layer to map (visible by default)
  - Do NOT add contour layer initially (hidden by default)
  - Handle missing `contourmap.png` gracefully:
    - Try to load image
    - On error: log warning, disable contour checkbox, add "(unavailable)" to label

### 3.4 Implement layer toggle functions
- [x] Create function `toggleTerrainLayer(visible)` that:
  - If visible: add terrainLayer to map
  - If not visible: remove terrainLayer from map
  - Updates `state.terrainVisible`
  - Calls `updateContourOpacity()` after toggle

- [x] Create function `toggleContourLayer(visible)` that:
  - If visible: add contourLayer to map
  - If not visible: remove contourLayer from map
  - Updates `state.contourVisible`
  - Calls `updateContourOpacity()` after toggle

- [x] Create function `updateContourOpacity()` that:
  - If both layers visible (`state.terrainVisible && state.contourVisible`):
    - Set contour layer opacity to 0.7
  - If contour only (`!state.terrainVisible && state.contourVisible`):
    - Set contour layer opacity to 1.0

### 3.5 Add event listeners for checkboxes
- [x] In `setupEventListeners()` function:
  - Add change listener for `terrain-layer-toggle` checkbox:
    ```javascript
    document.getElementById('terrain-layer-toggle').addEventListener('change', (e) => {
      toggleTerrainLayer(e.target.checked);
    });
    ```
  - Add change listener for `contour-layer-toggle` checkbox:
    ```javascript
    document.getElementById('contour-layer-toggle').addEventListener('change', (e) => {
      toggleContourLayer(e.target.checked);
    });
    ```

### 3.6 Handle map reload correctly
- [x] When user selects new map and clicks "Load Map":
  - Remove existing terrain and contour layers from map
  - Set `state.terrainLayer = null` and `state.contourLayer = null`
  - Reset `state.terrainVisible = true` and `state.contourVisible = false`
  - Reset checkbox states to match:
    ```javascript
    document.getElementById('terrain-layer-toggle').checked = true;
    document.getElementById('contour-layer-toggle').checked = false;
    ```
  - Re-enable contour checkbox (in case it was disabled for previous map)
  - Create new layers for new map

---

## 4. Styling and Polish

### 4.1 Add CSS for layer toggles (if needed)
- [x] Open `calculator/static/css/styles.css`
- [x] Add styles for `.calculator__layer-toggles` container if inline styles are insufficient
- [x] Ensure checkboxes align properly in both light and dark themes

### 4.2 Test layer interactions
- [x] Test: Load map -> terrain visible, contour hidden, checkboxes match
- [x] Test: Toggle contour ON -> both layers visible, contour semi-transparent (0.7 opacity)
- [x] Test: Toggle terrain OFF -> only contour visible, full opacity (1.0)
- [x] Test: Toggle both OFF -> blank map area (grid still works if enabled)
- [x] Test: Switch maps -> layers reset to defaults, checkboxes reset
- [x] Test: Map without contourmap.png -> contour checkbox disabled

---

## 5. Generate Contour Maps for All Maps

### 5.1 Run batch processing
- [x] Open `processor/generate_contours.ipynb` in Jupyter or Colab
- [x] Run all cells to process all maps
- [x] Verify no errors in output
- [x] Verify summary shows all maps processed

### 5.2 Verify output files
- [x] Check that `contourmap.png` exists in each map folder under `processed_maps/`
- [x] Check that `metadata.json` contains `contourmap` field for each map
- [x] Spot-check 5 maps with different terrain types:
  - Flat map (e.g., burning_sands) - verify contour lines sparse
  - Mountain map (e.g., korengal) - verify contour lines dense
  - Mixed terrain map (e.g., muttrah_city_2) - verify variety
  - Small height_scale map - verify labels readable
  - Large height_scale map - verify labels not overlapping

---

## 6. Run All Tests

### 6.1 Run contour generation tests
- [x] Run: `pytest processor/tests/test_contour_generation.py -v`
- [x] Verify all tests pass
- [x] Fix any failures

### 6.2 Run existing tests (regression check)
- [x] Run: `pytest processor/tests/ -v`
- [x] Verify no existing tests broken by changes

---

## 7. Final Validation

### 7.1 End-to-end test
- [x] Start server with `run.bat` (Windows) or `run.sh` (Linux/Mac)
- [x] Load 3 different maps in browser
- [x] Toggle layers in various combinations
- [x] Verify no console errors in browser DevTools
- [x] Verify contour lines align with terrain features on minimap
- [x] Verify elevation labels are readable

### 7.2 Code review checklist
- [x] All code uses ASCII characters only (no Unicode, no emojis)
- [x] No external API calls or CDN links added
- [x] Code follows project style guide (see `openspec/project.md`)
- [x] New functions have docstrings/comments
- [x] metadata.json updated for all maps
- [x] Tests added and passing

