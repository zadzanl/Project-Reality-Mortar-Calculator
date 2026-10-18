> [!WARNING] **Skepticism Disclaimer**
> Moderate confidence: all findings, test results, task counts, and line numbers were verified against live repo state and tool executions; however, zero client-side PR:BF2 game-engine tests and zero Android device builds were run.

## 1. What the prior attempt got wrong

1. **Incorrect OpenSpec Task Counts in Table (Section 2):**
   - **Input:** Inspection of `openspec/changes/add-opening-flow-simulator/tasks.md`, `openspec/changes/validate-bridge-crossing-connectivity/tasks.md`, and `openspec/changes/overhaul-ui-swiss-style/tasks.md`.
   - **Expected:** Accurate count of completed vs open tasks across each change.
   - **Actual:** Prior review reported `19 done, 10 open` for `add-opening-flow-simulator` (actual: **77 done, 11 open** across 88 total tasks); `0 / 22 done` for `validate-bridge-crossing-connectivity` (actual: **23 total tasks**, 0 done); and `0 / 24 done` for `overhaul-ui-swiss-style` (actual: **25 total tasks**, 0 done, having missed subtask `2.1a`).
   - **Root Cause:** Incomplete manual sampling across subsections rather than full checklist enumeration.

2. **Omission of Untracked Test Suite Dependency (`test_flow_dom.js`):**
   - **Input:** Cross-reference of `calculator/tests/run-tests.js` line 6 with `git status`.
   - **Expected:** Flag any test harness modifications that depend on untracked working-directory artifacts.
   - **Actual:** Prior review celebrated that `test_flow_dom.js` passed without noticing that tracked `run-tests.js` was modified to `import { runFlowDomTests } from './test_flow_dom.js'`, while `test_flow_dom.js` remains **untracked in Git**.
   - **Root Cause:** Reviewing test runner output without verifying tracking status in Git; on a clean clone or after `git clean -fd`, `npm test` immediately crashes with `ERR_MODULE_NOT_FOUND`.

3. **Untracked OpenSpec Archive Directory Omitted:**
   - **Input:** Inspection of `openspec/changes/archive/` and `git status`.
   - **Expected:** Inventory all untracked directories under `openspec/changes/`.
   - **Actual:** Prior review listed only the 4 active untracked change directories.
   - **Root Cause:** Overlooking `openspec/changes/archive/2026-10-04-validate-bridge-crossing-connectivity/` which is also untracked in Git (total: 5 untracked directories).

4. **Android Build Pipeline Shell Script Parity Overlooked:**
   - **Input:** Inspection of `build-android.sh` lines 75–78 alongside `build-android.bat`.
   - **Expected:** Flag that the 10.52 GiB / 10,770 MB asset packaging bloat affects Unix builds (`build-android.sh`) equally via `cp -r processed_maps www/`.
   - **Actual:** Focused exclusively on Windows `build-android.bat` without mentioning that Linux/macOS developers suffer the exact same asset explosion.
   - **Root Cause:** Restricting shell script audits to `.bat` scripts on Windows.

5. **Omission of Test Collection Regression Cause in Pytest:**
   - **Input:** Comparison of historical test records (`task-record.md:28` noting 130 tests) vs current pytest collection (102 tests).
   - **Expected:** Document why 28 test cases disappeared from the collection run.
   - **Actual:** Prior review noted 102 tests without explaining the 28-test drop from 130.
   - **Root Cause:** Uncommitted deletions in `processor/tests/test_terrain_cost.py` removed `test_confirmed_and_candidate_water_semantics` and stripped parameterization decorators from `test_step_and_ridge_hazards_survive_aggregation_and_roads`, collapsing 4 parameterized cases into 1 unparameterized errored function.

6. **Documentation Drift Omission for Test Runners in `AGENTS.md`:**
   - **Input:** Audit of `AGENTS.md` vs repo test harnesses.
   - **Expected:** Document that `AGENTS.md` fails to mention `npm test` (`run-tests.js`) and `test_server.py`.
   - **Actual:** Section 3 did not include test framework omissions in `AGENTS.md`.
   - **Root Cause:** Focused solely on architecture and data compression drift.

## 2. What I changed

