# Design: Opening-Flow Simulator

## Context

The mortar calculator is a fully offline, browser-math application: Flask serves static files, all ballistics computation happens in JavaScript, and per-map data ships as pre-processed JSON/PNG under `processed_maps/<map>/`. The flow simulator fits this architecture, but with one deliberate shift from the original design: **all reachability computation moves offline into a maintainer-side Python pipeline**, and the browser receives a precomputed field grid that it only renders. The frontend therefore does no physics, no Dijkstra, and no video decoding; it thresholds a grid at time t and draws the result.

The core question the feature answers: "At minute T after round start, where can each team's infantry and vehicles physically be?" This is a reachability question, not a prediction question. The design separates an honest deterministic core (time-to-reach field, computed once in Python) from an engaging presentation layer (bands, contested zone, race times, and particles, all derived from the same field in the browser).

## Key Decisions

### D1: Time-to-reach field as the core model, particles as presentation

**Decision:** Compute earliest-arrival time per grid cell via multi-source Dijkstra over a cost grid. In the browser, render bands, contested zone, and particles advected along the field's negative gradient.

**Alternatives considered:**
- *Pure Monte Carlo agent swarm (user's initial framing):* thousands of agents random-walking. Rejected as the core model because results are noisy, require behavior assumptions, and cannot be regression-tested (every stochastic render differs, so videos/outputs cannot be diffed or reproduced from a bug report). The swarm's p95 extent IS the Dijkstra frontier, estimated noisily at far higher compute. Retained only as the presentation layer, where noise is a feature (organic look), not a bug.
- *Fast marching method:* mathematically cleaner for continuous cost, but Dijkstra on a grid is simpler to implement and unit-test correctly, and fast enough at our grid sizes.

**Consequence:** The bands, contested zone, race times, and particles can never contradict each other, because all four derive from one field.

### D2: Cost grid mechanically derived from game data, not hand-annotated and not the navmesh

**Decision:** Build the movement cost grid in Python from four mechanical sources: the heightmap (slope via central differences), road geometry decoded from compiled road meshes (`roads/*_compiled.mesh` in client.zip, placements from `compiledroads.con` in server.zip; roads = fast tier), `staticobjects.con` (building/wall footprints via a name heuristic = slow tier), and `overgrowth/overgrowthcollision.con` (vegetation instance positions = forest density). Do not parse the binary `aipathfinding/*.clb` navmesh. Do not build a hand-annotation painting tool.

**Rationale:** Every checked map ships `compiledroads.con` (segment placements) and `staticobjects.con` (thousands of placed objects with position/rotation). The planning-phase assumption that compiledroads.con contains "polylines with widths" proved WRONG at implementation time: it holds only per-segment mesh references and positions. The compiled mesh binary format was decoded during implementation (52-byte header with world origin and vertex count, 32-byte vertices `[position xyz, UV0, UV1, alpha]`, uint16 triangle indices; documented in `artifacts/road-mesh-format.md` and cross-validated against a public open-source BF2 importer), so road geometry is now EXACT, not heuristic. Vegetation uses `overgrowthcollision.con`, the game's own overgrowth placement list, rather than counting tree-named statics. This makes the user's "3-tier binning" (smooth-passable roads / bumpy-passable terrain / near-impassable water+ridges) derivable mechanically, which is reproducible and survives a rule change. Hand-annotation is 66 maps of unverifiable manual judgment that must be redone whenever a constant changes. A CV/LLM classification pipeline was considered and rejected as YAGNI: there is no off-the-shelf classifier for BF2 static-template walkability, and the name heuristic plus slow-cost treatment already meets v1 tolerance.

**QA model:** The pipeline renders the cost grid as a debug overlay on the minimap; a human (or a QA subagent) eyeballs 2-3 maps and records corrections as a hand-edited per-map JSON patch file. Overrides are rare and reviewable; the agent reviews, it does not author from scratch.

**Forest tier:** Forest has no direct heightmap/road/statics signal, but the game ships its own vegetation placement list: `overgrowth/overgrowthcollision.con` (one `Object.create` + transformation matrix per plant, positions verified during implementation). v1 uses a tree-density proxy: count overgrowth instances (plus vegetation-classified statics) per cell, and treat high density as the slow/bumpy tier. This proxy is cross-checked against the minimap texture (green/dark regions) purely as a sanity signal to catch dense forests that have few placed plants; the texture is not the source of truth and no image classification is built.

**Cost model:** The grid stores one continuous cost number per cell (base x slope x water x building, with road membership overriding to the fast tier), not three discrete buckets. The user's "smooth / bumpy / near-impassable" 3-tier picture is the QA rendering derived from those numbers, not the storage model; continuous cost yields smoother, more physical frontiers.

**Known ceiling:** Building footprints come from a name heuristic, not collision meshes, so urban maps are approximate. Forest cover is a density proxy cross-checked against the minimap, not a true land-cover mask. Upgrade path: `objects_statics_server.zip` collision-mesh parsing or navmesh parsing.

### D3: Movement parameters are pipeline inputs with provenance labels

**Decision:** All movement constants (infantry walk/sprint speed, max traversable slope, per-vehicle speeds, surface/road modifier, water and building cost multipliers) are inputs to the Python pipeline, recorded per-run. Defaults come from extracted game files where possible; otherwise from labeled historical baselines.

**Rationale:** Research found NO verified public v1.9 values for infantry speed, slope limits, or road/off-road modifiers. Freezing unverified numbers would violate the project's honesty bar; the ballistics constants are frozen precisely because they ARE verified. Because computation is offline, a wrong constant is fixed by editing one config and re-running the pipeline for affected maps, not by re-rendering media. Defaults:
- Sprint ~5 m/s, walk ~2.5 m/s, 30 s sprint / 90 s regen: historical 2014 dev post, labeled "historical baseline, unverified for v1.9".
- Vehicle speeds: extracted from `objects_vehicles_server.zip` `.tweak` files. `setMaxSpeed` is a per-axis vector (x/y/z = lateral/vertical/forward) whose absolute value is not directly km/h (M3 halftrack forward = 150, a civilian truck = 10000), so values are used for relative ordering and calibrated against documented vehicles; uncalibrated entries are labeled.
- Uniform surface by default (no road bonus) matches the user's forum claim; unverified either way; exposed as a pipeline knob. Because `compiledroads.con` exists, a road speed bonus can be enabled later without new extraction.

### D4: Precompute offline, ship a field grid, render in the existing map UI

**Decision:** The Python pipeline emits a compact quantized arrival-time grid per map/layer/team/agent-class (PNG-as-data or raw binary, ~1 MB each) plus a `race_times.json`, shipped under `processed_maps/<map>/flow/` and served by the existing `/maps/<map>/<file>` route. The calculator's existing Leaflet map gains a Flow layer that loads the grid and thresholds it at time t. No separate `/flow.html` page; no GIF/MP4/WebM.

**Alternatives considered:**
- *In-browser Dijkstra engine (original design):* Rejected. It puts physics in the frontend, adds a WebView performance gamble on 4 km maps, and duplicates the solver in JS where it is harder to test than in Python.
- *Pre-rendered video overlay (user's intermediate framing):* Rejected. GIF has 1-bit alpha, MP4 has no browser alpha, WebM alpha is spotty; 66 maps x layers x classes x 300 s of video is a repo-size/LFS problem; and any wrong speed constant forces a full corpus re-render. A quantized grid is not a schema; it is the heightmap pattern the repo already ships.

**Consequence:** The frontend stays dumb (threshold + draw), Android inherits the feature for free, speeds stay correctable per-map, and the output is fully seekable with no codec work.

### D5: Coordinate transform verified by spike before pipeline work

**Decision:** Phase A begins with a spike that parses one `gameplayobjects.con` and plots extracted control-point positions over the minimap to confirm the transform before any pipeline code is written.

**Rationale:** BF2 `absolutePosition X/Y/Z` is center-origin with Y as elevation; the repo uses top-left origin with Y increasing southward. The spike (task 1.1) CONFIRMED the transform: `x_repo = X + map_size/2`, `y_repo = map_size/2 - Z` (+X = east, +Z = north). Verified by plotting named control points over the minimap (asad_khal's "northobjective" at Z=+134 lands north of "southobjective" at Z=-79 only under this sign) and by aligning sea-level water masks with minimap coastlines on adak and fools_road (heightmap row 0 = north = minimap top). A sign error here would silently poison every downstream artifact, and the spike cost under an hour.

### D6: Grid resolution and offline performance budget

**Decision:** Simulation grid at ~4 m cells (512x512 for 2 km maps, 1024x1024 for 4 km maps), float32 fields, binary-heap Dijkstra, computed in Python where runtime is not user-facing. The shipped grid is quantized (e.g. 8-bit or 16-bit arrival-seconds) to keep per-file size near 1 MB.

**Rationale:** 4 m cells resolve roads and ridgelines well enough for a strategic overview. Because computation is offline, the WebView frame-time concern that drove the original D6 fallback disappears; the browser only reads a grid and thresholds it, which is trivially cheap. If a 4 km map's grid is too large to ship comfortably, the pipeline (not the browser) halves resolution.

### D7: Water and buildings are heavy cost, never hard walls

**Decision:** Water and building footprints are modeled as a large cost multiplier, not as impassable. Only extreme slope (a configurable ridge threshold) is impassable.

**Rationale:** BF2/PR infantry swim; marking water impassable would tell new players "you are safe across the river," an underestimate of enemy reach, which is the dangerous direction of error and teaches the exact overextension this tool exists to prevent. The same logic applies to buildings: a wrong "slow" cell makes the frontier slightly conservative (safe), while a wrong "impassable" cell silently deletes a real street (dangerous). This corrects an earlier draft whose test asserted water is never crossed.

**Consequence:** The solver sanity suite asserts water/buildings slow but never hard-block; only the ridge threshold may hard-block.

### D8: Inland water needs a second pass beyond sea level

**Decision:** The water mask combines `sea_level_m` (global) with a flat-region detection pass over the heightmap to catch inland lakes and rivers that sit above sea level.

**Rationale:** `sea_level_m` is a single global; a mountain lake at 100 m on a map with sea level 49 m is missed by the global mask, and those missed water bodies are exactly the chokepoints that matter on the maps where they occur. A cheap flat-region pass (near-zero slope over a minimum area, elevation not part of the sea-level body) closes the hole.

### D9: Wave-one scope, extensible data format

**Decision:** The field is sourced only from initial spawn points and is labeled "from initial deployment" in the UI. The shipped format reserves room for scenario fields so forward-spawn modeling can be added later without reworking the format.

**Rationale:** BF2 spawns are teleportation, not walking; forward spawns and rallies appear as flags are captured, so a minute-4 frontier can be violated by reality. Modeling that is out of scope for v1, but the format must not preclude it. The honest v1 label prevents players from trusting a frontier that forward spawns would break.

### D10: Per-flag race-time readout is a first-class output

**Decision:** The pipeline samples each team's arrival field at every control point and ships `race_times.json`; the UI shows a per-flag "you vs enemy" readout (e.g. "Village: enemy 2:40, you 3:05").

**Rationale:** The new player's real question is not "watch the pretty fluid" but "if I rush this flag, do I win the race?" Once the field exists, sampling arrival times at CP positions from `gamelayers.json` is nearly free, and this readout teaches the anti-overextension lesson more directly than any animation.

## Implementation Deviations

- The existing `/maps` route was generalized from `<filename>` to `<path:filename>` with per-segment sanitization because shipped flow data is nested; no new routes were added.

### Cost-grid construction moved to add-terrain-traversability-model (2026-09-28)

The original task 2.1 had `build_flow_fields.py` building the cost grid itself (slope, road tier, water, buildings, forest). During implementation, cost-grid construction was split into the `add-terrain-traversability-model` change, which now owns it: `processor/build_terrain_cost.py` implements D2's four mechanical sources, D6's ~4 m grid, D7's never-block-except-extreme-slope semantics ("Water and buildings remain high-cost and passable by default"), and D8's inland-water pass (conservatively, as candidate-not-confirmed per traversability D6). It writes validated `processed_maps/<map>/terrain/<profile>/cost.bin` float32 grids (-1.0 = blocked) whose documented loader contract (`processor/terrain_artifact.py`) names this solver as the consumer. `build_flow_fields.py` therefore LOADS terrain artifacts instead of rebuilding cost logic; duplicating the cost model in two files would double the maintenance surface for zero benefit. Profile mapping: flow class `infantry` -> terrain profile `infantry`; flow class `vehicles` -> terrain profile `wheeled_vehicle`. The D2 cost-grid QA overlay is the traversability change's deterministic QA renderer output.

## Data Formats

### `processed_maps/<map>/gamelayers.json` (new)

```json
{
  "map_name": "asad_khal",
  "format_version": "1.0",
  "layers": [
    {
      "mode": "gpm_cq",
      "size": 32,
      "control_points": [
        { "id": 301, "name": "cpname_asad_khal_aas32_idfbase", "team": 2, "x": 762.09, "y": 860.116 }
      ],
      "spawn_points": [
        { "name": "cpname_asad_khal_aas64_mecbase_0_5", "group": 2, "control_point_id": 702, "x": 2402.5, "y": 2454.3 }
      ],
      "vehicle_spawners": [
        { "name": "...", "template": "us_jep_hmmwv", "team": 2, "control_point_id": 301, "x": 2276.0, "y": 1686.0 }
      ]
    }
  ]
}
```

Positions are in repo world coordinates (meters, top-left origin), converted from BF2 center-origin by the verified D5 transform. `the_falklands` is skipped.

The generalized nested serving route exposes the full per-map processed_maps tree; it already exposed individual files, and nested paths extend that access to subdirectories. No sensitive data lives there.

### `processed_maps/<map>/obstructions.json` (new, pipeline-only)

Road segment triangle geometry (world-space, decoded from client.zip compiled meshes via `processor/bf2_road_mesh.py`; the compiled format contains no polylines or widths), name-filtered building/wall footprints (position, rotation, template class), and vegetation placements from `overgrowthcollision.con`, all in repo world coordinates. Consumed by `build_flow_fields.py`; not shipped to the browser as-is.

### `metadata.json` (additive)

`"sea_level_m": 49`; absent on maps not yet re-processed. The pipeline treats absence as "no sea-level water mask" and relies on the D8 flat-region pass, logging a warning.

### `calculator/static/data/vehicle_speeds.json` (new, generated)

```json
{
  "format_version": "1.0",
  "source": "objects_vehicles_server.zip .tweak extraction, PR v1.9; setMaxSpeed per-axis, calibrated where possible",
  "vehicles": {
    "us_jep_hmmwv": { "max_speed_ms": 30.6, "class": "jeep", "calibrated": true }
  }
}
```

### `processed_maps/<map>/flow/<layer>/<team>/<class>.bin|png` (new, generated)

Quantized arrival-time grid (arrival seconds per cell), with a small JSON sidecar carrying grid origin, cell size, quantization scale, and the movement-parameter provenance used for the run. Reserved `scenario` field for D9 forward-spawn extension.

### `processed_maps/<map>/flow/<layer>/race_times.json` (new, generated)

Per control point: `{ cp_id, name, team1_seconds, team2_seconds }`.

## Error Handling

- Map without `gamelayers.json`: hidden from the Flow layer controls (console log only).
- Map without `obstructions.json` (currently andromeda): the terrain stage logs a warning and builds cost artifacts without obstruction-derived road, building, or vegetation costs; flow generation consumes the terrain artifacts as-is.
- Map without `sea_level_m`: pipeline runs with the D8 flat-region pass only; warning logged; shipped sidecar records the degraded mask.
- Vehicle template missing from `vehicle_speeds.json`: pipeline falls back to class-average speed and records the fallback in the sidecar.
- Corrupt/unparseable `gameplayobjects.con` layer: extractor logs, skips that layer, continues; summary at end.
- Layer with zero spawn points for a team: pipeline writes no field for that team; UI shows "no spawn data" for that team instead of an empty overlay.
- Missing flow grid for a map: Flow layer shows a "not computed for this map" notice, never a blank or broken overlay.
- --race-times-only never deletes a ace_times.json; if a layer's fields were ever removed, a stale file would remain and must be deleted by hand (fields are never removed in practice).

## Testing Strategy

- **Parser fixtures** (`processor/tests/test_gamelayer_extraction.py`): verbatim excerpts of real CP template+instance, spawn point, vehicle spawner, road, and static-object blocks; assert IDs, teams, positions, and numeric linkage survive parsing.
- **Field solver sanity** (`processor/tests/test_flow_field.py`): flat uniform cost map produces a frontier radius ~= speed x time (tolerance 1 cell); a ridge above the slope threshold forces a detour; water and building cells increase arrival time but are still reached (D7); only extreme slope hard-blocks.
- **Frontend** (`calculator/tests/test_flow_overlay.js`): loading a known grid and thresholding at time t produces the expected band set; contested zone is the intersection within delta; race-time readout matches the sidecar.
- **Manual smoke:** Adak AAS 64; spawn clusters land on the main bases visible in the minimap; 5-minute infantry frontier stays plausibly inside the map; contested zone appears near central flags; cost-grid debug overlay eyeballed on 2-3 maps (D2 QA).
- **Regression:** existing ballistics test suite and calculator behavior must pass unchanged.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Coordinate-transform sign error | D5 spike with visual ground-truthing before pipeline work |
| `setMaxSpeed` units not directly km/h | Extract for relative ordering; calibrate against documented vehicles; label uncalibrated entries (D3) |
| Unverifiable movement constants | D3: pipeline inputs with provenance labels; cheap to re-run |
| Inland water above sea level missed | D8 flat-region second pass |
| Building footprint heuristic silently wrong | D7 slow-cost-never-wall (safe direction of error) + D2 debug-overlay QA |
| Water marked impassable teaching overextension | D7 heavy-cost-never-wall |
| 4 km map grid too large to ship | D6 pipeline-side resolution fallback |
| Minute-4 frontier violated by forward spawns | D9 wave-one label; format reserved for scenarios |
| Licensing of PR assets | Only extracted numeric tables and coordinates ship; zips stay maintainer-side in `raw_game_data/` |
| 19 processed maps lack local server.zip | Hidden from Flow controls; re-collection is a separate maintainer task |
