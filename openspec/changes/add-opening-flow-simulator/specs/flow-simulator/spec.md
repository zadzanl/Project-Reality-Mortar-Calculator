# flow-simulator Spec Delta

## ADDED Requirements

### Requirement: Flow Overlay in the Existing Map UI

The system SHALL add a "Flow" layer to the existing calculator Leaflet map that displays precomputed opening-flow reachability. The overlay SHALL reuse the existing map setup, minimap/contour overlays, and map dropdown. The calculator's ballistics behavior SHALL remain functionally unchanged. There SHALL NOT be a separate flow page.

#### Scenario: Overlay loads offline
- **WHEN** a user opens the calculator with no network access and enables the Flow layer
- **THEN** the overlay loads completely using only vendored libraries and local files
- **AND** maps without flow data are hidden from the Flow controls

#### Scenario: Calculator unaffected
- **WHEN** the Flow layer is added
- **THEN** all existing ballistics tests pass unchanged
- **AND** the only modifications to the calculator are the Flow layer toggle, its controls, and the per-flag readout

#### Scenario: Missing flow grid
- **WHEN** a map has no precomputed flow grid
- **THEN** the Flow layer shows a "not computed for this map" notice
- **AND** no blank or broken overlay is shown

---

### Requirement: Precomputed Field Consumption (No Browser Physics)

The system SHALL load a precomputed arrival-time field grid per map/layer/team/agent-class and SHALL NOT compute reachability, slope, cost grids, or run any shortest-path solver in the browser. The browser SHALL only threshold and render the loaded field. The system SHALL NOT use GIF, MP4, WebM, or any video codec for the overlay.

#### Scenario: Field loading
- **WHEN** a map and layer with flow data are selected
- **THEN** the browser loads the quantized arrival-time grid and its JSON sidecar via the existing `/maps/<map>/<file>` route
- **AND** the sidecar provides grid origin, cell size, quantization scale, and movement-parameter provenance

#### Scenario: Thresholding at time t
- **WHEN** the user moves the seek slider to time t
- **THEN** the overlay thresholds the loaded field at t to produce the reachable region
- **AND** no solver or physics runs in the browser

#### Scenario: Team with no spawn data
- **WHEN** a layer has no field for a team
- **THEN** that team's overlay displays "no spawn data" instead of an empty visualization

---

### Requirement: Movement Parameter Provenance

The system SHALL record the provenance of every movement parameter used to compute a field and SHALL surface that provenance in the UI. Movement parameters SHALL NOT be frozen constants. The frozen ballistics constants (gravity 14.86, projectile speed 148.64, max range 1500) SHALL NOT be affected.

#### Scenario: Provenance surfaced
- **WHEN** the Flow overlay is displayed
- **THEN** the movement-parameter provenance from the field sidecar is shown, using one of these labels:
  - "extracted from v1.9 files"
  - "historical baseline, unverified for v1.9"
  - "uncalibrated"
  - "user set"

#### Scenario: Wave-one scope labeled
- **WHEN** the Flow overlay is displayed
- **THEN** a visible label states the field is computed "from initial deployment"
- **AND** the shipped format reserves a scenario field for future forward-spawn modeling

---

### Requirement: Flow Visualization

The system SHALL display per-team frontier bands at 60-second intervals, a contested-overlap highlight, a per-flag race-time readout, and a particle-flow animation. All four visual elements SHALL derive from the same loaded arrival field so they cannot contradict each other.

#### Scenario: Frontier bands
- **WHEN** an arrival field is loaded for a team
- **THEN** bands are drawn at each 60-second mark up to the seek time t, in that team's color

#### Scenario: Contested zone
- **WHEN** both teams' arrival fields are loaded
- **THEN** cells reachable by both teams within a small time delta are highlighted as the contested zone

#### Scenario: Race-time readout
- **WHEN** flow data is loaded for a layer
- **THEN** each control point shows a per-flag "you vs enemy" earliest-arrival readout from `race_times.json`

#### Scenario: Particle animation
- **WHEN** the visualization plays
- **THEN** particles spawn at source cells and move along the negative gradient of the loaded arrival field plus small noise
- **AND** particle positions derive only from the loaded field

---

### Requirement: Game-Layer Data Format

The system SHALL consume per-map `gamelayers.json` files containing control points, spawn points, and vehicle spawners for every extracted game-mode layer, with positions in repo world coordinates (meters, top-left origin) and numeric control-point linkage.

#### Scenario: Layer selection
- **WHEN** a map with `gamelayers.json` is selected
- **THEN** a layer dropdown lists all extracted layers (mode + size)
- **AND** the default selection is `gpm_cq/64` when present

#### Scenario: Spawn-to-flag linkage
- **WHEN** spawn points are displayed or used as sources
- **THEN** each spawn point's `control_point_id` matches a control point `id` in the same layer
- **AND** the linkage uses the numeric ID, not the object name
