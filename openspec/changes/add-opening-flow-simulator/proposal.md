# Proposal: Add Opening-Flow Simulator

## Why

New players and squad leaders in Project Reality: BF2 have no way to visualize where infantry and vehicles can physically reach during the opening minutes of a match. This leads to overextension, unrealistic expectations about first-contact timing, and poor mortar/FOB placement decisions. The mortar calculator already ships heightmaps, map imagery, and coordinate plumbing for every map; this feature reuses them.

This is a simulation feature: no replay parsing, no telemetry, no recorded matches, no upload endpoints. The reachability model is computed offline by a maintainer-side Python pipeline and shipped as compact data grids; the browser only renders them. This keeps the frontend dumb, keeps Android/WebView free of physics code, and keeps every number correctable without re-rendering media.

## What Changes

1. **Game-layer extraction (maintainer-side):** New `processor/extract_gamelayers.py` parses `gamemodes/*/*/gameplayobjects.con` from each `raw_map_data/<map>/server.zip` and writes `processed_maps/<map>/gamelayers.json` (control points, infantry spawn points, vehicle spawners, linked by numeric `controlPointId`). All gamemode layers are extracted; the UI defaults to AAS 64 (`gpm_cq/64`). `the_falklands` remains excluded per AGENTS.md.

2. **Sea-level extraction (maintainer-side):** Parse `heightmapcluster.setSeaWaterLevel` from `heightdata.con` and add `sea_level_m` to `processed_maps/<map>/metadata.json` (additive field; existing consumers unaffected).

3. **Obstruction extraction (maintainer-side):** New extractors parse `compiledroads.con` (per-segment mesh references and placements) and decode the referenced client.zip road meshes into exact world-space triangle geometry; they also parse `staticobjects.con` (building/wall footprints via a name heuristic) from each server.zip, writing per-map JSON consumed only by the field pipeline (not shipped to the browser as-is).

4. **Vehicle speed extraction (maintainer-side):** New `processor/extract_vehicle_speeds.py` parses vehicle `.tweak` files from maintainer-provided `raw_game_data/objects_vehicles_server.zip` and writes `calculator/static/data/vehicle_speeds.json`. `setMaxSpeed` is a per-axis vector whose absolute units are not directly km/h, so values are extracted for relative ordering and calibrated against documented vehicles; uncalibrated values are labeled. The PR asset zip is never shipped or committed.

5. **Field pipeline (maintainer-side, the core):** New `processor/build_flow_fields.py` loads validated terrain cost artifacts produced by `processor/build_terrain_cost.py` and runs a multi-source Dijkstra per team per agent class, producing an earliest-arrival-seconds field. It also samples arrival times at each control point to produce per-flag race times. Output is a compact quantized grid per map/layer/team/class shipped under `processed_maps/<map>/flow/`.

6. **Flow overlay in the existing map UI:** The calculator's Leaflet map gains a "Flow" layer. The frontend loads a precomputed field grid and does only presentation: threshold the field at time t to draw isochrone bands, highlight the contested zone (cells both teams reach within a small delta), show a per-flag race-time readout, and advect presentation particles along the field gradient. A seek slider scrubs t. No Dijkstra, no physics, no video codecs in the browser.

7. **Zero NEW server routes:** The existing `/maps/<map>/<file>` route was generalized to nested paths so it serves any new per-map file. "No new server routes" means no second route, no POST endpoints, and no new dependencies; it does not mean zero code changes to the existing route. No external calls. Fully offline.

8. **Movement numbers are configurable at the pipeline, never frozen:** Unlike the ballistics constants (frozen per AGENTS.md), movement parameters are pipeline inputs with provenance labels ("extracted from v1.9 files" / "historical baseline, unverified" / "uncalibrated"), because no verified public v1.9 values exist for infantry speed, slope limits, or surface modifiers. Changing a parameter re-runs the pipeline for affected maps; it does not require re-rendering video.

