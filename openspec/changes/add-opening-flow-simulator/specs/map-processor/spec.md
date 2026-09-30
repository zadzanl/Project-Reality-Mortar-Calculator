# map-processor Spec Delta

## ADDED Requirements

### Requirement: Game-Layer Extraction Script

The system SHALL provide a maintainer-side script (`processor/extract_gamelayers.py`) that parses `gamemodes/<mode>/<size>/gameplayobjects.con` from each `raw_map_data/<map>/server.zip` and writes `processed_maps/<map>/gamelayers.json`. The script SHALL NOT modify `raw_map_data/`. The `the_falklands` map SHALL remain excluded.

#### Scenario: Successful extraction
- **WHEN** the script is run with local server.zip files present
- **THEN** for each map with a server.zip, `gamelayers.json` is written containing all parsed layers
- **AND** each layer contains control_points (id, name, team, x, y), spawn_points (name, group, control_point_id, x, y), and vehicle_spawners (name, template, team, control_point_id, x, y)
- **AND** positions are converted from BF2 center-origin coordinates to repo top-left-origin coordinates using the transform verified in the extraction spike
- **AND** progress displays "[X/Y] Processing map_name..." and a final summary lists maps processed and errors

#### Scenario: Missing server.zip
- **WHEN** a processed map has no local `raw_map_data/<map>/server.zip`
- **THEN** the map is skipped and logged
- **AND** processing continues with the next map

#### Scenario: Malformed layer file
- **WHEN** a `gameplayobjects.con` cannot be parsed
- **THEN** the error is logged for that layer
- **AND** other layers of the same map are still extracted
- **AND** the error appears in the final summary

---

### Requirement: Sea-Level Extraction

The system SHALL parse `heightmapcluster.setSeaWaterLevel` from `heightdata.con` in each server.zip and store it as `sea_level_m` in `processed_maps/<map>/metadata.json`. This is an additive field; all existing metadata fields SHALL be preserved.

#### Scenario: Sea level present
- **WHEN** `heightdata.con` contains `heightmapcluster.setSeaWaterLevel <value>`
- **THEN** `metadata.json` is updated with `sea_level_m` set to that numeric value

#### Scenario: Sea level absent
- **WHEN** `heightdata.con` lacks the field
- **THEN** a warning is logged and the key is omitted
- **AND** processing continues

---

### Requirement: Obstruction Extraction Script

The system SHALL provide a maintainer-side script (`processor/extract_obstructions.py`) that parses `compiledroads.con` and `staticobjects.con` from each server.zip, decodes the referenced compiled road meshes (`roads/*_compiled.mesh`) from the matching client.zip via `processor/bf2_road_mesh.py`, parses vegetation placements from `overgrowth/overgrowthcollision.con`, and writes `processed_maps/<map>/obstructions.json`. Roads SHALL be extracted as world-space triangle geometry (the compiled mesh format contains no polylines or widths; the format is documented in the change artifacts and was cross-validated against a public BF2 importer). Static objects SHALL be classified by a name heuristic (buildings, walls, fences, containers); the heuristic SHALL NOT be treated as authoritative, and unclassified objects SHALL be logged. This output is pipeline input only and SHALL NOT be shipped to the browser as-is.

#### Scenario: Roads extracted
- **WHEN** a server.zip contains `compiledroads.con` and the matching client.zip contains the referenced meshes
- **THEN** road triangle geometry is decoded and written to `obstructions.json` in repo world coordinates
- **AND** segments whose mesh is missing are logged and skipped

#### Scenario: Missing client.zip
- **WHEN** a map has a server.zip but no client.zip
- **THEN** roads are omitted for that map, the omission is logged
- **AND** statics and vegetation are still extracted

#### Scenario: Vegetation extracted
- **WHEN** a server.zip contains `overgrowth/overgrowthcollision.con`
- **THEN** vegetation instance positions are written to `obstructions.json` in repo world coordinates

#### Scenario: Statics classified
- **WHEN** a server.zip contains `staticobjects.con`
- **THEN** each `Object.create` instance is recorded with position, rotation, and a heuristic class
- **AND** per-map counts of roads, classified statics, and unclassified statics are logged for QA

