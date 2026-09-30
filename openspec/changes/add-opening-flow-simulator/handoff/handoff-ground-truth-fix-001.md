# Handoff Brief: fix/map-ground-truth-obstructions

- **Brief ID:** handoff-ground-truth-fix-001
- **Source change:** `add-opening-flow-simulator`
- **Created:** 2026-09-27
- **Handoff Status:** Completed
- **Mode:** Task-level (ground-truth repair + obstruction extraction completion)
- **Suggested branch:** `fix/map-ground-truth-obstructions`
- **Snapshot note:** This brief describes repo state as of 2026-09-27. Follow the Reconciliation Rule before editing.

---

## Repo Context

Project Reality: BF2 mortar calculator. Flask serves static files; all ballistics math runs in the browser; per-map data ships as pre-processed JSON/PNG under `processed_maps/<map>/`. Maintainer-side Python pipeline lives in `processor/`. Fully offline; no CDN; no new runtime dependencies (Python stdlib + numpy; PIL/matplotlib allowed for debug images; browser = vanilla ES modules + vendored Leaflet/pako).

Truth precedence when documents disagree: `PRD.md` (if present) > approved specs in `openspec/changes/add-opening-flow-simulator/specs/` > `design.md` > `tasks.md`. For BF2 file formats, the game files themselves are ground truth — verify against them, never assume.

Safety rules (hard):
- NEVER modify anything under `raw_map_data/` or `raw_game_data/` (read-only extraction inputs).
- NEVER commit or ship PR asset zips. No git commits unless the user explicitly asks.
- ASCII-only in all files and outputs. No emojis, no Unicode symbols.
- `the_falklands` is excluded from all extraction and UI lists.
- Do not create or edit files outside the Assigned Tasks below. In particular do NOT touch: `calculator/` frontend code, `www/`, `android/`, `processor/extract_vehicle_speeds.py`, `processor/movement_params.json`, `calculator/static/data/vehicle_speeds.json` (sibling workstreams, already delivered).
- Existing test commands: `python -m pytest processor/tests/` and `node calculator/tests/run-tests.js`. Both must stay green.

## Current State

The OpenSpec change `add-opening-flow-simulator` adds a precomputed "opening flow" overlay: maintainer-side Python builds per-team arrival-time fields from extracted game data; the browser only thresholds and renders. Phase A (extraction) is partially complete:

DONE and verified (do not redo):
- `processor/extract_gamelayers.py` — parses `gamemodes/<mode>/<size>/gameplayobjects.con` from each `raw_map_data/<map>/server.zip`; writes `processed_maps/<map>/gamelayers.json` (control points, spawn points, vehicle spawners) and adds `sea_level_m` to `metadata.json`. Ran 66/66 maps.
- `processor/bf2_road_mesh.py` — decoder for BF2 compiled road meshes from `client.zip` (52-byte header with world origin + vertex count, 32-byte vertices `[position xyz, UV0, UV1, alpha]`, uint16 triangle indices). Verified 62/62 segments on asad_khal ONLY. Format doc: `openspec/changes/add-opening-flow-simulator/artifacts/road-mesh-format.md`.
- `processor/extract_obstructions.py` — exists and ran 66/66 maps, but its OUTPUT IS WRONG (see below). `processor/extract_vehicle_speeds.py`, `calculator/static/data/vehicle_speeds.json`, `processor/movement_params.json` — delivered by sibling workstreams; do not touch.
- Coordinate transform SIGN confirmed: BF2 `absolutePosition X/Y/Z` is center-origin, +X east, +Z north, Y = elevation meters. Repo coords (top-left origin, y south): `x_repo = X + map_size/2`, `y_repo = map_size/2 - Z`.

BROKEN (the reason for this handoff):
- `processed_maps/<map>/metadata.json` carries wrong `map_size` on 31 of 66 zipped maps and wrong `height_scale` on nearly ALL maps (see Root Cause). Every downstream artifact that used those values is suspect: all `gamelayers.json` positions on mis-sized maps, all `obstructions.json`, and any elevation read via the wrong `height_scale`.
- `processor/bf2_road_mesh.py` rejects many non-asad_khal mesh variants (930 logged skip events across the corpus) because their reserved header fields are nonzero. Road coverage outside asad_khal is incomplete.

## Root Cause (verified, with evidence)

`processor/process_one_map.py` (pre-existing pipeline) derives two critical values with broken parsing:

1. `parse_init_con` regexes `init.con` for `heightmapCluster.create <num> <num>`. The real line is `heightmapcluster.create HeighmapCluster` (a NAME) in `heightdata.con`. The regex never matches, so a fallback guesses `2048 if heightmap.shape[0]==1025 else 4096`.
2. `parse_terrain_con` regexes `terrain.con` for `HeightmapCluster.setHeightScale`. That line does not exist there; the true vertical scale is the Y component of `heightmap.setScale x/y/z` in `heightdata.con` (meters per raw uint16 unit). All processed maps got the fallback `300`.

