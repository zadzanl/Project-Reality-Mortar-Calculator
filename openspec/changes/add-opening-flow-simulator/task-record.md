# Task Record: add-opening-flow-simulator (Implementation)

## Intent

User communication (copy-pasted 1:1):

> Alright, plan looks good.  I've switched your environtment from planning (previous) to implementation/orchestration (current) Please proceed with implementation. Please make sure to delegate tasks to all the subagents you have access to. Make sure to adhere to efficient engineering, retrieval-first, and good code writing -principles.
>
> Please never hesistate to ask questions whenever needed. Good luck and godspeed!

Inferred goal: implement the approved OpenSpec change `add-opening-flow-simulator` end-to-end (Phases A-D in tasks.md), orchestrating subagents where delegation adds value, implementing each phase directly, with Review Orchestrator coverage after each phase.

## Constraints

- ASCII-only in all files.
- No new runtime dependencies (Python stdlib + numpy; browser = vanilla ES modules + vendored Leaflet/pako).
- Never modify `raw_map_data/` or `raw_game_data/`; never ship PR zips.
- No video codecs. No browser physics. No server changes.
- Movement numbers are pipeline inputs with provenance labels; ballistics constants frozen.
- `the_falklands` stays excluded.
- Match existing code style (4-space Python, 2-space JS).

## Decisions

- D1-D10 as recorded in design.md (approved).
- Veteran Engineer first-pass gate: SKIPPED. Justification: the design already survived multiple challenge rounds during planning (D1-D10 each record alternatives considered and rejected), the user explicitly approved the plan, and the remaining work is execution against a validated spec (`openspec validate` passes). A re-challenge now would repeat settled ground. Recorded per orchestration-policy budget (1 pass max; 0 used).
- Model selection: no model overrides on any runSubagent call (policy).

## Evidence

- `openspec validate add-opening-flow-simulator` -> exit 0 (pre-implementation).
- Python 3.11.4, numpy 1.26.4, PIL, matplotlib 3.7.2 available.
- `raw_game_data/`: common_server.zip, objects_common_server.zip, objects_statics_server.zip, objects_vehicles_server.zip all present.
- asad_khal server.zip: 60 entries; layers gpm_coop/{16,32,64,128}, gpm_cq/{32,64}, gpm_gungame/16, gpm_skirmish/{16,32,64}; compiledroads.con, staticobjects.con, heightdata.con present.
- asad_khal metadata: map_size 4096, height_scale 300, heightmap 513px.
- gameplayobjects.con format confirmed by inspection: ObjectSpawner/SpawnPoint/ControlPoint templates + `Object.create` instances with `Object.absolutePosition X/Y/Z`, `Object.layer N`. CP ids via `ObjectTemplate.controlPointId`; spawns link via `ObjectTemplate.setControlPointId`.
- asad_khal gpm_cq/32: 36 positioned objects; X range -318..357, Z range -374..417 (center-origin confirmed; play area is a small subset of the 4096m terrain).
- `heightmapcluster.setSeaWaterLevel 49` present in asad_khal heightdata.con.

## Handoffs

- 2026-09-26 Assistant subagent: decoded BF2 compiled road mesh format. Delivered `processor/bf2_road_mesh.py`, `artifacts/road-mesh-format.md`, `artifacts/spike_roads_asad_khal.png`. Claims: 62/62 asad_khal segments decoded, exact size accounting on 3 file sizes, origins match compiledroads.con within 0.0005 m. Orchestrator independently re-verified: decoder runs, dirtroad20 -> 268 vertices / 290 triangles, bytes_consumed == file_size, plot traces the minimap road network exactly.
- 2026-09-26 Explorer subagent: found public Godot BF2 importer documenting the same layout (52-byte pre-vertex region, 32-byte vertices [position xyz, UV0, UV1, alpha], uint16 indices). Cross-validates the Assistant decode. `artifacts/research-road-mesh-format.md`.
- Spec deviation recorded: planning assumed compiledroads.con holds "polylines with widths" — FALSE, it holds mesh references; geometry lives in client.zip compiled meshes. Specs/design/tasks updated to match reality. Roads are now exact triangle geometry, not heuristic.

## Verification

