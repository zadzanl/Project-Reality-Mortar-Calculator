# worklog - add-opening-flow-simulator

## Latest resume state

**Updated:** 2026-10-01
**Session status:** IN PROGRESS
**Change state:** in-progress
**Implementation authorized:** yes - constrained R10 Phase 0 through Phase 4
**Active task:** R10 Phase 3/4 browser contract and QA evidence review

**Resume from:** `openspec/changes/add-opening-flow-simulator/artifacts/qa-and-tests/continue-implementation-plan-001.md`, Phase 2 after baseline review
**Next action:** Review the constrained browser patch and decide whether to authorize a fixture-serving QA round; do not regenerate or publish the full corpus
**Blockers:** Production v2 flow data is not published, so integrated browser rendering of a real flow overlay remains unverified. Helicopter, Android, corpus publication, commits, and parent completion remain excluded.
**Last verification:** frontend harness passed with synthetic v2 manifest coverage; integrated browser loaded a map and switched tabs; static diagnostics and `git diff --check` passed. Details: `artifacts/qa-and-tests/phase-3-4-evidence-001.md`.

## Technical trace

- [review] R15 corrected workspace review returned NEEDS_REVISION; repaired B-07/B-08/B-09 in two JS files. Existing Node harness, 20 focused processor tests, diff check and diagnostics passed. Fresh port-8082 Adak browser verified Flow-off tab round-trip. Full matrix remains open; see implementation-review-revision-002.md.
- [resume] 2026-10-01 Continued from corrected review R-corrected-001; preserved all existing dirty work and made no reset, stash, commit, generated-data, raw-input, Android, or corpus-publication changes.
- [edit] 2026-10-01 Applied constrained A1-A5 review repairs: restored Mortar-only Show Grid, retained Leaflet mortar layer membership while hiding/disabling Flow-owned layers, mapped class availability statuses to readable reasons/title/status UI, separated arrival and delta time formatting, skipped invalid v2 CP coordinates, corrected the ten-minute quantization comment, and updated reduced-motion wording.
- [test-pass] 2026-10-01 `node calculator/tests/run-tests.js` -> All tests passed; `python -m pytest processor/tests/test_flow_field.py -q` -> 20 passed; `git diff --check` -> no output.
- [review-limit] 2026-10-01 Fresh browser AC-16/AC-17 verification was not run during this resume; no live browser, Android, corpus, or parent-completion claim is recorded.

- [edit] 2026-10-01 Added the missing `re` import required by `build_flow_fields.publish_v2_generation`; this was the only product failure in the fresh baseline.
- [test-fail] 2026-10-01 Before the fix, focused and broader safe pytest both failed at `publish_v2_generation` with `NameError: name 're' is not defined`; frontend tests passed.
- [decision] 2026-10-01 Preserved the existing dirty worktree and historical task claims; did not reset, stash, regenerate, publish, commit, or edit raw inputs.
- [discovery] 2026-10-01 OpenSpec reports 77/88 historical tasks complete and five constrained R10 follow-up tasks pending; Phase 0/1 evidence is tracked separately from those feature tasks.
- [test-pass] 2026-10-01 Frontend harness passed; focused processor suite passed 52 tests; safe broader processor/server suite passed 102 tests; diff check passed after the import fix.
- [edit] 2026-10-01 Integrated the temporary v2 processor path: positive selected-team sources, class/speed grouping, class-keyed races, confirmed-water boats, and staged immutable publication.
- [review] 2026-10-01 Local review found publication validation occurred after pointer activation; moved validation before activation and added a simulated pointer-replacement failure regression.
- [test-pass] 2026-10-01 Focused processor tests passed 26; safe broader processor tests passed 98; frontend harness passed; diff check passed. Evidence: `artifacts/qa-and-tests/phase-2-evidence-001.md`.
- [review-limit] 2026-10-01 Review Orchestrator dispatch failed with provider HTTP 402 out-of-credits; local review was recorded instead.
- [edit] 2026-10-01 Added browser v2 manifest/generation validation, class-specific loading, class-aware cache invalidation, and v2 class selector options; legacy vehicles loading remains an explicit fallback.
- [test-pass] 2026-10-01 Added synthetic v2 loader and identity-mismatch regressions; `node calculator/tests/run-tests.js` passed all suites, static diagnostics found no errors, and `git diff --check` passed.
- [qa] 2026-10-01 Integrated browser loaded the local app, loaded `test_bootcamp`, created the Leaflet map, and completed Mortar/Opening Flow tab switching. Flow controls stayed hidden because no production v2 manifest is published; this was expected and recorded as a verification ceiling.