- **File Updated:** `handoff/reports/CONDITION.md`
  - Corrected task counts in Section 2 table:
    - `add-opening-flow-simulator`: updated to **77 done, 11 open** (out of 88 total tasks).
    - `validate-bridge-crossing-connectivity`: updated to **0 / 23 tasks** done.
    - `overhaul-ui-swiss-style`: updated to **0 / 25 tasks** done (including subtask 2.1a).
  - Added **Critical Clean-Clone Fragility Warning** in Section 1.3 documenting that `calculator/tests/run-tests.js` imports untracked `calculator/tests/test_flow_dom.js`, creating an immediate break on fresh checkouts.
  - Added **Collection Drop Analysis** in Section 1.1 explaining the drop from 130 to 102 collected tests.
  - Added Unix parity in Section 1.6 documenting that `build-android.sh` line 77 (`cp -r processed_maps www/`) shares the identical 10.52 GiB / 10,770 MB asset explosion failure mode as `build-android.bat`.
  - Added Test Suite Documentation drift row to Section 3 table (`AGENTS.md` omits `npm test` and JavaScript test tooling).
  - Clarified disk space figures throughout report with exact byte counts and units: **11,293,286,499 bytes (10.52 GiB binary / 10,770.12 MiB / 11.29 GB decimal)**.
  - Upgraded Risk 3 in Section 4 to explicitly include untracked `test_flow_dom.js` and all 5 untracked OpenSpec directories.
  - Updated Section 5 (Observed Facts) ledger with all reconciled metrics.
  - Removed accidental line number prefixes from markdown content.
- **Review Report Written:** `c:\Projects\Project_Reality-Mortar-Calculator\.agents\teamwork\teamwork_preview_reviewer_2\handoff.md`.

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  - Safe Python test suite: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py` -> 90 passed, 4 failed, 8 errors (102 collected items in 4.00s).
  - Server test suite: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest calculator/tests/test_server.py` -> 7 passed, 0 failed in 0.49s.
  - Node core test runner: `npm test` (`node calculator/tests/run-tests.js`) -> 6 of 6 test suites passed in active tree.
  - Performance benchmark: `node calculator/tests/bench.js` -> 1,000 iterations passed, average full pipeline 0.004 ms (budget: <50 ms).
  - Map-specific test: `node calculator/tests/test_map_specific.js` -> FAILED at line 135 on Vadso City (`Expected status OUT_OF_RANGE, got UNREACHABLE`).
  - In-game validation test: `node calculator/tests/test_in_game.js` -> PASSED (1/1 vector on `test_bootcamp`).
  - Pytest collection check: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py --collect-only` -> 102 items collected.
  - Disk measurement via Python: 11,293,286,499 bytes total (5,505,810,432 bytes `.bin` = 5,250.75 MB; 5,412,464,871 bytes `.json` = 5,161.73 MB; 249,203,391 bytes `.png` = 237.66 MB; 125,804,026 bytes `.gz` = 119.98 MB).
  - Git status check: `git status` -> branch `feat/opening-flow-simulator`, 43 modified files, 7 untracked directories; `git check-ignore -v handoff/reports/CONDITION.md` confirmed `.gitignore:37:handoff/`.

- **Shallow Verification (manual only):**
  - Manual verification of checklist items in all 5 open changes in `openspec/changes/`.
  - Code inspection of `build-android.sh` lines 75–80 and `build-android.bat` lines 20–30.
  - Inspection of `calculator/tests/run-tests.js` line 6 importing untracked `test_flow_dom.js`.
  - Verification of line numbers and mechanisms in `processor/build_flow_fields.py:417-430`, `processor/build_flow_fields.py:1031`, `processor/tests/test_terrain_cost.py:40-74`, and `processor/tests/test_terrain_artifact.py:27`.

- **Unverified aspects:**
  - Android APK compilation via `./gradlew assembleDebug` was NOT run to avoid generating artifacts in `www/` or requiring Android SDK/Java 21 environment.
  - In-game PR v1.9 mortar elevation accuracy across 85 maps beyond the single bootcamp vector in `test_in_game.js` was not verified in an actual PR:BF2 client.
  - `processor/tests/test_update_manifest.py` was intentionally NOT executed per AGENTS.md safety rule.

## 4. Known Issues

- **Fatal Functional Bug:** Maintainer processor suite has 4 test failures and 8 setup errors on active branch `feat/opening-flow-simulator`.
- **Fatal Functional Bug:** `build-android.bat` and `build-android.sh` will attempt to package 10.52 GiB into APK assets unless `flow/` and `terrain/` are excluded.
- **Fatal Functional Bug:** Clean clone or `git clean -fd` breaks `npm test` due to untracked `calculator/tests/test_flow_dom.js` imported by tracked `run-tests.js`.
- **Minor Robustness Risk:** 5 directories under `openspec/changes/` are untracked by Git, vulnerable to accidental deletion via `git clean -fd`.
- **Minor Robustness Risk:** `test_map_specific.js` contains a stale assertion (`OUT_OF_RANGE`) out of sync with `ballistics.js` and `test_integration.js`.
- **Shallow Verification:** Android build viability and PR v1.9 game-client ballistic accuracy remain unverified.

## 5. Remaining risk & next step

The read-only assessment is complete, verified, and delivered in `handoff/reports/CONDITION.md`. Next round should attack:
1. Stage and track `calculator/tests/test_flow_dom.js` and all untracked `openspec/changes/` directories.
2. Fix the 4 test failures and 8 fixture errors on `feat/opening-flow-simulator`.
3. Add exclusion rules for `flow/` and `terrain/` to both `build-android.bat` and `build-android.sh`.