- Spike 1.1: transform confirmed `x = X + size/2`, `y = size/2 - Z` (+Z north) via named CPs on asad_khal; heightmap/minimap orientation confirmed via sea-level water masks on adak + fools_road. Evidence: `artifacts/spike_asad_khal_zoom.png`, `artifacts/spike_water_{adak,fools_road}.png`.
- Task 1.2/1.3: `python processor/extract_gamelayers.py` -> "Summary: 66/66 maps processed", zero errors. Spot-check: asad_khal gpm_cq/32 idfbase -> x=2298.09, y=2396.116, elevation_m=47.011, matches hand computation. metadata.json gained sea_level_m=49 additively (all prior keys preserved).
- Bug found and fixed during verification: dict key-order collision overwrote elevation with repo y (elevation_m held 2396.116 instead of 47.011). Fixed by popping elevation before writing repo y; re-verified against known values.

## Revisions

### R1 - 2026-09-27 interrupted-delegation audit

User request (verbatim):

> All 3 subagent dispatch seems to have hit a provider rate limit in this environtment. To fix this, can you please dispatch a 2nd set of 3 explorer subagents to check where did those 3 assistant left off? Compare it with your original dispatch instruction for those 3 assistant subagent. The output needs to be 3 report (1 for each subagent) on where did they left off, what is finished, and what is unifished

Scope: audit only; do not resume implementation or modify existing outputs. Three parallel Explorers will compare original dispatches, child logs, and current files. Each may write only its own recovery report in this artifacts directory.

Original sessions (parent 117d16f2-f5a0-41ab-acac-f1c0f5e9bb17):
- Obstructions: toolu_b71915f8964326b6; parent span 000000000000063f. Parent result: completed with no output; completion unverified.
- Vehicle speeds: toolu_949c15500ff62ffd; parent span 0000000000000640. Parent result explicitly reports HTTP 429.
- Infantry parameters: toolu_ff7a2b0466ce5624; parent span 0000000000000641. Parent result explicitly reports HTTP 429.

Expected reports: recovery-obstructions-001.md, recovery-vehicle-speeds-001.md, recovery-infantry-params-001.md. Acceptance: original requirements compared individually against evidence; last recorded action; finished/partial/unfinished work; verification gaps; exact resume point; non-empty attempt log. Existing unrelated working-tree changes must remain untouched.

Recovery results:
- `recovery-obstructions-001.md`: task 1.4 is unfinished. The existing road decoder and research are preexisting prerequisites; no extractor, obstruction JSON, QA overlay, or verification was evidenced. The worker stopped after retrieval/advisory work when its final inventory command was canceled.
- `recovery-vehicle-speeds-001.md`: task 1.5 has a useful uncalibrated spike report with five representative quotes and the single M3 anchor; task 1.6 is unfinished. No extractor or generated JSON exists. The parent interruption was HTTP 429.
- `recovery-infantry-params-001.md`: ZIP search research found candidate soldier parameters and explicit negatives, but task 1.7 deliverables and JSON verification are absent. The parent interruption was HTTP 429.

Verification of recovery outputs: all three report files exist with nonzero size. Direct file checks show `processor/extract_obstructions.py`, `processor/extract_vehicle_speeds.py`, `calculator/static/data/vehicle_speeds.json`, `processor/movement_params.json`, and `processed_maps/asad_khal/obstructions.json` are absent; `vehicle-speed-spike.md` exists; `infantry-params-search.md` is absent.

### R2 - 2026-09-27 ground-truth root cause (obstruction inaccuracy)

User request (verbatim):

> Just from the result of the 1.4 subagent, there also seems to be something odd going on with the obstruction extractor causing it to be highly inaccurate. Can you please create a handoff brief that i send to a new, fresh context agent so that they can finish it properly?

Redispatched workers completed: vehicle speeds (791 entries, 4 tests pass), infantry params (baselines + candidates artifact), obstructions (66/66 maps, tests pass) — but the obstruction QA overlay showed all data compressed into the map center. Orchestrator diagnosis:

