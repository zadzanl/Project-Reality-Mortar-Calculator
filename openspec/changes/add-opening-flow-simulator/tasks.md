# Tasks: Add Opening-Flow Simulator

## Before You Start (Required Reading)

Read these files to understand the codebase:

1. **`openspec/project.md`** - Read the "Tech Stack" and "Code Style Rules" sections.
2. **`AGENTS.md`** - Read "Critical Numbers and Formulas" (ballistics numbers are frozen; movement numbers in THIS change are explicitly NOT frozen) and "Map Processing (Maintainer Only)".
3. **`openspec/changes/add-opening-flow-simulator/design.md`** - Decisions D1-D10 and data formats; do not deviate without updating the design doc.
4. **`processor/process_one_map.py`** - Study how server.zip files are opened and parsed (zipfile, regex on .con files).
5. **`calculator/static/js/heightmap.js`** - Study `loadHeightmap`, `loadMetadata`, `worldToPixel`, and the Uint16Array cache. The Flow overlay reuses these for display alignment only (no physics in the browser).
6. **`calculator/static/js/app.js`** - Study `initializeLeafletMap()`, the terrain/contour checkbox pattern, and the Y-flip convention `[lat,lng] = [mapSize - y, x]`.
7. **`calculator/tests/run-tests.js`** - Study the test harness pattern before writing `test_flow_overlay.js`.

## Critical Rules

- **ONLY ASCII CHARACTERS:** All code, comments, labels, and output must use ASCII characters only. Do NOT use Unicode symbols, special characters, or emojis.
- **Offline operation:** Do NOT add external API calls or CDN links. Leaflet and pako are already vendored; reuse them.
- **No new runtime dependencies:** Extractors and the field pipeline use Python stdlib (zipfile, re, json, struct) plus numpy (already a processor dependency). Browser code is vanilla ES modules. No image/video libraries, no CV/ML frameworks.
- **Never modify `raw_map_data/` or `raw_game_data/`:** These are extraction inputs only.
- **Never ship PR asset zips:** Only the extracted JSON tables and generated field grids are committed.
- **No video codecs:** Do NOT introduce GIF/MP4/WebM encoding or decoding anywhere. The shipped artifact is a quantized arrival-time grid, not media.
- **No browser physics:** The browser loads a precomputed field grid and only thresholds/draws it. No Dijkstra, no slope math, no cost grid in JavaScript.
- **Movement numbers are configurable:** Every movement parameter is a pipeline input with a provenance label. Do not hard-code them as frozen constants, and do not touch the frozen ballistics constants.
- **the_falklands stays excluded** from all extraction and UI lists.
- **Follow existing code style:** Match indentation, naming, and patterns in existing files (2-space JS, 4-space Python).

---

## 1. Phase A: Maintainer-Side Extraction

### 1.1 Coordinate transform spike (BLOCKS 1.2 and all of Phase B)
- [x] Parse `gamemodes/gpm_cq/32/gameplayobjects.con` from `raw_map_data/asad_khal/server.zip` (read-only, in-memory)
- [x] Extract control-point names, teams, IDs, and `absolutePosition X/Y/Z` values
- [x] Apply candidate transform `x = X + map_size/2`, `y = Z + map_size/2` and plot points over `processed_maps/asad_khal/minimap.png`
- [x] Verify visually that flags land on plausible locations (main bases near map edges, objectives central); if mirrored, flip the Z-sign and re-verify
- [x] Verify `heightmapcluster.setSeaWaterLevel` (asad_khal = 49) behaves as meters: terrain elevation at coastline pixels should be near 49 m
- [x] Record the confirmed transform as a comment block in `extract_gamelayers.py` and in design.md if it differs from D5

### 1.2 Game-layer extractor
- [x] Create `processor/extract_gamelayers.py`
- [x] For each `raw_map_data/<map>/server.zip` (skip missing, skip `the_falklands`), enumerate all `gamemodes/<mode>/<size>/gameplayobjects.con` entries
- [x] Parse ControlPoint templates (`controlPointId`, `team`, `unableToChangeTeam`) and instances (`absolutePosition`, `layer`)
- [x] Parse SpawnPoint templates (`setGroup`, `setControlPointId`) and instances (`absolutePosition`)
- [x] Parse ObjectSpawner templates (`setObjectTemplate <team> <vehicle_template>`, `team`, `teamOnVehicle`) and instances (`absolutePosition`, `setControlPointId`)
- [x] Link spawns and spawners to control points by numeric ID; retain `group` for spawn points
- [x] Convert all positions to repo coordinates using the confirmed 1.1 transform
- [x] Write `processed_maps/<map>/gamelayers.json` per the design.md schema
- [x] Print "[X/Y] Processing map_name..." progress and a final summary (maps processed, layers per map, errors)

