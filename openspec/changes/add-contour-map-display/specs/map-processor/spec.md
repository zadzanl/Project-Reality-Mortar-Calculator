# map-processor Spec Delta

## ADDED Requirements

### Requirement: Contour Map Generation Notebook

The system SHALL provide a Jupyter notebook (`processor/generate_contours.ipynb`) that generates precomputed contour map PNG images from heightmap data. The notebook runs after `process_maps.ipynb` completes. Contour maps are generated once during processing and loaded at runtime (NOT generated live).

#### Scenario: Successful contour generation
- **WHEN** notebook is run with processed heightmap data available
- **THEN** for each map in `processed_maps/`:
  - `contourmap.png` is created at path `processed_maps/<map_name>/contourmap.png`
  - Image resolution matches the minimap.png resolution exactly
  - Image contains elevation heat map with contour lines
  - `metadata.json` is updated with contourmap information
- **AND** progress displays "[X/Y] Processing map_name..." for each map
- **AND** summary shows total processed and any errors

#### Scenario: Missing heightmap data
- **WHEN** a map folder lacks `heightmap.json.gz`
- **THEN** error is logged for that map
- **AND** processing continues to next map
- **AND** error is included in final summary

#### Scenario: Corrupted heightmap data
- **WHEN** `heightmap.json.gz` cannot be parsed
- **THEN** error message displays "Failed to load heightmap: [map_name]"
- **AND** processing continues to next map

---

### Requirement: Elevation Normalization

The system SHALL normalize raw heightmap values (0-65535) to actual elevation in meters using the height_scale from metadata.json.

#### Scenario: Elevation conversion formula
- **WHEN** heightmap data is processed
- **THEN** elevation is calculated using formula: `elevation_meters = (raw_value / 65535.0) * height_scale`
- **AND** `raw_value` is uint16 integer from heightmap (range 0-65535)
- **AND** `height_scale` is read from metadata.json (e.g., 300 meters)
- **AND** output is floating-point elevation in meters

#### Scenario: Contour levels based on normalized elevation
- **WHEN** contour lines are calculated
- **THEN** thin line levels are: `np.arange(min_elevation, max_elevation + 5, 5)`
- **AND** thick line levels are: `np.arange(min_elevation, max_elevation + 15, 15)`
- **AND** levels are in actual meters (not raw heightmap values)

---

### Requirement: Resolution Matching via Interpolation

The system SHALL interpolate heightmap data to match minimap.png resolution exactly, ensuring pixel-perfect overlay alignment.

#### Scenario: Heightmap upscaling
- **WHEN** heightmap resolution (e.g., 1025x1025) is smaller than minimap resolution (e.g., 2048x2048)
- **THEN** heightmap is upscaled using bilinear interpolation
- **AND** in-between elevation points are filled smoothly
- **AND** output matches minimap dimensions exactly

#### Scenario: Heightmap downscaling
- **WHEN** heightmap resolution is larger than minimap resolution
- **THEN** heightmap is downscaled using bilinear interpolation
- **AND** output matches minimap dimensions exactly

#### Scenario: Missing minimap
- **WHEN** minimap.png does not exist for a map
- **THEN** contourmap resolution defaults to heightmap resolution
- **AND** warning is logged

---

### Requirement: Elevation Heat Map Background

The contour map SHALL display an elevation heat map background using a four-color gradient that provides visual elevation context.

