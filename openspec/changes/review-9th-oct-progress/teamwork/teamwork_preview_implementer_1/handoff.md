# Handoff Report: Codebase Condition Assessment

**Task:** Self-contained read-only assessment of Project Reality Mortar Calculator  
**Deliverable File:** `handoff/reports/CONDITION.md`  
**Working Directory:** `c:\Projects\Project_Reality-Mortar-Calculator`  
**Branch:** `feat/opening-flow-simulator`  
**Author:** implementer (`teamwork_preview_implementer_1`)  
**Date:** 2026-10-09  

---

## Summary of Findings

1. **Test Status:**
   - Safe Python test command (`python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`): **FAILED** (90 passed, 4 failed, 8 errors / 102 total).
     - Failures in `processor/tests/test_flow_field.py` (`TypeError` on `solve_field` argument count, diagonal cutoff assertion) and `processor/tests/test_terrain_artifact.py` (NameError `load_terrain_artifact`).
     - 8 setup errors in `processor/tests/test_terrain_cost.py` caused by missing `config` fixture.
   - Python server tests (`python -m pytest calculator/tests/test_server.py`): **PASSED** (7/7 passed).
   - Core JavaScript test suite (`npm test` / `node calculator/tests/run-tests.js`): **PASSED** (6/6 suites passed).
   - Auxiliary JavaScript tests: `test_map_specific.js` **FAILED** (AssertionError on status enum), `test_in_game.js` **PASSED** (1 vector).

2. **Open OpenSpec Changes Status:**
   - `validate-bridge-crossing-connectivity`: 0 of 22 tasks marked done in `tasks.md`. Phase A/redo-2 assets exist in `handoff/`, but execution is stalled because delegated subagents lacked vision capability (`status: blocked`). No crossing records in production terrain sidecars. Only 6 maps have `bridge_mask.bin`.
   - `add-opening-flow-simulator`: 19 completed, 10 open tasks. In progress with 43 dirty files in the worktree. Tests broken.
   - `add-terrain-traversability-model`: Active task-record revision 2 in progress. Gated on fixture maps and defect fix at `extract_obstructions.py:224`.
   - `overhaul-ui-swiss-style`: Untracked proposal with 24 open tasks, pending flow simulator stabilization.
   - `add-shallow-water-wading`: Untracked stub directory with plan only.

3. **Drift in AGENTS.md and Documentation:**
   - Scope drift: AGENTS.md describes Version 1 Scope as simple mortar calc, ignoring Flow Simulator, terrain rasters, and particle animation.
   - Storage drift: Heightmaps are `.json.gz` with pako decompression, not plain JSON.
   - Pipeline drift: Architecture uses modular Python scripts, not `process_maps.ipynb`.
   - Test command drift: Documented safe command currently fails.
   - Dependencies drift: `requirements.txt` lacks `numpy` and `pytest`.
   - Map count: README.md claims 84 maps, while `mapsList.json` has 85.

4. **Ranked Risks:**
   - Risk 1 (High): Regressed and broken test suite on active branch.
   - Risk 2 (High): Stalled bridge traversability pipeline from vision subagent failures.
   - Risk 3 (High): Massive uncommitted working tree drift (43 modified files).
   - Risk 4 (Medium): Android build asset bloat (>1.5 GB terrain/flow data copied to APK).
   - Risk 5 (Medium): Documentation and dependencies drift in `AGENTS.md` and `requirements.txt`.

The complete detailed report is delivered at `handoff/reports/CONDITION.md`.