- All asad_khal obstruction data spans repo coords ~1538..2560 (central ~1024m of a metadata-claimed 4096m map).
- Root cause: `process_one_map.py` fallbacks. `parse_init_con` regex never matches (`heightmapcluster.create HeighmapCluster` is a name, in heightdata.con, not numbers in init.con) -> map_size guessed by heightmap resolution; `parse_terrain_con` regex never matches -> height_scale = 300 everywhere.
- Authoritative source: `heightdata.con` -> `heightmapcluster.setHeightmapSize` (asad_khal: 1024, not 4096) and primary `heightmap.setScale x/y/z` with height_scale = 65535*y (asad_khal: 163.84, not 300).
- Survey: 31/66 zipped maps have wrong map_size; true max heights range 25-700 m while metadata says 300 everywhere (only adak and operation_thunder accidentally correct).
- Ground-truth check (bilinear heightmap sample vs object elevation): asad_khal spawn mecbase_0_5 object 59.5 m -> 137.6 m current vs 50.0 m corrected. Residual 9-14 m remains; pixel-convention investigation assigned to the handed-off agent.
- Prior spike plots were scale-INSENSITIVE (sign and orientation checks only). Lesson: visual ground-truthing must include a scale-sensitive check (object elevation vs heightmap).
- Pre-existing impact beyond this change: the shipping calculator's elevation math consumes the same wrong metadata. Surfaced to user as a separate decision; NOT fixed under this change.
- Handoff brief written: `openspec/changes/add-opening-flow-simulator/handoff/handoff-ground-truth-fix-001.md` (tasks T1-T6, status OPEN).

### R3 - 2026-09-28 Phase A close-out and bookkeeping repair

User request (verbatim):

> what next steps can be taken on `opening-flow-simulator`? `terrain-travesability-model` are entirely completed (including adding the missing 15 client.zip).

Followed by (verbatim):

> Task 1.8 and bookkeeping then Phase B field pipeline. But, **do not commit**

State audit findings (tasks.md checkboxes were stale; nearly all Phase A work was done but unchecked):

- Ground-truth repair (R2 handoff) COMPLETED 2026-09-27: `processor/repair_map_metadata.py` repaired 66/66 metadata (map_size from `heightmapcluster.setHeightmapSize`, height_scale from primary `heightmap.setScale`); gamelayers and obstructions re-extracted. Evidence: `artifacts/implementation-ground-truth-001.md`.
- The 15 missing client.zip files were supplied under the `add-terrain-traversability-model` change; obstruction re-extraction now yields roads for all maps except `deagle5` (one non-finite mesh, logged and skipped by design). Verified: only deagle5 has zero roads in obstructions.json.
- Tasks 1.5/1.6 COMPLETE: `calculator/static/data/vehicle_speeds.json` (791 entries, per-entry `calibrated` flag and `estimate_method`; calibration failed so values are class defaults labeled uncalibrated, raw_forward preserved). Tests pass (`test_vehicle_speeds.py`).
- Task 1.7 COMPLETE: `processor/movement_params.json` with per-field provenance; historical baselines labeled "unverified for v1.9", candidates list from raw_game_data search.
- Task 1.8 COMPLETED this session: `processor/tests/test_gamelayer_extraction.py` (7 tests). Road/static-object fixtures intentionally NOT duplicated here; they live in `test_obstruction_extraction.py` (those parsers are in extract_obstructions.py). Writing the malformed-section test exposed a REAL BUG: `parse_gameplayobjects` crashed with ValueError on a non-numeric `absolutePosition`, killing the whole layer. Fixed at the root (per-object try/except around position parse). 11/11 parser tests pass (gamelayer + obstruction + mapinfo).
- tasks.md checkboxes for 1.1-1.8 marked done to match reality. Phase B/C/D remain unchecked and unstarted (`build_flow_fields.py`, `flow_overlay.js` absent).

Open risk carried into Phase B (explicitly parked, not resolved): spawn-elevation ground-truth residuals (median 9-24 m; Kunar 210 m) per `processor/verify_map_scale.py`. Phase B solver sources use spawn XY only, so this does not block; it must be resolved before spawn elevations are used as a strict acceptance gate (per implementation-ground-truth-001.md).

### R4 - 2026-09-28 Phase B implementation (solver, sampler, serializer)