## Vehicle classes and spawn sources continuation

- [audit] 2026-10-02 Read-only audits found 7,206 control points and 30,772 vehicle spawners across 84 extracted maps; 1,435 control points have derived `main_base=true`. Position/layer data exists for 30,748 spawners, but the prior schema lacked raw marker provenance and rule version. Reports: `artifacts/research/continuation-source-gate-001.md` and `artifacts/research/continuation-pipeline-001.md`.
- [edit] 2026-10-02 Added `unable_to_change_team_raw`, `team_ownership`, and `main_base_rule_version` to extracted control points, preserving normalized fields and backward compatibility.
- [test-pass] 2026-10-02 Focused processor checks passed 37 tests; safe broader processor suite passed 102 tests; Node frontend harness passed; modified-file diagnostics reported no errors.
- [failure] 2026-10-02 Re-running Adak after gamelayer regeneration initially collided with the immutable catalog-only build id (`v2-adak-1abbd7e784db`). No files were overwritten.
- [edit] 2026-10-02 Made v2 build identity include catalog, movement parameters, map/layer identity, and extracted layer source data; identical valid generations now safely validate/repoint without overwrite, while conflicting content still fails.
- [test-pass] 2026-10-02 `python -m pytest processor/tests/test_flow_field.py -q` passed 24 tests; Adak rerun printed `Summary: 1/1 maps processed.`; scoped diff check passed. Published Adak `gpm_cq_64` exposes six-class availability and `main_base_v1` extraction provenance.
- [next] Full supported-map v2 regeneration remains pending. Retention policy, generated coverage report, browser live QA, Android sync, Review Orchestrator verdict, and final acceptance claims remain open.
- [generation] 2026-10-02 Four-worker corpus build initially completed 76/84 maps; eight Windows staging renames failed with `PermissionError`. Target and staging paths were clean after the run. Retrying only those eight maps with four workers completed `Summary: 8/8 maps processed.`
- [audit] 2026-10-02 Active-manifest audit completed: 84/84 maps, 737/737 layers, zero malformed class statuses; status counts and source counts are in `artifacts/qa-and-tests/full-corpus-coverage-001.json`. It found 372 synthetic boat source records, 12,936 verified source records, 946 retained legacy `vehicles.bin` files, and two stale unreferenced payload directories.
- [cleanup] 2026-10-02 Removed only the two unreferenced stale `.payload` staging directories. Legacy pooled files were retained as compatibility artifacts; no retention deletion was performed.
- [edit] 2026-10-02 R17 recovery: removed the unintended water/bank veto on decoded candidate decks; retained unknown diagnostics and verified-only exclusion; degenerate-only geometry grants no mask.
- [test-pass] 2026-10-02 Focused extraction/terrain/flow suite passed 74 tests. Isolated Carentan/Tad Sae repeat builds matched 19 generated files per map; independent clipping matched 116/23 candidate cells; 367 protected files retained hashes. Evidence and limits: `artifacts/bridge-representative-validation-001.md`. No production regeneration or metadata repair in this recovery.
- [edit] 2026-10-02 R17 bounded real-Flow worker: loader already preserves bridge provenance; fixed missing terrain inputs in v2 generation identity and bumped solver version to `v2-bridge-4`. Added disk-loaded publication regression, including unchanged boat/helicopter bytes after bridge/cost changes.
- [test-pass] 2026-10-02 Normal v2 Carentan generation in retained isolated tree published 10 generations/71 fields; identities, race layers and candidate/unverified sidecars passed. Infantry reached 116 deck cells; available vehicle fields reached only 28 or 44, with remaining cells reported unreachable. All 367 protected files and 18 terrain inputs unchanged. Safe processor suite: 130 passed; Node harness passed. Evidence: `artifacts/bridge-flow-real-validation-001.md`; raw report: `artifacts/bridge-flow-real-implementation-001.md`. No production/raw writes, nested agents, sidebar verification or review approval.
- [browser] 2026-10-02 R17 isolated port-8083 integrated browser verified Carentan v2 Car availability, quiet candidate/unverified sidebar text, distinct 10/60-second painted frontiers, and stale notice/canvas removal on unavailable class/layer. External-only blocking reload succeeded; optional image/sidecar 404s remain. Shared 8080 returned 200. Three screenshots and exact steps: `artifacts/bridge-browser-validation-001.md`. No product/data edits or nested agents; keyboard tab activation used after mouse-click timeout. Bank/game truth and review approval remain unverified.

