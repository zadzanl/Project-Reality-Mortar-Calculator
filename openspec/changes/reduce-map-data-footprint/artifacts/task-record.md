# Task Record: reduce-map-data-footprint

## Intent (relayed user communications)

> "this current environtment that youre running in constant crashes due to OOM. i suspect, it is because reading too much data within processed_maps. you musnt read it directly without tools. you can only probe it. can you find out how to reduce the memory requirement or maybe just .gitignore the whole folder?"

> "this [resolution reduction] might still be needed though, and i would prefer doing it now when the flow simulation isnt finalised. can you plan a resolution/details/precision reduction + file cleanup? try to find which part are actually worth downscaling. also make sure to explore what files are possibly touched by this changes. maybe the best way of doing this is: 1. establishing a baseline/regression test 2. then doing all the actual resolution reduction work, then retesting it all. even quartering the size will be significant: 60GB -> 7.5GB. i suggest creating an openspec change proposal as the first step"

> "Plan looks good. Please proceed with implementation. I've switched your environment from Planning (previous) to Orchestration (current). Make sure to delegate and orchestrate the tasks with subagents when applicable and worthwhile. Please pause right before starting phase 4. Goodluck and godspeed!"

## Constraints

- HARD GATE: baseline captured + committed before any writer file is touched.
- PAUSE before Phase 4 (regenerate/verify/measure) for user gate.
- Never bulk-read `processed_maps/` — probe with listings/sizes only; single files exceed 100 MB.
- Never modify `raw_map_data/`. Exclude `the_falklands` from processing.
- Safe pytest: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`.
- No new dependencies (stdlib + NumPy only for harness; native DecompressionStream in browser).
- Never change physics numbers (gravity 14.86, speed 148.64, range 1500, /65535.0 formula).
- Phases 2 and 3 run SEQUENTIALLY (user-approved plan recommendation: 2.1 fields_of_kassel measurement is a go/no-go gate).

## Environment

- OS: Windows, repo at C:\Projects\Project_Reality-Mortar-Calculator
- Python 3.11.4, Node v24.11.0 (node EXISTS — firing-solution fixture feasibility still open)
- Branch: feat/opening-flow-simulator (f6ba143), DIRTY working tree
- Veteran Engineer first pass: SKIPPED — design already went through profiling-driven review and user approved the plan in the prior session.

## Risks / Open Items

- DIRTY TREE: `add-opening-flow-simulator` change in flight. Modified: calculator/static/js/app.js, flow/flow_core.js, flow/flow_overlay.js, templates/index.html, several processed_maps/*/metadata.json, and more. Our Phase 2.2/3 reader changes touch app.js — must not clobber uncommitted flow work. Branch strategy question to raise with user at Phase 1 -> 2 boundary.
- Flow-sim change may regenerate processed_maps artifacts independently — could invalidate baseline if it lands mid-change. Baseline compare tolerances assume only OUR writers changed.
- Firing-solution baseline may be manual QA (known ceiling) if node can't load the ballistics module.

## Decisions

- D1: obstructions -> compact JSON + 0.1 m rounding + gzip (reuse heightmap.json.gz pattern). Gate: >= 5x on fields_of_kassel.
- D2: terrain grids -> uint16 thresholded / uint8 diagnostic, per-grid {dtype, offset, scale}, format_version "1.2"; loader accepts 1.0/1.1/1.2.
- D3: gzip .bin DEFERRED, gated on post-D1+D2 measurement.
- D4: baseline harness first (processor/baseline.py, capture + compare).
- D5: regenerate -> verify -> cleanup order; rollback via raw_map_data/ regeneration + git.

## Handoffs / Evidence / Verification Log

- 2026-10-09: Task record created. openspec validate --strict: VALID, 4/4 artifacts complete, 0 tasks done.

### Phase 1.1 recon (2026-10-09, 3 Explorers)

- research-001.md (UI readers): Browser NEVER loads terrain/*.bin or obstructions.json — reader changes are processor-only, no JS edits needed for those artifacts. heightmap.js L104-130 gzip pattern: fetch -> blob -> DecompressionStream('gzip') with window.pako fallback; server sends no Content-Encoding (no server change needed for new .gz). build-android.bat renames *.gz->*.gzip and rewrites paths only in app.js/heightmap.js (pre-existing flow_core.js gap, not ours).
- research-002.md (writers): obstructions.json schema pinned (extract_obstructions.py:201-208, indent=2, no rounding); consumers are processor-only (build_terrain_cost.py:592, render_obstruction_qa.py:31, spike_material_map.py:37). Rasterization cell_m min 4.0 m -> 0.1 m rounding safe but NOT bit-identical (boundary cells can flip) -> compare rasterized output with tolerance, not raw JSON. Grid inventory: road_mask/water uint8, <profile>/cost.bin float32 (-1.0 blocked), classes.bin uint8, 8 float32 diagnostics; sentinels -1.0 (float32 internal), 255 (uint8 shipped), flow cap 3600.0 s. Per-map float32 BIGGER than design assumed: 512^2 ~ 11.1 MiB, 1024^2 ~ 44.1 MiB -> quantization savings larger than estimated.
- research-003.md (tests/tooling): node feasibility = YES — ballistics.js is pure ESM, zero browser APIs, already run headlessly by calculator/tests/run-tests.js -> firing-solution fixture feasible. 5 largest obstructions.json: fields_of_kassel 191.5 MB, ascheberg 181.3 MB, korbach_offensive 177.8 MB, road_to_damascus 174.4 MB, shijiavalley 156.1 MB. NumPy 1.26.4 present (undeclared in requirements.txt). Map list: repo-root mapsList.json (85 maps).

### Pre-existing test baseline (2026-10-09, BEFORE any of our changes)

`python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py -q` => **4 failed, 90 passed, 8 errors**. ALL pre-existing, from in-flight add-opening-flow-simulator work:
- FAILED: test_flow_field.py::test_land_diagonal_cannot_cut_between_blocked_orthogonal_cells, ::test_v2_normal_generation_filters_selected_sources_and_keeps_classes
- FAILED: test_terrain_artifact.py::test_loader_returns_flow_contract, ::test_loader_rejects_wrong_grid_length
- ERRORS (8): all in test_terrain_cost.py (deleted config fixture + parametrize decorators)
Our gate: after our work, same failures/errors, no new ones.

### Decisions added during execution

- D6: baseline harness decodes artifacts DIRECTLY (sidecar JSON + np.fromfile), NOT via terrain_artifact.py loader — that loader is mid-refactor in the dirty tree and must not be a harness dependency.
- D7: obstruction fixture = normalize-then-hash (round coords to 0.1 m, sort, sha256) + record count + bbox, so post-compaction compare verifies semantic equality rather than raw bytes (raw sha256 expected to change).
- Dirty processor files from in-flight flow work: build_flow_fields.py, build_terrain_cost.py, extract_obstructions.py + others. terrain_artifact.py itself is CLEAN at HEAD. Coordination question for user before Phase 2/3 edits: edit on top of dirty tree vs wait for flow work to commit.