Same user instruction as R3 ("Task 1.8 and bookkeeping then Phase B field pipeline. But, **do not commit**").

Decisions:
- Cost-grid reuse: design.md gained an "Implementation Deviations" section. Task 2.1's in-module cost-grid builder is superseded by the add-terrain-traversability-model change; `build_flow_fields.py` loads `terrain/<profile>/cost.bin` via `terrain_artifact.load_terrain_artifact` (infantry -> infantry, vehicles -> wheeled_vehicle). The traversability artifact contract already names this solver as its consumer, and its D5 matches flow D7 (water/buildings high-cost passable; only extreme slope blocks).
- Infantry field speed: sustained sprint/regen average from movement_params.json = (5*30 + 2.5*90)/120 = 3.125 m/s, provenance recorded per sidecar.
- Vehicle field speed: median of the team's spawner template speeds per layer; missing templates fall back to the found-average (design "Error Handling"), recorded in the sidecar.
- Serializer: 8-bit quantization with per-field whole-second quantum (255 = unreachable, cap 3600 s). A 4 km map field is 1 MB, inside the D6 budget, so the D6 resolution-halving fallback is NOT triggered; race_times.json carries exact floats, so the coarse quantum only affects band rendering, which thresholds at 60 s intervals anyway.

Implementation bugs found by tests (both fixed at root):
- `extract_gamelayers.parse_gameplayobjects` crashed with ValueError on a non-numeric absolutePosition, killing the whole layer (found by the new 1.8 malformed-section test). Fixed with a per-object try/except.
- `solve_field` stored arrivals as float32 while heap keys stayed float64; when float32 rounding stored a value BELOW its heap key, the stale-entry skip discarded the cell's best entry and propagation silently cut off (~9-cell boundary on flat grids). Fixed by keeping the working grid float64 and converting to float32 at return. Side effect: 6-test suite runtime dropped 53 s -> 2.6 s (the rounding had also caused re-relaxation churn).

Data gap found and fixed at root:
- `extract_vehicle_speeds.py` only accepted `vehicles/land/` and `vehicles/sea/`; ALL `vehicles/civilian/` templates (42 referenced: technicals, zastavas, car bombers) were dropped, so insurgent teams got no vehicle field at all (e.g. asad_khal gpm_cq_64 team1). Command vehicles (`*_acv_*`, 16 referenced) live in `objects_common_server.zip:common/command_post/`, also unparsed. Extractor now covers both; 791 -> 903 templates, referenced-matched 369 -> 431. Remaining 355 missing are air assets, deployables, rallypoints, bipods, and static spawns (out of scope for a ground-movement field) plus a handful of genuinely absent templates handled by the labeled fallback.

Verification:
- `python -m pytest processor/tests/test_flow_field.py` -> 11 passed (flat-frontier circle within 1 cell, ridge detour, water/building heavy-cost-never-blocked, unreachable sentinel, source nudge, quantization, sampling, team linkage, speed median/fallback).
- `python -m pytest processor/tests/test_gamelayer_extraction.py processor/tests/test_obstruction_extraction.py processor/tests/test_mapinfo.py` -> 11 passed.
- `python -m pytest processor/tests/test_vehicle_speeds.py` -> 4 passed (after extractor change).
- Smoke: `python processor/build_flow_fields.py asad_khal` -> 10 layers, 36 fields written; race_times plausible (team2 idfbase 0.2 s = own base; team1 hamasbase 26 s); team1 vehicles field now written (28 m/s jeep-class median).
- Full-corpus terrain artifact generation (`python processor/build_terrain_cost.py`) and full flow build: IN PROGRESS at time of writing.

### R5 - 2026-09-29 crosscheck audit against repo truth

User request (verbatim):

> Can you please orchestrate a crosscheck of `add-opening-flow-simulator` against the actual repo truth? Use multiple explorer subagents to perform it

Method: three parallel Explorer subagents with overlapping lanes. Reports: `artifacts/crosscheck-code-001.md` (code/tests), `artifacts/crosscheck-data-001.md` (data artifacts), `artifacts/crosscheck-docs-001.md` (docs/claims). No project files modified by the audit.

