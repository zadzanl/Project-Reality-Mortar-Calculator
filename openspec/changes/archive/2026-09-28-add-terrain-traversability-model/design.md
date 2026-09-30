## Context

The separate `add-opening-flow-simulator` work established the map coordinate and obstruction foundation, but it does not yet build a terrain movement model. The completed foundation includes authoritative metadata repair from `heightdata.con`, corrected BF2-to-repository coordinates, triangle-based road extraction, static and vegetation extraction, and QA minimap overlays. The current obstruction output is evidence about explicit roads and placed objects; it is not a traversability field.

The repository's heightmaps are authored 16-bit rasters, commonly 513 or 1025 samples over 1024, 2048, or 4096 meter worlds. Sample spacing therefore varies by map, commonly about 2 or 4 meters. The future opening-flow solver is planned to operate on approximately 4 meter cells. Some maps, including Adak, have `compiledroads.con` references but no local `client.zip`, so road geometry can be unavailable even when road definitions exist.

The model must answer a narrower and more honest question: how expensive is movement through each terrain cell for a chosen agent class, given available height, road, water, vegetation, and obstruction evidence? It must not pretend that a flat heightmap cell is a verified road or that a static object point is an exact collision footprint.

## Goals / Non-Goals

**Goals:**

- Convert heightmap samples to meters using repaired authoritative metadata and the repository's fixed 65535 formula.
- Derive native-resolution slope with a documented metric gradient and correct edge behavior.
- Preserve local elevation changes that can represent steps, ledges, berms, and short banks before simulation-grid aggregation.
- Provide an optional small metric-scale detrended roughness signal without using a map-relative smoothing window as the primary classifier.
- Aggregate terrain evidence into a continuous movement-cost grid at the planned simulation resolution.
- Keep explicit road membership, ordinary terrain, water evidence, vegetation density, and static-object penalties as separate inputs.
- Record engine-painted surface material as an additive diagnostic evidence layer when decodable from client archives; it is not a movement-cost input by default (D9).
- Produce diagnostic classes and QA images that explain why cells are smooth, rough, slow, extreme-slope, road, water, or unknown.
- Record units, thresholds, source coverage, provenance, resolution, and uncertainty in sidecars.
- Make the output consumable by the later opening-flow Dijkstra stage without putting terrain physics in the browser.

**Non-Goals:**

- Do not infer roads from flatness, low slope, color, or minimap appearance. (Engine-painted material data, when decodable, is extraction of a game-authored designation, not inference; it is diagnostic-only by default. See D9.)
- Do not adopt the full ETH Zurich ROS stack, Recast voxel/navmesh pipeline, TRI/VRM as the primary classifier, or any new runtime dependency.
- Do not make the surface-material layer a movement-cost multiplier by default; the uniform-surface default stands until the material speed effect is verified.
- Do not claim exact collision geometry from static object points or heightmaps.
- Do not solve missing `client.zip` archives; report them as unavailable input and preserve ordinary terrain processing.
- Do not change the frozen ballistics constants or modify raw archives.
- Do not implement the opening-flow Dijkstra solver or browser overlay in this change; this change supplies and validates its cost-grid input.
- Do not make water or buildings hard impassable by default. Only a configured extreme-slope condition may be hard blocked.

## Decisions

### D1: Use metric native-resolution slope as the primary terrain signal

Convert each raw sample to elevation meters, then use central differences on the native raster with `d = map_size / (resolution - 1)`. Compute gradient magnitude and slope angle. Use one-sided differences at the outer boundary rather than padding with invented elevations.

Horn's 3x3 estimator is a valid alternative, but the existing approved flow design already specifies central differences and the authored heightmaps do not require a robotics sensor-denoising pipeline. Implement one method first and document it in the sidecar; do not maintain two competing slope implementations without evidence.

### D2: Keep local edge rise separate from average slope

For each horizontal and vertical neighbor edge, retain absolute elevation rise and rise divided by edge distance. Optionally include diagonal edges with the correct `sqrt(2) * d` distance. Aggregate edge hazards conservatively into the simulation cell. This prevents a short ledge from disappearing when a wider cell is averaged.