### 1.3 Sea-level extraction
- [x] In `extract_gamelayers.py` (or `process_one_map.py` if cleaner), parse `heightmapcluster.setSeaWaterLevel` from `heightdata.con`
- [x] Add `sea_level_m` to `processed_maps/<map>/metadata.json` (additive; preserve all existing fields)
- [x] Handle missing field gracefully (log warning, omit key)

### 1.4 Obstruction extraction (roads + statics + vegetation)
- [x] Decode the compiled road mesh binary format (`processor/bf2_road_mesh.py`): 52-byte header (world origin, vertex count), 32-byte vertices `[position xyz, UV0, UV1, alpha]`, uint16 triangle indices; verified by plotting all asad_khal road vertices over the minimap and cross-validated against a public BF2 importer (see `artifacts/road-mesh-format.md`)
- [x] Create `processor/extract_obstructions.py`
- [x] Parse `compiledroads.con` from each server.zip: segment name, mesh reference, world position
- [x] Decode referenced meshes from the matching client.zip via `bf2_road_mesh.py`; rasterize-ready world-space triangles (repo coordinates via the 1.1 transform); missing client.zip or missing mesh: log and skip, continue
- [x] Parse `staticobjects.con` from each server.zip: `Object.create <template>`, `Object.absolutePosition`, `Object.rotation`
- [x] Classify templates with a name heuristic (buildings, walls, fences, containers) using folder/name prefixes; record the matched class per instance
- [x] Parse `overgrowth/overgrowthcollision.con`: vegetation instance positions from the transformation matrix (4th column = x/y/z)
- [x] Write `processed_maps/<map>/obstructions.json` (pipeline-only input; not shipped to the browser as-is)
- [x] Log per-map counts (roads, classified statics, unclassified statics, vegetation instances) for the QA pass

### 1.5 Vehicle physics spike (BLOCKS 1.6)
- [x] Confirm `raw_game_data/objects_vehicles_server.zip` is present (maintainer-provided)
- [x] Open .tweak files for 3-5 representative vehicles (truck, APC, tank, jeep, boat)
- [x] Confirm `setMaxSpeed` is a per-axis vector (x/y/z = lateral/vertical/forward) and identify the forward component
- [x] Calibrate: find a conversion from the forward component to km/h using 2-3 documented vehicles; if no linear map fits, record values as relative-only
- [x] If calibration fails: proceed with raw extracted values labeled "uncalibrated", and note it in the JSON `source` field

### 1.6 Vehicle speed extractor
- [x] Create `processor/extract_vehicle_speeds.py`
- [x] Parse all land-vehicle (and boat) .tweak files from the zip
- [x] Write `calculator/static/data/vehicle_speeds.json` per the design.md schema, including a `source` provenance string and a `calibrated` flag per entry
- [x] Cross-check: every vehicle template referenced by any `gamelayers.json` has an entry; log any misses

### 1.7 Infantry constants
- [x] Search `raw_game_data/objects_common_server.zip` and `raw_game_data/common_server.zip` for soldier movement/stamina parameters
- [x] Whatever is found becomes the labeled default; whatever is missing falls back to historical baseline (sprint 5 m/s, walk 2.5 m/s, 30 s sprint / 90 s regen, labeled "historical 2014, unverified for v1.9")
- [x] Store as defaults in a new pipeline config `processor/movement_params.json` with per-field provenance strings

### 1.8 Parser tests
- [x] Create `processor/tests/test_gamelayer_extraction.py` with verbatim fixture excerpts (CP template+instance, spawn point, vehicle spawner, road record, static-object record)
- [x] Assert IDs, teams, positions, and numeric linkage survive parsing
- [x] Assert malformed sections are skipped without crashing the whole layer

---

## 2. Phase B: Field Pipeline (Maintainer-Side Python)

### 2.1 Cost grid (SUPERSEDED 2026-09-28: owned by add-terrain-traversability-model)

Cost-grid construction (slope, roads, water, buildings, forest, combination, debug overlay) is implemented by `processor/build_terrain_cost.py` under the `add-terrain-traversability-model` change; see design.md "Implementation Deviations". What remains here:

- [x] Generate terrain artifacts for every map with a heightmap: `python processor/build_terrain_cost.py` (85 maps, 170 cost.bin files across infantry and wheeled_vehicle profiles)
- [x] `build_flow_fields.py` loads `processed_maps/<map>/terrain/<profile>/cost.bin` via `terrain_artifact.load_terrain_artifact` (profile infantry -> class infantry, profile wheeled_vehicle -> class vehicles); never rebuilds cost logic