Authoritative source, per map, from `raw_map_data/<map>/server.zip` -> `heightdata.con`:
- `heightmapcluster.setHeightmapSize <N>` -> true map world size in meters (asad_khal: 1024).
- Primary block (`rem --- primary ---` ... first `heightmap.setScale X/Y/Z` after it): X = horizontal meters per heightmap pixel, Y = vertical meters per raw unit. True `height_scale` (= max elevation) = `65535 * Y` (asad_khal: 0.0025 -> 163.84).
- `heightmapcluster.setSeaWaterLevel <m>` (already extracted correctly).

Evidence (full survey already run; mismatch list is authoritative):
- 31 maps with `map_size` mismatch: adak, asad_khal, ascheberg, assault_on_mestia, bamyan, battle_of_kerch, belyaevo, black_gold, burning_sands, deagle5, fallujah_west, fields_of_kassel, gaza_2, grostok, hades_peak, hill_488, icebreaker, kashan_desert, khamisiyah, korbach_offensive, korengal, kunar_province, masirah, merville, operation_bobcat, operation_soul_rebel, operation_thunder, pavlovsk_bay, reichswald, road_to_damascus, saaremaa.
- True max heights (`65535*Y`) range 25-700 m across the corpus (e.g. route 25, burning_sands 60, kunar_province 700); metadata says 300 everywhere. Only adak and operation_thunder are accidentally correct.
- Ground-truth elevation check on asad_khal (bilinear heightmap sample at object positions vs the object's own BF2 elevation): spawn `mecbase_0_5` object elev 59.5 m -> current pipeline (size 4096, hs 300) reads 137.6 m; corrected (size 1024, hs 163.84) reads 50.0 m. CP `idfbase` object elev 47.0 -> 115.0 current vs 61.1 corrected. Corrected values are close but leave 9-14 m residuals with opposite signs: you MUST finish nailing the exact pixel convention (see T2 acceptance).

Why prior visual checks missed it: the spike plots verified transform SIGN (north/south naming) and mask ORIENTATION (coastline alignment), both of which are scale-insensitive near the map center. Only object-elevation-vs-heightmap sampling is scale-sensitive. Use it as the regression gate.

## Assigned Tasks

### T1: Authoritative map-info parser
Create `processor/bf2_mapinfo.py`: given a map's `server.zip` path, parse `heightdata.con` and return `{map_size, height_scale, heightmap_resolution, sea_level_m}` where `height_scale = 65535 * primary_setScale_Y`. Handle case-insensitivity and missing fields (log + return None per field). Pure stdlib + re.

### T2: Ground-truth verification harness
Create `processor/tests/test_map_ground_truth.py` + a runnable script form (`processor/verify_map_scale.py`) that, per map: loads 5+ ground-hugging objects (prefer SpawnPoints; they sit on terrain) from that map's `gameplayobjects.con` (gpm_cq/32 preferred, else any layer), transforms with the T1 values, bilinear-samples the repo heightmap (`processed_maps/<map>/heightmap.json.gz`), and reports elevation residuals. Investigate until residuals are small and sign-consistent explanations exist: candidate conventions to test are `mpp = size/(res-1)` vs `size/res`, half-pixel center offsets, and whether the primary heightmap tile is exactly world-centered. Acceptance: on asad_khal, adak, fools_road, muttrah_city_2, kunar_province — median absolute residual <= 3 m, and the chosen convention is documented in `bf2_mapinfo.py` docstring. If a residual floor persists for a documented reason (e.g. spawn hover offset), state the floor and evidence, do not silently accept it.

### T3: Repair metadata.json for all zipped maps
For every `raw_map_data/<map>/server.zip` (skip `the_falklands`): rewrite `processed_maps/<map>/metadata.json` `map_size` and `height_scale` from T1, preserving all other keys, adding `heightmap_size_source: "heightdata.con setHeightmapSize / setScale"` for provenance. Maps without zips (19) keep old values; list them in the completion report as unverifiable. Re-run `python processor/extract_gamelayers.py` afterwards (it reads `map_size` from metadata) and re-verify the asad_khal CP spot-check: `gpm_cq/32` idfbase -> x = 512+250.09 = 762.09, y = 512+348.116 = 860.116, elevation_m = 47.011.

### T4: Road mesh decoder coverage
Extend `processor/bf2_road_mesh.py` to handle the rejected variants (930 skip events; reserved header fields nonzero on non-asad_khal maps). Inspect 3-5 failing meshes from different maps, generalize the header parse, and validate per map by plotting road vertices over that map's minimap for 2 maps beyond asad_khal (pick one 1024m and one 4096m map). Segments that still fail: logged and skipped, never fatal. Acceptance: rejected-segment count drops below 5% of total segments corpus-wide, with the remainder listed by map and reason in the completion report.

### T5: Re-run obstruction extraction + QA
Re-run `python processor/extract_obstructions.py` over all maps. Regenerate the QA overlay `openspec/changes/add-opening-flow-simulator/artifacts/qa_obstructions_asad_khal.png` (roads, classified statics, vegetation over the minimap) plus one more map. Acceptance: features span the full minimap (not a central cluster); roads trace the visible road network; asad_khal counts remain ~62 roads / ~3232 statics / ~1339 vegetation; per-map error summary included.

### T6: Regression wiring
`python -m pytest processor/tests/` passes (existing `test_gamelayer_extraction.py` if present, `test_obstruction_extraction.py`, `test_vehicle_speeds.py`, plus your new `test_map_ground_truth.py`). `node calculator/tests/run-tests.js` passes unchanged (you are not modifying the calculator; this is a no-damage check).

## Relevant Files

- `processor/process_one_map.py` — contains the broken `parse_init_con`/`parse_terrain_con` fallbacks (root cause; read to understand, fix only if a task says so — the metadata repair in T3 is the fix path; leave the script's fallback behavior documented if untouched).
- `processor/extract_gamelayers.py` — transform + gamelayers extractor; module docstring records the confirmed transform; re-run in T3.
- `processor/bf2_road_mesh.py` + `openspec/changes/add-opening-flow-simulator/artifacts/road-mesh-format.md` — road mesh decoder and format doc (T4).
- `processor/extract_obstructions.py` — obstruction extractor; correct logic, poisoned inputs; re-run in T5 after T3.
- `openspec/changes/add-opening-flow-simulator/{proposal,design,tasks}.md` and `specs/*/spec.md` — the approved change. `artifacts/task-record.md` (revision R2) — full evidence chain.
- `openspec/changes/add-opening-flow-simulator/artifacts/subagent-recovery/recovery-obstructions-001.md` — prior audit of the obstruction workstream.
- Format cheat-sheet (verified): `gameplayobjects.con` = `ObjectTemplate.create <Class> <name>` blocks + `Object.create <name>` instance blocks with `Object.absolutePosition X/Y/Z`; `compiledroads.con` = per-segment `object.create <name>` / `object.geometry.loadMesh Levels\<map>\Roads\<file>` / `object.absoluteposition X/Y/Z` with meshes in client.zip `roads/`; `overgrowth/overgrowthcollision.con` = `Object.create <template>` + `Object.absoluteTransformation [..][..][..][X/Y/Z/1]` (translation = 4th bracket group); statics in `staticobjects.con` (NEVER parse `staticobjects_old.con` — double counting).

## Reconciliation Rule

This brief is a snapshot. Your local repo is the truth. Before editing, verify the files listed above exist and roughly match their descriptions; if they have drifted (e.g. tasks already done, files moved), trust the local state, note the drift in your completion report, and continue with the remaining work.

## Before You Start

Reply with a pre-work acknowledgement: confirm you read this brief, `artifacts/task-record.md` (R2), and the recovery report; restate the root cause in two sentences; list the six task IDs you will execute. Only then begin T1.

## When You're Done

1. Scope: only the files created/modified by T1-T6. No drive-by edits.
2. Write `openspec/changes/add-opening-flow-simulator/artifacts/implementation-ground-truth-001.md`: per-task evidence (exact commands + outputs), the final residual table for the 5 verification maps, the decoder coverage numbers before/after, the list of unverifiable no-zip maps, and anything you did NOT verify.
3. Verification matrix (fill with PASS/FAIL + one-line evidence each):

| Check | Command |
|---|---|
| Ground truth | `python processor/verify_map_scale.py` |
| Unit tests | `python -m pytest processor/tests/` |
| Calculator no-damage | `node calculator/tests/run-tests.js` |
| Gamelayers spot-check | idfbase x/y/elevation assertion from T3 |
| QA overlays | two PNGs eyeballed, features span full map |

4. Do not update `tasks.md` checkboxes or the task record; the orchestrator does that after review.

## Constraints

- ASCII-only; 4-space Python; match `extract_gamelayers.py` style; stdlib + numpy (PIL/matplotlib for debug PNGs only).
- No subagent dispatches. Work directly.
- Keep terminal commands short and simple; prefer writing a script file over long one-liners.
- If a map fails repeatedly, log, skip, continue; report at the end. Never let one map kill the run.

## Handoff Lifecycle

- Lifecycle status: CLOSED
- Assigned task IDs: T1, T2, T3, T4, T5, T6