Consensus CONFIRMED (all three lanes agree, tool evidence cited in reports):
- Phase A fully implemented; all claimed files exist; full processor suite 93 passed; frontend harness passes (exit 0).
- Phase B solver/sampler/serializer implemented as designed; 11 solver tests pass; smoke reproduces "10 layers, 36 fields written" byte-identical inventory.
- D5 transform, D7 semantics (water/buildings passable multipliers, only extreme slope blocks, -1.0 sentinel), D9 scenario field, profile mapping (infantry->infantry, vehicles->wheeled_vehicle), and the cost-grid ownership deviation all confirmed in code.
- vehicle_speeds.json: 903 entries, all calibrated:false with honest failed-calibration provenance. movement_params.json: per-field provenance, baselines labeled unverified.
- Metadata repair confirmed (asad_khal map_size 1024, height_scale 163.8375, sea_level_m 49 present; prior keys retained).
- Phase C/D genuinely unstarted (no flow_overlay.js, no Flow toggle in index.html, no AGENTS.md flow subsection).
- the_falklands exclusion consistent everywhere.

Discrepancies found (ordered by severity):
1. R4 "IN PROGRESS" status is now half-stale: terrain artifacts are COMPLETE for all 85 heightmap maps (170 cost.bin, timestamps after the R4 note), but flow fields exist for asad_khal ONLY (36 fields). Full-corpus flow build was never run. tasks.md 2.1 first bullet is a stale checkbox (work done, unchecked).
2. R4/task-record stale values: the gamelayer spot-check coordinate (2298.09, 2396.116) was pre-repair; current truth is (762.09, 860.116) with the same elevation 47.011 (consistent with map_size 1024). The "team1 hamasbase 26 s" race-time claim is stale; current gpm_cq_64 value is team1 2.0 s (team2 idfbase 0.2 s confirmed). Implementation is correct; the record was not.
3. gamelayers.json exists for 66 maps; 85 map dirs exist; the 19 missing match the documented "19 processed maps lack local server.zip" design risk. obstructions.json exists for 84 maps (andromeda missing); 18 maps have obstructions but no gamelayers - explainable by corpus differences but worth a note.
4. Handoff `handoff/handoff-ground-truth-fix-001.md` still says Ready/OPEN though R3 recorded the repair complete; task record also referenced a wrong filename (handoff-ground-truth-001.md).
5. proposal.md stale wording: "road polylines + widths" and "build_flow_fields.py builds a 3-tier cost grid" predate the mesh-geometry reality and the traversability ownership deviation (both correctly documented in design.md only).
6. Environment note: bare `python -m pytest` hangs in this environment (third-party langsmith plugin autoload, KeyboardInterrupt during plugin import). All results above obtained with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. Repo tests themselves are clean.
7. Repo-size flag: terrain artifact tree is ~1.54 GiB across 85 maps (per-field budget met; corpus total is a shipping/LFS decision not yet made).
8. AGENTS.md is modified in the working tree but the diff is a broad rewrite, NOT the Phase D flow subsection - must not be counted as Phase D progress.

Corrections applied to this record by R5: items 1-2 above supersede the corresponding R4 statements. No other files changed by this audit.

### R6 - 2026-09-29 bookkeeping patch (go received for plan)

User instruction (verbatim):

> Plan looks good. Please proceed with implementation. I've switched your environtment from Planning (previous) to Orchestration (current). Goodluck and godspeed!

Plan executed: `artifacts/plan-bookkeeping-and-flow-build-001.md` (research: `plan-research-bookkeeping-001.md`, `plan-research-flow-build-001.md`).

Bookkeeping patch applied:
- tasks.md 2.1 first bullet checked; parenthetical now records 85 maps / 170 cost.bin files.
- handoff-ground-truth-fix-001.md: Handoff Status Ready -> Completed; Lifecycle OPEN -> CLOSED.
- proposal.md items 3 and 5: polylines+widths wording replaced with mesh-reference/decoded-triangle reality; cost-grid ownership moved to build_terrain_cost.py.
- specs/map-processor/spec.md: Field Pipeline Script requirement now says build_flow_fields.py LOADS a validated terrain cost grid; ownership sentence added.
- design.md: stale illustrative coordinate (pre-repair 4096 m space) replaced with current gpm_cq/32 idfbase (762.09, 860.116); Error Handling gained the missing-obstructions line (andromeda; terrain stage warns and continues without obstruction-derived costs - verified in build_terrain_cost.py lines 584-592).
- Historical R4 text intentionally not edited (append-only log); R5 supersession stands.