---

### Requirement: Vehicle Speed Extraction Script

The system SHALL provide a maintainer-side script (`processor/extract_vehicle_speeds.py`) that parses vehicle `.tweak` files from the maintainer-provided `raw_game_data/objects_vehicles_server.zip` and writes `calculator/static/data/vehicle_speeds.json`. The PR asset zip SHALL NOT be committed or shipped; only the extracted JSON is committed. Because `setMaxSpeed` is a per-axis vector whose absolute value is not directly km/h, entries SHALL carry a `calibrated` flag and the JSON SHALL record calibration status in its `source` string.

#### Scenario: Successful extraction
- **WHEN** the script runs with `raw_game_data/objects_vehicles_server.zip` present
- **THEN** `vehicle_speeds.json` contains an entry per land-vehicle and boat template with `max_speed_ms`, `class`, and `calibrated`
- **AND** the JSON includes a `source` provenance string naming the extraction input and calibration status
- **AND** every vehicle template referenced by any `gamelayers.json` has an entry, or is logged as missing

#### Scenario: Missing input zip
- **WHEN** `raw_game_data/objects_vehicles_server.zip` is absent
- **THEN** the script exits with an actionable error message naming the expected file and folder

---

### Requirement: Field Pipeline Script

The system SHALL provide a maintainer-side script (`processor/build_flow_fields.py`) that loads a validated terrain cost grid per map and runs a deterministic multi-source Dijkstra per team per agent class, writing a quantized arrival-time grid plus a JSON sidecar and a `race_times.json` per layer under `processed_maps/<map>/flow/`. Terrain cost-grid construction is owned by `processor/build_terrain_cost.py`. The solver SHALL be deterministic (identical inputs produce identical outputs). The pipeline SHALL NOT use any video codec.

#### Scenario: Cost grid tiers
- **WHEN** the cost grid is built for a map
- **THEN** roads are rasterized as a fast tier, terrain is slope-scaled, and water, building, and high-tree-density cells are assigned a heavy cost multiplier
- **AND** water, building, and forest cells remain passable (heavy cost, never impassable)
- **AND** only cells above a configurable slope threshold are impassable
- **AND** each cell stores one continuous cost value, not a discrete tier label

#### Scenario: Inland water
- **WHEN** a map has inland water above `sea_level_m`
- **THEN** a flat-region detection pass adds those cells to the water mask
- **AND** the water treatment remains heavy-cost, not impassable

#### Scenario: Field output
- **WHEN** the solver runs for a layer
- **THEN** a quantized arrival-time grid and a sidecar (grid origin, cell size, quantization scale, movement-parameter provenance, reserved scenario field) are written per team per agent class
- **AND** `race_times.json` is written with per-control-point earliest arrival per team

#### Scenario: Solver correctness on flat terrain
- **WHEN** the solver runs on a uniform flat cost grid with a single source
- **THEN** the frontier at time T approximates a circle of radius speed x T within one cell of tolerance

#### Scenario: Water and buildings slow but never block
- **WHEN** the solver crosses water or building cells
- **THEN** those cells are reached with arrival times reflecting the heavy cost multiplier
- **AND** they are not treated as impassable

---

### Requirement: Movement Parameter Defaults Extraction

The system SHALL extract infantry movement and stamina parameters from maintainer-provided `raw_game_data/objects_common_server.zip` and `raw_game_data/common_server.zip` where present, writing defaults with per-field provenance strings to `processor/movement_params.json`. Parameters not found in game files SHALL fall back to labeled historical baselines.

#### Scenario: Parameter found in game files
- **WHEN** a movement parameter is located in the game files
- **THEN** its default uses the extracted value with provenance "extracted from v1.9 files"

#### Scenario: Parameter not found
- **WHEN** a movement parameter cannot be located in the game files
- **THEN** its default uses the historical baseline (sprint 5 m/s, walk 2.5 m/s, 30 s sprint / 90 s regen)
- **AND** its provenance is "historical baseline, unverified for v1.9"