The concepts correspond to Recast's maximum walkable slope and climb-height filters, but the implementation remains a heightmap edge test. Recast itself is not used because this repository does not have a geometry-complete triangle mesh or voxel span model.

### D3: Use bounded metric roughness, not a map-width moving average

Compute optional roughness as local detrended elevation residual RMS over a small odd window, initially 3x3 and configurable to 5x5. The window is expressed in meters or sample count derived from meters, not `map_size / 32`. A broad map-relative window may be retained only as an experimental macro-context diagnostic and must not erase local step or ridge signals.

The first production default records roughness and may apply a configured multiplier only when the QA policy enables it. All coefficients are pipeline inputs with provenance, not frozen Project Reality facts.

### D4: Separate terrain class from explicit road membership

A cell may be low-cost terrain without belonging to a road. Road triangles, when decoded, provide an independent explicit road mask and optional speed modifier. Missing client archives produce `road_coverage = missing_client_zip` or equivalent diagnostic status; they do not turn the terrain grid into an empty or blocked map.

The extractor may add additive road-coverage metadata to the obstruction output or a companion report. Existing road triangle, static, and vegetation fields remain compatible.

Road segments whose names match decal classes (stain, decal, parkinglot, oilstain; measured 386 of 7213 segments corpus-wide, about 5.4%) are surface decorations, not drivable road geometry. They must be filtered or flagged before the road-membership mask is built, with per-map flagged counts shown in QA.

### D5: Use continuous cost with diagnostic categories

Store one numeric movement cost per simulation cell. Derive labels for QA only. The baseline combination is:

`cost = base_cost * slope_multiplier * roughness_multiplier * water_multiplier * obstruction_multiplier * vegetation_multiplier`

Road membership can apply a configured modifier but cannot bypass an extreme-slope or step hazard unless an explicit future bridge/deck source exists. Water and buildings remain high-cost and passable by default. The only default hard block is an extreme slope/edge condition configured for the agent class.

Suggested diagnostic labels are `smooth_traversable`, `rough_traversable`, `slow`, `extreme_slope`, `water`, `road`, and `unknown`. Labels must not imply that terrain is a verified surface material when the source only supports a geometric estimate.

### D6: Treat water evidence conservatively

Use authoritative sea level and boundary-connected low-elevation regions as strong water evidence. A flat inland region above sea level is only a candidate unless another source supports water; it must not be silently promoted to water solely because it is flat. Candidate inland-water regions may be emitted in diagnostics and receive a configurable penalty under an explicit policy.

This prevents runways, courtyards, beaches, dry riverbeds, and flat fields from being mislabeled as water. The existing D8 flat-region idea is retained as a candidate detector, not an unquestionable semantic classifier.

### D7: Aggregate hazards conservatively during downsampling

When native terrain features are reduced to approximately 4 meter simulation cells, ordinary continuous values may be averaged, but maximum slope and step/ledge signals must be retained with a documented conservative reduction. A dangerous edge must not disappear merely because most of the target cell is flat.

If a source heightmap is already coarser than the target grid, the sidecar records degraded input resolution and the pipeline does not invent subcell detail through oversampling.

### D8: Validate with synthetic terrain and map QA before solver integration

Synthetic tests are the primary algorithm regression gate: flat plane gives zero slope and near-zero detrended roughness; a tilted plane gives expected slope and near-zero detrended roughness; a single step retains an edge hazard; a ridge above the configured threshold is blocked or heavily penalized; and an ordinary flat cell remains passable with no road mesh.

Map QA uses Asad Khal, Adak, and Muttrah City 2 or another urban map. QA compares slope/cost maxima with contour density and checks that missing roads do not erase terrain. It does not claim that minimap pixels are ground truth for collision or movement speed.

### D9: Engine-painted surface material as an optional additive diagnostic

Each client.zip ships `detailmaps/txNNxNN_{1,2}.dds`: uncompressed 16-bit 256x256 per-tile textures (format verified on asad_khal by DDS header parse), almost certainly the engine's painted per-texel surface-material assignment. `raw_game_data/common_server.zip` ships `material/materialmanagerdefine.con` with per-surface physics (verified verbatim: Tarmac friction 1.2 / resistance 0.04, Dirt 0.9 / 0.1). This is extraction of a game-authored surface designation, not inference from flatness, slope, or color, so it does not violate the non-goal above.