Additional finding recorded (no doc change): the D6 resolution-halving fallback was never implemented in the serializer; the ~1 MB per-field budget is met by 8-bit quantization alone (1024x1024 u1 = 1 MiB), so the fallback condition never triggers. Design D6 wording is a contingency, not a promise.

### R7 - 2026-09-29 parallel full-corpus flow build (COMPLETE)

User instructions (verbatim):

> I guess the build dying suddenly is a universe sign that the build need to be redone with multi threaded? either way its okay. Yes, please make the required modification and redo the build. But, lets not go for the entire map list all at once. Lets start slowly and record benchmark from a map or two first (single vs multi -threaded), before comitting fully to the entire map list build. Also, i think its wise to research and explore *what* and *how* the multithreading should be implemented first via concrete web or official source.

> Yep, please proceed with the full build with 4 workers

First full-build attempt (sequential, started 06:25) died silently at ~06:44 mid-bamyan (6 maps complete, bamyan partial 9/33); cause unknown; the PowerShell `*>` log capture buffered everything and lost it. Lesson applied: later runs use `python -u` and per-run logs.

Research (before implementation, per user instruction): `artifacts/research-parallelism-official-001.md` (docs.python.org: GIL pins threads to one core for CPU-bound Python; ProcessPoolExecutor is the documented mechanism; Windows spawn needs the __main__ guard, already present) and `artifacts/research-parallelism-patterns-001.md` (map-level granularity, submit+as_completed error collection, no grids across IPC, benchmark methodology).

Implementation: `processor/build_flow_fields.py` gained `--workers N` (default 1 = sequential, unchanged). Parallel path: one ProcessPoolExecutor, one top-level picklable task per map (process_map), per-future exception capture, nonzero exit on any failure. `OUT` gained a PR_FLOW_OUT env override so tests can fixture the tree (inherited by spawned workers). No new dependencies.

Verification:
- New regression tests in `processor/tests/test_flow_field.py`: parallel-vs-sequential byte-identity on a synthetic 2-map fixture (real spawned workers), --workers validation. Suite: 13/13 pass.
- Benchmark (black_gold + kashan_desert, 120 fields, 1024x1024): serial 755.2 s vs --workers 2 322.9 s = 2.34x measured (above the 2x two-map scheduling ceiling because serial ran cold-first; defensible claim ~2x at 2 workers). Logs: artifacts/bench-big-w1.log, bench-big-w2.log.
- Correctness: --workers 2 outputs for asad_khal + adak are SHA-256 byte-identical to the serial baseline (154/154 files, artifacts/bench-baseline-hashes.json).
- Full build: `python -u processor/build_flow_fields.py --workers 4 <58 remaining maps>` -> "Summary: 58/58 maps processed.", exit 0, 1696.9 s (28.3 min). Log: artifacts/flow-build-w4.log; map list: artifacts/flow-build-remaining-maps.txt.
- Corpus verification (`artifacts/verify_flow_corpus.py`): 66 flow map dirs; 2046 bins + 2046 sidecars (exactly the pre-build prediction); bin bytes 1,066,696,704 (exactly predicted); all sidecars schema-checked; bin/sidecar pairing clean; 555 race_times files.
- The single missing race_times (operation_marlin gpm_skirmish_16) is by design: that layer has zero infantry spawn points and only fixed_supply_crate/rallypoint spawners, so no fields exist to sample.
- Race-time spot checks plausible on asad_khal/adak/muttrah_city_2 (own bases 0.2-5.4 s, cross-map tens-to-hundreds of seconds, no negatives/NaN).
- Regression: full processor suite 95 passed (PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; bare pytest hangs on the langsmith plugin in this environment); `node calculator/tests/run-tests.js` all pass.

