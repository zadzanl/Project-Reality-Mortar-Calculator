## Why

The obstruction extractor now places available roads, static objects, and vegetation in the correct map coordinate frame, but obstruction geometry alone does not describe traversability. A map can contain passable flat terrain without an extracted road mesh, while a steep ridge, ledge, water body, building cluster, or vegetation field can slow movement independently of road membership. The next change must convert the authoritative heightmap and existing obstruction inputs into an explainable terrain-cost model without inventing roads from flatness.

This change is separate from `add-opening-flow-simulator` so the terrain model can be designed, tested, and reviewed independently before it becomes an input to the opening-flow solver or browser overlay.

## What Changes

- Add a maintainer-side terrain analysis pipeline that converts each processed 16-bit heightmap into metric elevation values using the repaired authoritative metadata.
- Calculate native-resolution terrain slope using a documented local-gradient method, with correct sample spacing and boundary behavior.
- Retain local neighbor-to-neighbor elevation changes as a separate step/ledge signal before downsampling to the simulation grid.
- Add an optional small metric-scale roughness signal based on local detrended elevation residuals; do not use a map-width-relative moving average as the primary classifier.
- Produce a continuous movement-cost grid and a parallel diagnostic classification such as smooth-traversable, rough-traversable, slow, extreme-slope, water, road, and unknown.
- Keep explicit road membership separate from ordinary low-cost terrain. Missing `client.zip` road geometry must not make all other terrain impassable or silently imply that no roads exist.
- Combine terrain signals with existing road triangles, obstruction records, vegetation density, sea-level data, and conservative water detection while preserving the project's rule that water and buildings are heavy-cost and passable rather than hard walls.
- Add QA overlays and synthetic regression checks for flat planes, ramps, steps, ridges, coastlines, and maps with unavailable road meshes.
- Record source coverage, thresholds, units, movement-parameter provenance, and known uncertainty in generated sidecars and reports.
- Add a bounded spike to decode engine-painted terrain material index textures (`detailmaps/tx*.dds` in client.zip) and record the material physics table (`materialmanagerdefine.con` friction/resistance) with provenance; on success, emit an additive `paved_material` diagnostic layer that is not a movement-cost input by default.
- Filter or flag decal-class road segments (stain/decal/parkinglot meshes, about 5.4% of segments corpus-wide) so the road-membership mask reflects drivable roads.
- Track recollection of the 15 missing `client.zip` archives as a maintainer task via the existing collect_maps.py pipeline.
- Preserve the completed obstruction foundation from the separate change: authoritative `heightdata.con` metadata repair, corrected BF2 road-mesh variant handling, triangle-based road output, static/vegetation extraction, and generated minimap QA overlays.

## Capabilities

### New Capabilities

- `terrain-traversability`: Derive and validate continuous terrain movement cost and diagnostic traversability classes from heightmaps plus separately sourced roads, water, vegetation, obstruction, and (optionally, spike-gated) engine-painted surface-material evidence.

### Modified Capabilities

<!-- No existing repository capability requirement is modified by this change. The opening-flow solver will consume this capability in a later integration phase. -->

## Impact

- New maintainer-side modules under `processor/`, centered on terrain feature extraction, cost-grid construction, and QA rendering.
- New processor tests for metric conversion, slope, step detection, roughness, aggregation, and passability rules.
- New per-map terrain-cost data and diagnostic overlays under `processed_maps/<map>/` and OpenSpec artifacts.
- Existing `processed_maps/<map>/obstructions.json` remains the source for explicit road and obstruction evidence; its schema is not silently changed.
- Existing `processor/bf2_mapinfo.py`, repaired metadata, `processor/extract_obstructions.py`, and `processor/bf2_road_mesh.py` are prerequisites and verification inputs, not replacements.
- Optional additive surface-material diagnostic in terrain artifacts, gated on a falsifiable spike; `raw_game_data/common_server.zip` material physics table recorded with provenance (never shipped raw).
- No browser physics, new Flask route, external service, raw archive modification, new runtime dependency, or ballistics change.