A bounded spike on Asad Khal (client.zip present; decoded road triangles available as a cross-check) decodes the textures, resolves the index-to-material wiring, and measures road-triangle overlap with the dominant material index. If confirmed, the pipeline emits a per-cell material class (for example `paved_material`) in the diagnostic grid and sidecar ONLY: it is not a cost multiplier by default, consistent with the unverified surface-speed question. The material physics table is recorded in the terrain configuration with provenance "extracted from v1.9 files, speed effect unverified". If the spike fails, the layer is dropped and nothing else in this design changes.

## Risks / Trade-offs

- [Unverified movement thresholds] Project Reality v1.9 slope, step, roughness, and road-speed parameters are not fully verified. -> Keep them in a config with provenance, default to conservative passable costs, and label estimates in sidecars.
- [Heightmap resolution] A 2-4 meter raster cannot represent small curbs, foliage, overhangs, or narrow collision openings. -> Report resolution limits and never claim centimeter-level collision accuracy.
- [Missing road archives] Empty road output can be mistaken for no roads. -> Add explicit coverage status and show it in QA reports; process remaining terrain independently.
- [Water ambiguity] Flatness can identify candidate basins but not material type. -> Separate confirmed water from candidate inland water and avoid hard blocking.
- [Static heuristic] Name classification and point placement are not collision footprints. -> Keep static penalties heavy but passable, include classification counts, and document the upgrade path to collision meshes or navmesh data.
- [Downsampling loss] Averaging can erase a narrow ledge or ridge. -> Preserve maxima for edge rise and extreme slope during aggregation and test synthetic steps.
- [Overfitting] Tuning thresholds to one map can damage another. -> Validate across map sizes, terrain types, and source resolutions; record per-map overrides explicitly.
- [Performance and output size] Full-resolution feature arrays can be large. -> Compute features offline, emit compact float or integer grids with sidecars, and keep the browser uninvolved.
- [Unresolved elevation residuals] Existing spawn-vs-heightmap checks still show residuals on some maps. -> Resolve or document the sampling convention before treating slope-derived costs as calibrated movement predictions.
- [Material texture semantics] The detailmap DDS format is verified but its per-texel semantics are not. -> The D9 spike is cheap and falsifiable and runs before any consumer is built; on failure the layer is dropped and the rest of the design is unchanged.
- [Decal-class road segments] About 5.4% of compiled road segments are stain/decal meshes, not drivable roads. -> Filter or flag decal-class names before building the road mask; show flagged counts in QA.

## Migration Plan

1. Verify the existing corrected metadata and obstruction outputs before terrain processing. Do not rerun or overwrite raw inputs.
2. Add the terrain feature and cost-grid builder behind maintainer-side commands. Generate outputs in a new per-map terrain directory so existing obstruction and calculator data remain readable.
3. Run synthetic tests and selected-map QA. Record thresholds, source coverage, and any map-specific overrides in sidecars.
4. Integrate the terrain grid into the later opening-flow builder as a new input, not by duplicating terrain calculations in the solver or browser.
5. Roll back by deleting generated terrain outputs and disabling the later flow-builder input; existing minimap, metadata, obstruction JSON, and calculator behavior remain available.

## Open Questions

- Which movement profiles need separate thresholds first: infantry only, or infantry plus a generic wheeled vehicle profile?
- Should roughness affect the default cost in the first implementation, or be emitted for QA with multiplier 1.0 until map review approves it?
- (Resolved) Recollection of the 15 missing `client.zip` archives is now a tracked maintainer task (tasks.md section 7) via the existing collect_maps.py pipeline, no longer an open question.
- Which maps provide trusted gameplay or maintainer annotations for calibrating slope, step, and road modifiers?
- Should future water-source work parse terrain material data, collision data, or a curated per-map water patch before inland water affects costs? (Partially answered by D9: once decodable, a water material class may serve as independent water evidence; any cost impact still requires an explicit policy.)
