## 1. Reconcile Existing Obstruction Foundation

- [x] 1.1 Verify `processor/bf2_mapinfo.py` reads authoritative `heightdata.con` map size, primary height scale, resolution, and sea level without modifying raw archives.
- [x] 1.2 Verify repaired `processed_maps/<map>/metadata.json` values and provenance for all available server archives, including the Asad Khal 1024 meter correction.
- [x] 1.3 Verify `processor/bf2_road_mesh.py` accepts observed nonzero header variants while retaining finite-value, bounds, triangle, and index validation.
- [x] 1.4 Verify `processor/extract_obstructions.py` emits world-space road triangles, static classifications, vegetation positions, counts, and per-map errors without double-reading `staticobjects_old.con`.
- [x] 1.5 Verify QA overlays for Asad Khal, Fools Road, Muttrah City 2, Belyaevo, and Adak exist and distinguish missing client archives from ordinary empty terrain.

## 2. Terrain Feature Extraction

- [x] 2.1 Add a maintainer-side terrain feature module that loads compressed heightmap JSON and repaired metadata using only existing Python and NumPy dependencies.
- [x] 2.2 Convert raw height samples to meters using the fixed `65535.0` formula and calculate sample spacing as `map_size / (resolution - 1)`; record units and source metadata.
- [x] 2.3 Implement native-resolution central-difference slope with documented one-sided boundary handling and slope angle output.
- [x] 2.4 Implement cardinal and diagonal neighboring-edge rise and grade features with correct metric distances.
- [x] 2.5 Implement configurable odd-window detrended roughness using local elevation residual RMS; reject or flag map-width-relative `map_size / 32` primary windows.
- [x] 2.6 Add a terrain configuration with agent-profile thresholds and multipliers, provenance strings, and deliberately uncalibrated defaults where Project Reality v1.9 evidence is unavailable.
- [x] 2.7 Record the extracted material physics table (`materialmanagerdefine.con` friction/resistance per surface) in the terrain configuration with provenance "extracted from v1.9 files, speed effect unverified"; do not wire it into costs by default.

## 3. Simulation-Grid Cost Construction

- [x] 3.1 Define the terrain artifact schema: compact cost grid, diagnostic class grid, feature summaries, origin, cell size, source coverage, configuration hash or values, and provenance sidecar.
- [x] 3.2 Aggregate native features to approximately 4 meter cells without inventing detail; average ordinary costs and conservatively retain maximum slope and edge-rise hazards.
- [x] 3.3 Rasterize explicit road triangles as an independent road-membership mask and apply only the configured road modifier; do not make low-slope non-road cells roads.
- [x] 3.4 Apply continuous slope, roughness, vegetation, and heuristic static-object multipliers while keeping water and buildings passable by default.
- [x] 3.5 Apply the configured extreme-slope or edge hazard rule as the only default hard-block condition, with passability sentinel and reason recorded in diagnostics.
- [x] 3.6 Preserve degraded-resolution status when source spacing is coarser than the requested simulation grid and prevent false subcell precision.
- [x] 3.7 Reserve an additive per-cell surface-material field in the artifact schema (absent or `unknown` until the section 7 spike confirms decodability); absence must not break the loader contract.
- [x] 3.8 Filter or flag decal-class road segments (stain/decal/parkinglot/oilstain names; about 5.4% of segments corpus-wide) before rasterizing the road-membership mask; log per-map flagged counts.

## 4. Water and Coverage Semantics

- [x] 4.1 Derive confirmed water evidence from authoritative sea level and documented connected low-elevation rules.
- [x] 4.2 Emit inland flat-region results as candidate or unknown water evidence unless an independent source supports confirmed water; never infer water from flatness alone.
- [x] 4.3 Add explicit road coverage states for complete extraction, missing client archive, no road definitions, missing mesh records, and partial extraction.
- [x] 4.4 Ensure maps with missing `client.zip`, including Adak, still receive terrain cost and diagnostic outputs from heightmap and available obstruction evidence.
- [x] 4.5 Keep road, terrain, water, vegetation, and obstruction signals independently inspectable in output metadata and QA rendering.

## 5. Regression Tests and QA Overlays

- [x] 5.1 Add synthetic flat-plane tests for zero slope, near-zero roughness, ordinary passability, and no-road behavior.
- [x] 5.2 Add synthetic analytic-ramp tests for slope magnitude and tilted-plane detrended roughness.
- [x] 5.3 Add synthetic one-cell step and ridge tests proving edge hazards survive simulation-grid aggregation and thresholding.
- [x] 5.4 Add tests for cardinal versus diagonal edge distance and for boundary-gradient handling.
- [x] 5.5 Add tests for confirmed water, candidate inland water, missing client archive, and no-road-definition status.
- [x] 5.6 Add a deterministic terrain QA renderer that overlays cost classes, road membership, water evidence, and source-coverage warnings on the minimap.
- [x] 5.7 Generate and inspect QA overlays for Asad Khal, Adak, Muttrah City 2, and at least one map with coarse source resolution; record findings and per-map overrides.
- [x] 5.8 Validate slope and cost patterns against contour density without treating minimap imagery as collision ground truth.

## 6. Integration Readiness and Documentation

- [x] 6.1 Add the terrain artifact loader contract for the later offline opening-flow solver, including grid dimensions, origin, cell size, costs, passability sentinel, and provenance.
- [x] 6.2 Confirm the browser and Flask server do not calculate terrain features or depend on new routes or external services.
- [x] 6.3 Document known limits: heightmap resolution, missing client archives, heuristic static classes, unresolved elevation residuals, and uncalibrated movement thresholds.
- [x] 6.4 Write `openspec/changes/add-terrain-traversability-model/artifacts/implementation-terrain-001.md` with commands, test outputs, QA map list, thresholds, source coverage, and anything not verified.
- [x] 6.5 Run `python -m pytest processor/tests/`, `node calculator/tests/run-tests.js`, and the terrain-specific verification command; report exact failures without claiming unverified success.

## 7. Engine Material Spike (Additive Diagnostic, D9)

Runs in parallel with sections 2-5; nothing in those sections may depend on its outcome.

- [x] 7.1 Decode one `detailmaps/txNNxNN_1.dds` tile from the asad_khal client.zip with struct+numpy (verified format: 128-byte DDS header, uncompressed 16-bit, 256x256); histogram values across all tiles.
- [x] 7.2 Resolve the index-to-material wiring (candidates in order: map server.zip terrain.con, common_server.zip material/materials.json and material/cells.json, materialmanagerdefine.con ordering); if unresolvable, record the unnamed-cluster fallback (paved cluster identified via road-triangle overlap).
- [x] 7.3 Cross-validate: rasterize asad_khal road triangles onto the material grid, record the overlap percentage with the dominant index, and eyeball a debug overlay of the material mask over the minimap.
- [x] 7.4 Record go/no-go in `openspec/changes/add-terrain-traversability-model/artifacts/material-spike-001.md`. On go: emit the per-cell material class as a diagnostic only (never a default cost multiplier) and add it to the QA renderer. On no-go: drop the layer and record why.
- [x] 7.5 Maintainer task (no code): recollect the 15 missing client.zip archives (adak, ascheberg, bamyan, battle_of_kerch, burning_sands, fields_of_kassel, hades_peak, kashan_desert, khamisiyah, korbach_offensive, kunar_province, masirah, operation_bobcat, operation_soul_rebel, saaremaa) via the existing collect_maps.py pipeline; re-run extraction for those maps.
