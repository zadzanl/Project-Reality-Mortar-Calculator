> [!WARNING] **Skepticism Disclaimer**
> Moderate confidence: the codebase evaluation is grounded in actual executed test suites, disk measurements, and source inspection; however, zero client-side PR:BF2 game-engine validation or Android device builds were run.

## 1. What the prior attempt got wrong

1. **Android Build Asset Bloat Understatement:**
   - **Input:** Disk scan of `processed_maps/` directory.
   - **Expected:** Report exact disk usage and breakdown so packaging impact is accurately understood.
   - **Actual:** Prior attempt cited `>1.5 GB`. Actual disk usage is **10.77 GB** (`10,770 MB`), comprising 5,250.75 MB in `.bin` (flow fields/costs), 5,161.73 MB in `.json` (race matrices/gamelayers/sidecars), 237.66 MB in `.png`, and 119.98 MB in `.gz`.
   - **Root Cause:** Incomplete manual size assessment without full recursive aggregation over all 85 map directories. The core mortar calculator only requires ~358 MB (`.gz` + `.png` + `metadata.json`), so `build-android.bat` copying all 10.77 GB causes a 30x asset explosion.

2. **Omission of `.gitignore` Explanation for Deliverable:**
   - **Input:** `git status` check against acceptance criteria.
   - **Expected:** Explain why `handoff/reports/CONDITION.md` does not appear as untracked in `git status`.
   - **Actual:** Prior attempt listed `git status` without explaining that `handoff/` is listed on line 37 of `.gitignore` (`.gitignore:37:handoff/`).
   - **Root Cause:** Lack of explicit investigation into `.gitignore`, leaving junior maintainers confused as to why `git status` without `--ignored` shows no new report file.

3. **Incomplete Technical Root Causes for Processor & JS Test Failures:**
   - **Input:** Inspection of failing test suites.
   - **Expected:** Pinpoint the exact line numbers and mechanical mechanisms for each failure.
   - **Actual:** High-level descriptions without exact line mechanics (e.g. why diagonal cutting failed in Dijkstra, why `OUT_OF_RANGE` was expected in `test_map_specific.js`).
   - **Root Cause:**
     - For `test_land_diagonal_cannot_cut_between_blocked_orthogonal_cells`: `solve_field` (`build_flow_fields.py:417-430`) tests 8-connected diagonal neighbors without verifying that both orthogonal neighbors are unblocked, permitting corner-cutting between blocked cells.
     - For `test_v2_normal_generation_filters_selected_sources_and_keeps_classes`: `build_flow_fields.py:1031` passes 5 arguments to `solve_field(costs, sources, speed_ms, cell_size_m)` which only accepts 4.
     - For `test_terrain_artifact.py`: Missing `from terrain_artifact import load_terrain_artifact`.
     - For `test_terrain_cost.py`: Uncommitted deletion removed lines 46-69 (`@pytest.fixture def config()`), breaking 8 dependent tests.
     - For `test_map_specific.js:135`: `ballistics.js:315-320` returns `UNREACHABLE` on negative discriminant; `OUT_OF_RANGE` is never emitted by the engine.

4. **Missing Performance Benchmark Documentation:**
   - **Input:** Test suite inventory.
   - **Expected:** Benchmark results documented alongside unit and integration tests.
   - **Actual:** `calculator/tests/bench.js` was omitted from the prior report.
   - **Root Cause:** Focused solely on `npm test` without auditing auxiliary test runner scripts.

5. **Untracked OpenSpec Changes Risk Unstated:**
   - **Input:** `git status` inspection of `openspec/changes/`.
   - **Expected:** Highlight that 4 of the 5 change directories are completely untracked in Git.
   - **Actual:** Listed them simply as proposals or active directories without flagging the data-loss risk.
   - **Root Cause:** Overlooking Git tracking status of directory trees under `openspec/changes/`.

## 2. What I changed