Phase B is now complete except task 2.2 (human/QA eyeball of cost-grid overlays, owned by the traversability change's QA outputs). Phase C (browser overlay) and Phase D (docs) remain unstarted. Nothing committed per standing instruction.

### R8 - 2026-09-29 Phase C: C0-C2 complete, browser smoke done (IN PROGRESS)

User instruction (verbatim):

> Plan looks good. Please proceed with implementation. I've switched your environtment from Planning (previous) to Orchestration (current). Dont forget to use the integrated browser to test the webapp. Make sure to orchestrate this implementation and delegate tasks to subagents (offload more task, as much as possible, to assistant if possible).

Plan executed: `artifacts/plan-phase-c-001.md` (research: research-phase-c-{frontend,data,techniques,veteran}-001.md). User decisions on the four alignment questions: generalize the existing /maps route to nested paths; particles last + off by default; race times fixed at source + regenerated from bins; build-android.bat fixed with terrain/ and flow/ excluded from the APK copy and the WebView smoke deferred.

Environment events:
- Mid-implementation the environment froze (likely a subagent starting the Flask server in a blocking sync terminal) and was restarted by the user. Lesson applied: servers only via async terminals.
- After the restart the Assistant and Review Orchestrator agents are no longer in the agent roster (only Designer, Explorer, Technical Planner, Veteran Engineer remain). Implementation continued via direct orchestrator implementation (the workflow default); Explorer reserved for the final independent review pass.

C0 (unblockers; two Assistant subagents pre-restart, orchestrator-verified after):
- calculator/server.py: `/maps/<map_name>/<path:filename>` with per-segment secure_filename sanitization; the /processed_maps alias inherits it. Nested bins/sidecars/race_times serve; traversal rejected; server tests added (103 Python tests pass).
- processor/build_flow_fields.py: race times now sampled from the QUANTIZED grid (sample_quantized_arrival, min over classes per team) plus a `--race-times-only` regeneration mode. All 555 race_times.json regenerated from shipped bins in ~10 s; every sampled value verified a multiple of at least one of that team's field quanta (0 violations); layers with no fields still get no race_times.json (operation_marlin gpm_skirmish_16 preserved by design).
- design.md/proposal.md wording synced to the route generalization.

C1 (core + shell):
- calculator/static/js/flow/flow_core.js (Assistant, pre-freeze): DOM-less decodeField/fieldSeconds/renderBands/formatRaceTime/buildRaceReadout/flowUrls/probeFlow/loadLayerFields. Single-pass Uint8->RGBA with band alpha LUTs; contested = both finite and |a-b| <= delta; sentinel masked before thresholding. Extended (additive) to return sidecars for the provenance tooltip.
- calculator/static/js/flow/flow_overlay.js (orchestrator): Leaflet controller - custom L.Layer positioning a live canvas in the overlay pane (vendored Leaflet 1.9.4 imageOverlay accepts only IMG elements; confirmed in the minified source), rAF-coalesced redraws, per-map+layer Promise cache, mapLoadToken-style stale guards, bounds derived from the sidecar grid (row 0 = north; no heightmap-style row flip).

C2 (UI):
- index.html: Opening Flow checkbox + options block (layer dropdown default gpm_cq_64 with first-available fallback, team Both/1/2, class Infantry/Vehicles, slider 0-300 s with m:ss label, persistent "From initial deployment" label + provenance tooltip, race-time readout, notice area). Block hidden when the map has no gamelayers.json.
- app.js: import + state.flow controller, detach before map teardown, attachMap after init, initFlowControls in setupEventListeners.

Browser smoke (integrated browser + Flask on :8080, Playwright-driven):
- asad_khal gpm_cq_64: all 4 fields load; 58,990/65,536 px painted at t=300 s vs 7,754 at t=60 s; bands render team-colored with the contested band between the main bases (screenshot-verified; orientation correct: IDF NW, Hamas SE).
- Race readout matches regenerated race_times.json (hamasbase T1 0:02 / T2 1:33 etc.); provenance tooltip shows speed + provenance; vehicles tooltip shows the uncalibrated 28 m/s labeling.
- Team/class/layer switching repaints correctly; single-team renders verified via a putImageData interceptor (team2-only infantry t=60 paints exactly 4,705 px, matching a manual in-page renderBands call).
- andromeda (no gamelayers.json): controls hidden, no overlay, zero leftover canvases; switching back restores controls with a clean off state.
- operation_marlin gpm_skirmish_16 (zero-spawn layer): "Flow is not computed for this layer." notice, option disabled, overlay removed, "No race data" readout.
- ANOMALY (test harness, not app): getImageData readbacks intermittently returned all-zeros in the occluded integrated-browser page while the putImageData interceptor proved correct pixels were painted and screenshots showed correct rendering. Treated as an integrated-browser canvas readback artifact; app correctness established via interceptor logs + screenshots instead.
- Zero page errors and zero console errors attributable to the app (expected 404s only for absent optional per-field files, by design).

Remaining: C3 particles (off by default), C4 (build-android.bat rewrite + exclusions, tasks.md wrap-up, full verification), final independent review, then Phase D docs. Nothing committed per standing instruction.

R8 addendum (2026-09-29, same session): C3 particle code is now WRITTEN but NOT yet browser-verified. flow_overlay.js gained the particle system (~150 particles, central-difference negative gradient with sentinel/zero guards, cosmetic 60 m/s data-space speed plus jitter, destination-out trail fade, respawn on age/bounds/sentinel, viewport-sized canvas in the overlay pane realigned per frame, cleared on movestart, hard stop on overlay hide / map switch / visibilitychange-hidden) and index.html gained the off-by-default "Flow particles (visual)" checkbox. Syntax check and frontend suite pass. The particle browser smoke did NOT run: the Flask server exited (code 1) before the test; restart `python -m calculator.server` (async terminal) and smoke particles on/off, map switch, and tab-hide when resuming. tasks.md 3.3 particle checkbox stays unchecked until that smoke passes.

### R9 - 2026-09-30 browser and terrain verification

User instruction (verbatim):

> Plan looks good. Please proceed with implementation. I've switched your environtment from Planning (previous) to Orchestration (current). Goodluck and godspeed!

The approved verification plan was executed without changing the Flow or terrain implementation.

Browser evidence: `artifacts/browser-verification-002.md`.

- Confirmed `calculator/tests/test_flow_overlay.js` exists; the prior explorer discrepancy was a read failure, not a missing file.
- Started `python -m calculator.server` asynchronously on local port 8080.
- On asad_khal gpm_cq_64, Flow loaded field data and race times; particles were off by default; enabling created a second viewport canvas in the Leaflet overlay pane; disabling removed it.
- Switching with particles enabled to andromeda removed all canvases and hid Flow controls.
- Used two real browser pages and `bringToFront()` to observe document.hidden/visibilityState transitions: hidden/hidden while unfocused, visible/visible after returning. Particle page retained its active canvas state on resume.
- Browser smoke showed no application page exceptions or external requests. Expected local optional-data 404s and the existing andromeda contour warning were observed.

Terrain evidence: `artifacts/terrain-qa-002.md`.

- Ran `python processor/render_terrain_qa.py asad_khal adak muttrah_city_2`.
- Rendered overlays were visually inspected. Coverage was complete; source spacing was 2 m for asad_khal and muttrah_city_2, 4 m for adak. No obvious major road was visibly erased by a continuous blocked strip in the overview; no independently provable correction was found, so no patch was created.
- The report records that minimap/road-overlay QA cannot prove complete game collision truth. Per-map patch consumption is not implemented and remains a separate behavior change.

Verification results:

- `node calculator/tests/run-tests.js` -> PASS: ballistics, coordinates, heightmap, integration, and Flow overlay tests all passed.
- `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py calculator/tests/test_server.py` -> FAIL: 92 passed, 5 failed. All five failures are in terrain-cost synthetic fixtures and fail at `build_terrain_cost.py` with `KeyError: 'roughness_status'`; no source fix was attempted in this verification-only scope.
- The unfiltered processor command also collected the known unsafe `test_update_manifest.py` and failed during collection because `raw_map_data/manifest.json` is absent; this is documented in AGENTS.md and was not treated as a feature result.

Bookkeeping: tasks 2.2 and 3.3 particle verification are marked complete with the evidence and limitations above. Android, documentation, full wrap-up, and AC-1 through AC-8 confirmation remain open. No commit was made.