9. **Tests:** Parser fixture tests and a field-solver sanity suite under `processor/tests/` (flat map gives frontier radius ~= speed x time; a ridge forces a detour; water and buildings slow but never hard-block). Frontend tests cover only field loading and thresholding.

## Impact

- **Affected specs:** `map-processor` (delta), new spec `flow-simulator`
- **Affected code:**
  - New: `processor/extract_gamelayers.py`, `processor/extract_obstructions.py`, `processor/extract_vehicle_speeds.py`, `processor/build_flow_fields.py`
  - New: `processor/tests/test_gamelayer_extraction.py`, `processor/tests/test_flow_field.py`
  - Modified: `calculator/templates/index.html` (Flow layer toggle + controls + per-flag readout only)
  - New: `calculator/static/js/flow/flow_overlay.js` (field loading, thresholding, bands, contested zone, particles, seek slider)
  - New: `calculator/static/data/vehicle_speeds.json` (generated)
  - New: `calculator/tests/test_flow_overlay.js`
  - Modified: `AGENTS.md` (one subsection: flow overlay purpose, data provenance rule, movement-numbers-are-configurable rule)
- **Modified data files:** `processed_maps/<map>/metadata.json` (add `sea_level_m`)
- **New data files:** `processed_maps/<map>/gamelayers.json`; `processed_maps/<map>/flow/*.bin|*.png` field grids; `processed_maps/<map>/flow/race_times.json`
- **New maintainer input:** `raw_game_data/` folder holding `objects_vehicles_server.zip`, `objects_common_server.zip`, `common_server.zip`, `objects_statics_server.zip` (never shipped; extraction input only)
- **Out of scope:** replay/demo parsing, navmesh (`.clb`) parsing, hand-annotation tooling, CV/LLM classification, forward-spawn scenario modeling (format-extensible only), video codecs (GIF/MP4/WebM), live data, new Flask routes, new runtime dependencies, ballistics changes

## Terms and Definitions

- **Time-to-reach field:** A per-cell grid where each value is the earliest time (in seconds) an agent starting from any of one team's spawn points can arrive at that cell, given terrain movement costs. Computed offline, shipped as data.
- **Frontier band / isochrone:** The boundary of cells reachable within T seconds; drawn at 60-second intervals by thresholding the field in the browser.
- **Contested zone:** Cells reachable by BOTH teams within a small time delta of each other; where first contact can happen.
- **Race time:** The earliest arrival time at a control point for each team, sampled from the field; shown as "you vs enemy" per flag.
- **Cost grid:** A simulation-resolution grid (target 4 m cells) where each cell stores movement cost derived from roads, slope, water, and building footprints.
- **3-tier binning:** The user's mental model of the cost grid: smooth-passable (roads), bumpy-passable/slow (terrain, forest, urban), and near-impassable (water, ridges); implemented as cost multipliers, never hard walls except for extreme slope.
- **Multi-source Dijkstra:** Shortest-path search started simultaneously from all of one team's spawn points, producing the time-to-reach field.
- **Particle advection:** Moving visual particles along a vector field; here the negative gradient of the arrival field plus small noise, purely for presentation in the browser.
- **Control point (CP):** A flag/objective in the game files, with a numeric `controlPointId`, team, and position.
- **Spawn point:** An infantry spawn location, linked to a control point via `setControlPointId`.
- **Object spawner:** A vehicle spawn location, with a vehicle template name and team.
- **Game-mode layer:** One playable variant of a map, e.g. `gpm_cq/64` (AAS 64-player), `gpm_skirmish/32`.
- **Sea level:** The map's global water height from `heightdata.con` (`heightmapcluster.setSeaWaterLevel`); terrain at or below it is water. Inland water above sea level is handled by a separate flat-region pass.
- **Provenance label:** Text stating where a movement parameter's default came from (extracted from game files, historical community source, uncalibrated, or user-set).
- **Wave-one scope:** The field is sourced only from initial spawn points; forward spawns and rallies that appear after flags are captured are out of scope for v1 and labeled as such.