- **File Updated:** `handoff/reports/CONDITION.md`
  - Corrected disk consumption of `processed_maps/` to exact measured values: **10.77 GB** (`10,770 MB`) with full extension breakdown.
  - Added full root-cause mechanics and line numbers for all 4 processor test failures, 8 fixture errors, and `test_map_specific.js`.
  - Added Section 1.4 documenting `node calculator/tests/bench.js` performance (0.004 ms average vs 50 ms budget).
  - Added detailed explanation of `.gitignore:37:handoff/` interaction with `git status`.
  - Upgraded Risk 2 (Android asset bloat) and Risk 3 (working tree drift + untracked OpenSpec directories) with precise impacts and mitigation steps.
  - Refined Section 5 (Facts, Assumptions, Unknowns) to cover all ledger items cleanly.

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  - Safe Python test command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py` -> 90 passed, 4 failed, 8 errors (102 total in 6.18s).
  - Python server test suite: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest calculator/tests/test_server.py` -> 7 passed, 0 failed in 0.70s.
  - Node core test runner: `npm test` (`node calculator/tests/run-tests.js`) -> 6/6 test suites passed.
  - Performance benchmark: `node calculator/tests/bench.js` -> 1,000 iterations passed, average 0.004 ms per full pipeline calculation.
  - Auxiliary map test: `node calculator/tests/test_map_specific.js` -> FAILED at line 135 on Vadso City (`Expected status OUT_OF_RANGE, got UNREACHABLE`).
  - In-game validation test: `node calculator/tests/test_in_game.js` -> PASSED (1/1 vector on `test_bootcamp`).
  - Git ignore verification: `git check-ignore -v handoff/reports/CONDITION.md` -> `.gitignore:37:handoff/`.
  - Disk space measurement: Python script measuring `processed_maps/` -> 10,770.12 MB total (5,250.75 MB `.bin`, 5,161.73 MB `.json`, 237.66 MB `.png`, 119.98 MB `.gz`).

- **Shallow Verification (manual only):**
  - Code inspection of `processor/build_flow_fields.py`, `processor/tests/test_flow_field.py`, `processor/terrain_artifact.py`, and `processor/tests/test_terrain_cost.py` to confirm root causes.
  - Inspection of `build-android.bat` to confirm `xcopy` behavior.
  - Inspection of `openspec/changes/` directories to verify task states and Git untracked status.

- **Unverified aspects:**
  - Android APK compilation via `build-android.bat` / `./gradlew assembleDebug` was NOT run to avoid generating artifacts in `www/` or requiring local Android SDK/Java 21 environment.
  - In-game PR v1.9 mortar elevation accuracy across 85 maps beyond the single bootcamp vector in `test_in_game.js` was not verified in an actual PR:BF2 client.
  - `processor/tests/test_update_manifest.py` was intentionally NOT executed per AGENTS.md safety rule.

## 4. Known Issues

- **Fatal Functional Bug:** Maintainer processor suite has 4 test failures and 8 setup errors on active branch `feat/opening-flow-simulator`.
- **Fatal Functional Bug:** `build-android.bat` will attempt to package 10.77 GB into APK assets unless `flow/` and `terrain/` are excluded.
- **Minor Robustness Risk:** 4 of 5 active OpenSpec change directories in `openspec/changes/` are untracked by Git, vulnerable to accidental deletion via `git clean -fd`.
- **Minor Robustness Risk:** `test_map_specific.js` contains a stale assertion (`OUT_OF_RANGE`) out of sync with `ballistics.js` and `test_integration.js`.
- **Shallow Verification:** Android build viability and PR v1.9 game-client ballistic accuracy remain unverified.

## 5. Remaining risk & next step

The read-only assessment is complete, verified, and delivered in `handoff/reports/CONDITION.md`. Next round should focus on:
1. Fixing the 4 test failures and 8 fixture errors on `feat/opening-flow-simulator`.
2. Updating `build-android.bat` with exclusion rules for `flow/` and `terrain/`.
3. Staging and tracking untracked OpenSpec directories.