#### Scenario: Color gradient application
- **WHEN** contour map is generated
- **THEN** colors are applied based on normalized elevation:
  - Blue (#0000FF) at lowest elevation (0% of range)
  - Green (#00FF00) at 33% of elevation range
  - Yellow (#FFFF00) at 66% of elevation range
  - Red (#FF0000) at highest elevation (100% of range)
- **AND** colors blend smoothly between gradient stops

#### Scenario: Flat terrain map
- **WHEN** map has minimal elevation variation (height_scale < 50m)
- **THEN** colors still span full gradient range
- **AND** subtle elevation changes are visible

---

### Requirement: Contour Line Intervals

The contour map SHALL display contour lines at two intervals: thin lines every 5 meters of elevation change and thick lines every 15 meters of elevation change, matching military topographic map standards.

#### Scenario: Thin contour lines (5m interval)
- **WHEN** contour map is generated
- **THEN** thin contour lines are drawn at every 5 meters of elevation change
- **AND** thin lines use linewidth 0.5
- **AND** thin lines use dark gray color

#### Scenario: Thick contour lines (15m interval)
- **WHEN** contour map is generated
- **THEN** thick contour lines are drawn at every 15 meters of elevation change
- **AND** thick lines use linewidth 1.5
- **AND** thick lines use black color
- **AND** thick lines are visually distinct from thin lines

#### Scenario: High elevation map (500m height_scale)
- **WHEN** map has elevation range of 0-500 meters
- **THEN** thin contour lines appear at: 0m, 5m, 10m, 15m, ... 500m (100 lines)
- **AND** thick contour lines appear at: 0m, 15m, 30m, 45m, ... 495m (33 lines)

---

### Requirement: Elevation Labels on Thick Contour Lines

The contour map SHALL display elevation labels on thick contour lines only (15m intervals) at regular spacing along each line.

#### Scenario: Label placement
- **WHEN** contour map is generated
- **THEN** elevation labels appear on thick contour lines only (NOT on thin 5m lines)
- **AND** labels are spaced at regular intervals along each line
- **AND** labels display elevation value in meters as integer
- **AND** labels use ASCII characters only (no Unicode symbols)

#### Scenario: Label readability
- **WHEN** contour map is viewed
- **THEN** labels have sufficient contrast against background
- **AND** labels do not overlap excessively
- **AND** label font size is readable at normal zoom

---

### Requirement: Metadata Update

The system SHALL update `metadata.json` for each map to include contour map information after generation.

#### Scenario: Metadata field addition
- **WHEN** contour map is generated successfully
- **THEN** `metadata.json` is updated to include `contourmap` object with:
  - `file`: "contourmap.png"
  - `resolution`: "{width}x{height}" (e.g., "2048x2048")
  - `generated_at`: ISO 8601 timestamp with 'Z' suffix
  - `thin_interval_m`: 5
  - `thick_interval_m`: 15
- **AND** existing metadata fields are preserved unchanged

#### Scenario: Metadata validation
- **WHEN** metadata.json is updated
- **THEN** resulting JSON is valid and parseable
- **AND** all required existing fields remain intact

---

### Requirement: ASCII-Only Output

The contour generation notebook SHALL use ONLY ASCII characters in all code, comments, labels, and generated output. No Unicode symbols, special characters, or emojis are permitted.

#### Scenario: Code content
- **WHEN** notebook code is inspected
- **THEN** all characters are in ASCII range (0-127)
- **AND** no Unicode symbols appear in comments
- **AND** no emojis appear in print statements

#### Scenario: Generated image labels
- **WHEN** elevation labels are rendered on contour map
- **THEN** only ASCII digits (0-9) appear
- **AND** no Unicode degree symbols or special characters

---

### Requirement: Output File Specifications

The generated contour map SHALL be saved as a PNG file with specifications that ensure compatibility with Leaflet.js display.

#### Scenario: File path and format
- **WHEN** contour map is generated for a map
- **THEN** file is saved at `processed_maps/<map_name>/contourmap.png`
- **AND** file format is PNG with RGB color
- **AND** file has no transparency (opaque terrain-colored background)

#### Scenario: Resolution matching
- **WHEN** minimap.png exists for a map
- **THEN** contourmap.png resolution matches minimap.png resolution exactly (pixel-for-pixel)
- **WHEN** minimap.png does not exist
- **THEN** contourmap.png resolution is derived from heightmap resolution

---

### Requirement: Unit Tests for Contour Generation

The system SHALL include unit tests for contour generation functions in `processor/tests/test_contour_generation.py`.

#### Scenario: Heightmap loading tests
- **WHEN** tests are run
- **THEN** `load_heightmap()` is tested with valid gzipped JSON
- **AND** `load_heightmap()` is tested with missing file (expect graceful error)
- **AND** `load_heightmap()` is tested with corrupted data (expect graceful error)

#### Scenario: Elevation normalization tests
- **WHEN** tests are run
- **THEN** `normalize_elevation()` is tested with known values:
  - raw_value=0, height_scale=300 returns 0.0m
  - raw_value=65535, height_scale=300 returns 300.0m
  - raw_value=32768, height_scale=300 returns approximately 150.0m

#### Scenario: Resolution matching tests
- **WHEN** tests are run
- **THEN** `match_minimap_resolution()` is tested for upscaling
- **AND** `match_minimap_resolution()` is tested for downscaling
- **AND** output dimensions match target exactly

#### Scenario: Metadata update tests
- **WHEN** tests are run
- **THEN** `update_metadata()` correctly adds contourmap field
- **AND** existing fields are preserved
- **AND** output JSON is valid

