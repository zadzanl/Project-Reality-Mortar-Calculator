# calculator-ui Spec Delta

## ADDED Requirements

### Requirement: Map Layer Toggle Controls

The system SHALL provide two checkbox controls in the results panel that allow users to toggle visibility of terrain map and contour map layers independently.

#### Scenario: Toggle controls location
- **WHEN** page loads
- **THEN** two checkboxes appear in the results panel:
  - Located BELOW the hint box ("Tip: Click map to place target. Shift+click to place mortar. Drag markers to refine.")
  - Located AFTER the "Show Grid" checkbox
  - Aligned with "Show Grid" checkbox styling

#### Scenario: Toggle controls display
- **WHEN** page loads
- **THEN** two checkboxes appear:
  - "Terrain Map" checkbox (id: `terrain-layer-toggle`)
  - "Contour Map" checkbox (id: `contour-layer-toggle`)
- **AND** checkboxes use same styling as "Show Grid" checkbox
- **AND** checkboxes are keyboard accessible (Tab + Space)

#### Scenario: Default checkbox states
- **WHEN** map is loaded
- **THEN** "Terrain Map" checkbox is checked (ON)
- **AND** "Contour Map" checkbox is unchecked (OFF)
- **AND** only minimap.png is visible on map

#### Scenario: Checkbox state after map change
- **WHEN** user selects and loads a different map
- **THEN** checkboxes reset to default states (Terrain ON, Contour OFF)
- **AND** layers reset to match checkbox states
- **AND** contour checkbox is re-enabled (in case it was disabled for previous map)

---

### Requirement: Terrain Map Layer

The system SHALL display `minimap.png` as the terrain layer, controlled by the "Terrain Map" checkbox. The file path is `/maps/<map_name>/minimap.png`.

#### Scenario: Terrain layer visible (default)
- **WHEN** "Terrain Map" checkbox is checked
- **THEN** minimap.png displays on Leaflet map at path `/maps/<map_name>/minimap.png`
- **AND** layer has lower z-index than contour layer

#### Scenario: Terrain layer hidden
- **WHEN** user unchecks "Terrain Map" checkbox
- **THEN** minimap.png is removed from map display
- **AND** if contour layer is also hidden, map area is blank

#### Scenario: Missing minimap
- **WHEN** minimap.png does not exist for selected map
- **THEN** "Terrain Map" checkbox is disabled
- **AND** fallback placeholder displays (existing behavior)

---

### Requirement: Contour Map Layer

The system SHALL display `contourmap.png` as the contour layer, controlled by the "Contour Map" checkbox. The file path is `/maps/<map_name>/contourmap.png` (which maps to `processed_maps/<map_name>/contourmap.png` on disk).

#### Scenario: Contour layer visible
- **WHEN** user checks "Contour Map" checkbox
- **THEN** contourmap.png displays on Leaflet map at path `/maps/<map_name>/contourmap.png`
- **AND** layer has higher z-index than terrain layer
- **AND** contour layer overlays terrain layer if both visible

#### Scenario: Contour layer hidden (default)
- **WHEN** "Contour Map" checkbox is unchecked
- **THEN** contourmap.png is not displayed on map

#### Scenario: Missing contour map
- **WHEN** contourmap.png does not exist for selected map (404 error)
- **THEN** "Contour Map" checkbox is disabled
- **AND** checkbox label shows "(unavailable)" suffix or visual indicator
- **AND** console logs warning: "Contour map not available for [map_name]"

---

### Requirement: Layer Opacity Adjustment

The system SHALL adjust contour layer opacity based on layer combination to ensure readability when both layers are displayed simultaneously.

#### Scenario: Both layers visible
- **WHEN** both "Terrain Map" and "Contour Map" checkboxes are checked
- **THEN** contour layer opacity is set to 0.7 (70%)
- **AND** terrain layer remains at full opacity (1.0)
- **AND** both layers are visible with contour overlaying terrain

#### Scenario: Contour layer only
- **WHEN** "Contour Map" is checked AND "Terrain Map" is unchecked
- **THEN** contour layer opacity is set to 1.0 (100%)
- **AND** contour map displays at full brightness

#### Scenario: Terrain layer only
- **WHEN** "Terrain Map" is checked AND "Contour Map" is unchecked
- **THEN** terrain layer displays at full opacity (1.0)
- **AND** no opacity adjustment needed

#### Scenario: Neither layer visible
- **WHEN** both checkboxes are unchecked
- **THEN** map area displays blank (no image layers)
- **AND** grid overlay still functions if enabled
- **AND** markers and calculation still function

---

### Requirement: Layer State Management

The system SHALL maintain layer visibility state in the application state object and handle layer lifecycle correctly during map changes.

#### Scenario: State initialization
- **WHEN** application initializes
- **THEN** state object includes:
  - `terrainLayer: null` (Leaflet ImageOverlay reference)
  - `contourLayer: null` (Leaflet ImageOverlay reference)
  - `terrainVisible: true` (default visibility)
  - `contourVisible: false` (default visibility)

#### Scenario: State update on toggle
- **WHEN** user toggles a layer checkbox
- **THEN** corresponding state property updates immediately
- **AND** Leaflet layer is added or removed from map
- **AND** `updateContourOpacity()` function is called to adjust opacity

#### Scenario: Layer cleanup on map change
- **WHEN** user loads a new map
- **THEN** existing terrainLayer and contourLayer are removed from map
- **AND** state properties reset: `terrainLayer = null`, `contourLayer = null`
- **AND** state visibility resets: `terrainVisible = true`, `contourVisible = false`
- **AND** checkbox DOM elements reset to match state
- **AND** new layers are created for new map

---

### Requirement: Graceful Degradation

The system SHALL handle missing layer files gracefully without breaking functionality.

#### Scenario: Contour map unavailable
- **WHEN** contourmap.png fails to load (404 or network error)
- **THEN** "Contour Map" checkbox becomes disabled
- **AND** checkbox label shows "(unavailable)" suffix or visual indicator
- **AND** error is logged to console: "Contour map not available for [map_name]"
- **AND** terrain layer continues to function normally
- **AND** calculator functionality (markers, grid, calculation) still works

#### Scenario: Both files unavailable
- **WHEN** both minimap.png and contourmap.png are unavailable
- **THEN** both checkboxes are disabled
- **AND** existing fallback placeholder displays
- **AND** calculator functionality (markers, grid, calculation) still works

#### Scenario: Re-enable on map change
- **WHEN** user switches from a map without contourmap.png to a map with contourmap.png
- **THEN** "Contour Map" checkbox is re-enabled
- **AND** "(unavailable)" suffix is removed from label

---

### Requirement: Event Listeners for Layer Toggles

The system SHALL add event listeners for the layer toggle checkboxes in the `setupEventListeners()` function.

#### Scenario: Terrain toggle listener
- **WHEN** user changes "Terrain Map" checkbox
- **THEN** `toggleTerrainLayer(checked)` function is called
- **AND** terrain layer is added or removed from map based on checked state

#### Scenario: Contour toggle listener
- **WHEN** user changes "Contour Map" checkbox
- **THEN** `toggleContourLayer(checked)` function is called
- **AND** contour layer is added or removed from map based on checked state
- **AND** opacity is adjusted based on terrain layer visibility