### 2.2 Cost-grid QA (human or QA subagent)
- [x] Eyeball the debug overlay on 2-3 maps (asad_khal, adak, and urban muttrah_city_2; evidence: `artifacts/terrain-qa-002.md`)
- [x] Record correction outcome: no independently provable correction observed; no patch required. A patch consumer is not implemented and remains a separate design change.
- [x] Confirm no obvious major road is silently blocked or missed in the rendered overview; full game-collision truth remains outside this QA's evidence ceiling.

### 2.3 Time-to-reach solver (`processor/build_flow_fields.py`, solver stage)
- [x] Implement multi-source Dijkstra with a binary heap over the cost grid (numpy + heapq or a typed array)
- [x] Sources = selected team's spawn clusters (infantry) or vehicle spawner positions (vehicles) from `gamelayers.json`
- [x] Output float32 earliest-arrival-seconds per cell, per team, per agent class; unreachable cells = a sentinel
- [x] Deterministic: same inputs, same output, no randomness in the solver

### 2.4 Race-time sampler
- [x] Sample each team's arrival field at every control point in the layer
- [x] Write `processed_maps/<map>/flow/<layer>/race_times.json` per the design.md schema

### 2.5 Field serializer
- [x] Quantize each arrival field (8-bit or 16-bit arrival seconds) and write `processed_maps/<map>/flow/<layer>/<team>/<class>.bin|png`
- [x] Write a JSON sidecar per field: grid origin, cell size, quantization scale, movement-parameter provenance, and a reserved `scenario` field (D9)
- [x] If a 4 km map's grid exceeds the size budget, halve resolution in the pipeline (D6) and record it in the sidecar

### 2.6 Solver tests (`processor/tests/test_flow_field.py`)
- [x] Flat uniform cost map: frontier at time T is a circle with radius ~= speed x T (tolerance 1 cell)
- [x] Ridge above the slope threshold: arrival time behind it reflects the detour, not the straight line
- [x] Water cell: reached by infantry, but with arrival time reflecting the heavy cost multiplier (D7)
- [x] Building cell: reached, but slowed (D7)
- [x] Wire into the processor test suite

---

## 3. Phase C: Flow Overlay (Browser, presentation only)

### 3.1 Overlay scaffold (`calculator/static/js/flow/flow_overlay.js`)
- [x] Add a "Flow" layer toggle to the existing calculator map UI in `index.html` (no other calculator behavior changes)
- [x] Load the field grid + sidecar for the selected map/layer/team/class via the existing `/maps/<map>/<file>` route
- [x] Hide the Flow controls for maps without flow data; show a "not computed for this map" notice if a grid is missing

### 3.2 Controls
- [x] Layer dropdown populated from `gamelayers.json`, default `gpm_cq/64`
- [x] Team toggle (1 / 2 / both) and agent-class toggle (infantry / vehicles)
- [x] Seek slider for time t (0 to 5 minutes)
- [x] A visible "from initial deployment" label (D9) and a provenance tooltip sourced from the field sidecar

### 3.3 Visualization (threshold + draw only)
- [x] Per-team frontier bands: threshold the arrival field at 60 s intervals up to t, team-colored
- [x] Contested-overlap highlight: cells reachable by both teams within a small time delta
- [x] Per-flag race-time readout from `race_times.json` ("Village: enemy 2:40, you 3:05")
- [x] Particle canvas: advect presentation particles along the negative gradient of the loaded field plus small noise; particles derive ONLY from the field (browser smoke: `artifacts/browser-verification-002.md`)
- [x] Recompute bands/contested on seek-slider input (cheap threshold, no solver)

### 3.4 Frontend tests (`calculator/tests/test_flow_overlay.js`)
- [x] Loading a known fixture grid and thresholding at time t produces the expected band set
- [x] Contested zone equals the intersection of both teams' reachable sets within delta
- [x] Race-time readout matches the fixture sidecar
- [x] Wire into existing `run-tests.js` harness

### 3.5 Android sync
- [ ] Run `build-android.bat`; confirm `www/` picks up the Flow overlay JS and per-map flow grids
- [ ] Smoke-test the Flow layer in Android WebView (thresholding a grid must be cheap; no physics to budget)

---

## 4. Phase D: Documentation and Wrap-Up

- [ ] Add one subsection to `AGENTS.md`: flow overlay purpose, the movement-numbers-are-configurable rule, data provenance rule, the no-video/no-browser-physics rule, and the `raw_game_data/` maintainer input
- [ ] Update `README.md` feature list with the flow overlay
- [ ] Run full verification: `python -m pytest processor/tests/`, `node calculator/tests/run-tests.js`, offline smoke test (network tab: zero external requests), existing ballistics tests unchanged
- [ ] Confirm acceptance criteria AC-1 through AC-8 from the plan artifact