- [resume] 2026-10-03 Bridge remediation resumed under orchestration. User corrections: regenerate only six maps (carentan, tad_sae, albasrah_2, kunar_province, krivaja_valley, shijiavalley), NOT full corpus; browser flow-slider QA delegated to explorer subagent.
- [edit] 2026-10-03 B-01 fixed (subagent): `extract_obstructions.py` missing-client branch now keyed on actual client.zip absence; empty references with present client keep `bridge_source_available=True`; two regression tests added. Also added scoped map-name argv to `extract_obstructions.py main()` (orchestrator). 11/11 extractor tests pass.
- [validation] 2026-10-03 Extended isolated representative validation (subagent): kunar_province 2 decks/35 cells, krivaja_valley 8 decks/398 cells, all `candidates` status; byte-identical reruns; zero raster mismatches; 777 protected files hash-verified unchanged. Report: `add-terrain-traversability-model/artifacts/bridge-extended-representative-001.md`.
- [generation] 2026-10-03 Scoped production regeneration, 6/6 maps: extraction (6/6, errors=0), terrain format 1.1 with bridge_mask.bin + provenance sidecars, flow v2 (6/6, 4 workers). Boat/helicopter untouched. Verified: 132 processor tests passed (`--ignore=test_update_manifest.py`), Node harness all passed. Git diff scope: only 18 pre-existing dirty metadata.json (2 on target maps are pre-existing sea_level_m additions, unrelated).
- [next] Browser flow-slider production QA (explorer subagent) in progress; docs closeout pending.

- [browser] 2026-10-03 Production browser QA (subagent, Playwright + headless Edge on port 8080): krivaja_valley gpm_cq_64 Truck(wheeled) both teams. Sidebar verbatim: "Sources: 8. Candidate deck route; unverified. v2 catalog estimate; uncalibrated". Slider 10s->60s: 4,360 -> 30,480 nonzero-alpha canvas pixels (7x), distinct hashes. Helicopter clears note+canvas; switching back restores. Zero page errors. Verdict PASS. Report: `add-terrain-traversability-model/artifacts/bridge-browser-production-001.md`. Limits: pixel counts measure rendering, not per-cell routing; candidate geometry remains unverified in-game.
- [docs] 2026-10-03 Added "Bridge Decks and Movement Data" subsection to AGENTS.md (scoped extractor args, candidate-only policy, terrain 1.1 mask, boat/helicopter invariance); README feature list now mentions Opening Flow overlay with unverified bridge routing.
- [android] 2026-10-03 `build-android.bat` completed (BUILD SUCCESSFUL, debug APK ~2.1 GB). Verified `bridge_mask.bin` present in `android/app/src/main/assets/public/processed_maps/krivaja_valley/terrain/` and candidate note string present in packaged flow_overlay.js.
- [next] Final acceptance confirmation and review signoff remain open.
