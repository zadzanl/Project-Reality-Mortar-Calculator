# Task Record: add-terrain-traversability-model (Implementation)

## Intent

User communication (copy-pasted 1:1):

> Alright, plan looks mature and ready to implement. please proceed with implementation. Please make sure to delegate tasks to all the subagents you have access to. Make sure to adhere to efficient engineering, retrieval-first, and good code writing -principles.

Inferred goal: implement the merged `add-terrain-traversability-model` change (tasks.md
sections 2-7; section 1 already complete) end-to-end, orchestrating subagents where
delegation adds value, with Review Orchestrator coverage per phase.

## Constraints

- ASCII-only in all files.
- Python stdlib + numpy only; no new dependencies. Browser untouched.
- Never modify raw_map_data/ or raw_game_data/; zips read-only, in-memory.
- the_falklands stays excluded.
- Water/buildings heavy-cost but passable; only configured extreme slope hard-blocks.
- Movement thresholds are config inputs with provenance, never frozen facts.
- Match existing style: 4-space Python, extractor progress/summary pattern, plain pytest
  functions with inline fixtures, JSON artifacts with format_version + provenance.
- Working tree has uncommitted prior work (metadata repairs etc.) - do not clobber.

## Decisions

- Veteran Engineer first-pass gate: CONSUMED during planning (2026-09-27 challenge pass
  produced the material-map finding merged as D9). Budget 1/1 used.
- Model selection: no model overrides on any runSubagent call (policy).
- Merge decisions (user-approved 2026-09-27): adopt this change as plan of record +
  3 additions (D9 material spike, decal filtering, client.zip recollection task).
  Material spike runs parallel with sections 2-5; nothing depends on its outcome.
- Delegation plan: orchestrator implements core modules directly (sections 2-6);
  Assistant subagent gets the bounded, independent material spike (section 7);
  Review Orchestrator after each phase.
- Slope: central differences via np.gradient(edge_order=1) - documented numpy idiom for
  interior central + boundary one-sided differences (D1).
- Roughness: local least-squares plane residual RMS via sliding windows (D3), ETH
  traversability_estimation roughness-filter concept (see
  add-opening-flow-simulator/artifacts/research-traversability-methods-001.md).
- Artifact format: raw little-endian float32/uint8 .bin grids + JSON sidecar
  (deterministic, byte-for-byte reproducible), per design D5/spec "Deterministic
  terrain artifacts".

## Evidence

- `openspec validate add-terrain-traversability-model` -> valid (post-merge).
- `openspec status`: 43 tasks, 5 complete (section 1), 38 remaining.
- Ground-truth repair verified: asad_khal metadata map_size=1024, height_scale=163.8375,
  heightmap_size_source provenance key present.
- heightmap storage: processed_maps/<map>/heightmap.json.gz (gzipped JSON, uint16 flat
  row-major, keys resolution/width/height/format/data/compression).
- obstructions.json schema: roads [{name, triangles [[[x,y]x3], ...]}], statics
  [{template, class, x, y, rotation_deg}], vegetation [{template, x, y}], counts.
- Decal pollution measured: 386/7213 road segments match stain/decal/parkinglot/oilstain.
- Material table verified verbatim in common_server.zip material/materialmanagerdefine.con
  (Tarmac friction 1.2 / resistance 0.04; Dirt 0.9/0.1).
- detailmaps tx DDS format verified on asad_khal: 128-byte header, uncompressed 16-bit,
  256x256 per tile. Semantics UNVERIFIED (section 7 spike).

## Handoffs

- 2026-09-27 Assistant subagent: material spike (tasks 7.1-7.4). Verdict NO-GO: all 32
  asad_khal detailmap tiles decode as uncompressed RGB565 COLOR textures, not material
  indices; no DDS-word-to-material-ID wiring found in any candidate source; road-triangle
  overlap showed no dominant signal (best raw word 19.6% of road texels). Per design D9's
  recorded fallback, the material layer is DROPPED; nothing else changes. Evidence:
  artifacts/material-spike-001.md, artifacts/material_overlay_asad_khal.png,
  processor/spike_material_map.py. The spike also contradicted one supplied 'verified
  fact' (DDS pitch field reads 131072, not 512); data was trusted over the brief.
- 2026-09-27 Review Orchestrator, Phase 1: NEEDS_REVISION (S1-F01 incomplete extraction
  could overwrite config) -> fixed (validate-before-write, atomic os.replace, regression
  test tests/test_material_table.py) -> re-review APPROVED (review-record-phase1-002.md).

## Verification

(pending)

## Revisions

(none)

## R3 - 2026-09-28 coarse roughness repair and batch resume

- Reproduced the Shipment failure: 257 samples over 4096 m gives 16 m source
  spacing; the minimum valid 3-sample roughness window would be 48 m, above the
  24 m feature-scale bound.
- Implemented bounded degradation: coarse sources report
  `unavailable_coarse_source`, omit roughness from aggregation, retain slope and
  edge features, and reject processing only if roughness cost is explicitly
  enabled. The bound is imported from `terrain_features.MAX_ROUGHNESS_WINDOW_M`.
- Added truthful sidecar metadata provenance: maps with a recorded
  `heightmap_size_source` containing `heightdata.con` are marked
  `verified_from_heightdata_con`; legacy metadata is marked
  `unverified_legacy_metadata`.
- Added coarse threshold, downstream aggregation/classification/cost, and batch
  continuation regressions. Review `review-record-repair-r2-001.md` returned
  APPROVED after revision.
- Focused verification: `python -m pytest processor/tests/test_terrain_features.py
  processor/tests/test_terrain_cost.py` -> 37 passed.
- Resumed explicitly with Shipment and the 14 maps after the interruption. The
  command processed 15/15 maps with no failures.
- Artifact verification found all expected sidecars and binary dimensions valid
  for all 15 maps. Shipment is 256x256 at 16 m cells and records unavailable
  roughness plus unverified legacy metadata. Full safe processor suite:
  `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`
  -> 93 passed.
