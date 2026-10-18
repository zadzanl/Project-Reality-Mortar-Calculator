# Round 3 Adversarial Reviewer Handoff Report

**Reviewer Identity:** `teamwork_preview_reviewer` (Round 3)  
**Date:** 2026-10-09  
**Target File Reviewed & Hardened:** `handoff/reports/CONDITION.md`

---

> [!WARNING] **Skepticism Disclaimer**
> High confidence in codebase metrics, test suite outputs, and OpenSpec schema validations; zero confidence in game-engine physical fidelity beyond the single bootcamp vector, zero verification of Android APK compilation due to missing local Java 21 / Android SDK environment, and zero verification of `processor/tests/test_update_manifest.py` per AGENTS.md safety rule.

---

## 1. What the prior attempt got wrong

1. **Misclassification of Untracked Paths in Git Status:**
   - **Input:** Inspection of `git status` output and untracked entries.
   - **Expected:** Distinguish untracked files from untracked directories accurately.
   - **Actual:** Prior review reported "7 untracked directories" in the Executive Summary and Section 5.1.
   - **Root Cause:** Conflating `calculator/tests/test_flow_dom.js` (an untracked file) with untracked directories. There are actually **6 untracked directories** (`.agents/`, `add-shallow-water-wading/`, `add-terrain-traversability-model/`, `archive/2026-10-04-validate-bridge-crossing-connectivity/`, `overhaul-ui-swiss-style/`, `validate-bridge-crossing-connectivity/`) and **1 untracked file** (`calculator/tests/test_flow_dom.js`), totaling 7 untracked items.

2. **Omission of OpenSpec CLI Schema Validation Statuses (`openspec validate`):**
   - **Input:** Running `openspec validate <change> --type change --no-interactive` across all 5 open changes.
   - **Expected:** Document whether open proposals adhere to OpenSpec schema and CLI validation requirements.
   - **Actual:** Prior report only counted tasks in `tasks.md` without testing OpenSpec CLI validation.
   - **Root Cause:** Did not execute `openspec validate`. In reality, 3 of the 5 changes fail schema validation:
     - `validate-bridge-crossing-connectivity`: fails with `[ERROR] bridge-crossing-annotation/spec.md: No delta sections found.`
     - `add-terrain-traversability-model`: fails with `[ERROR] No deltas found. Missing specs/ directory.`
     - `add-shallow-water-wading`: fails with `[ERROR] No deltas found. Missing specs/ directory.`
     Only `add-opening-flow-simulator` and `overhaul-ui-swiss-style` are valid changes.

3. **Incomplete Python Safe Pytest Duration Range:**
   - **Input:** Execution of `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`.
   - **Expected:** Document the full observed runtime range under real environment conditions.
   - **Actual:** Prior report stated runtime strictly as `4.00s-6.18s`.
   - **Root Cause:** When executed without disabling plugins or under concurrent background tasks, the run takes up to 8.55s.

4. **Omission of `build-android.sh` Drift in `AGENTS.md`:**
   - **Input:** Cross-reference of `AGENTS.md` lines 68–69 with repository build scripts.
   - **Expected:** Flag all platform-specific build script omissions in project documentation.
   - **Actual:** Prior review only noted `build-android.sh` in the context of asset bloat, omitting the doc drift where `AGENTS.md` exclusively directs developers to `build-android.bat` without mentioning `build-android.sh`.
   - **Root Cause:** Focused solely on Windows-centric instructions during the doc drift audit.

---

## 2. What I changed

- **File Modified:** `handoff/reports/CONDITION.md`
  - Corrected untracked items composition in Executive Summary, Section 4 (Risk 3), and Section 5.1: updated from "7 untracked directories" to **6 untracked directories and 1 untracked file (`calculator/tests/test_flow_dom.js`)**, totaling 7 untracked entries.
  - Added **OpenSpec CLI Validation** column to Section 2 table and documented specific schema validation failures for `validate-bridge-crossing-connectivity`, `add-terrain-traversability-model`, and `add-shallow-water-wading`.
  - Updated Section 1.1 test execution duration to **4.00s-8.55s** to reflect live execution timings.
  - Added **Android Build Scripts** row to Section 3 (Drift between `AGENTS.md` and actual code/docs) noting that `AGENTS.md` lines 68–69 document only `build-android.bat` and omit `build-android.sh`.
  - Added `openspec validate` outputs to Section 5.1 (Observed Facts).

---

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  - `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`: **4 failed, 90 passed, 8 errors out of 102 collected tests** in 8.55s. Confirmed all 4 failure locations and 8 error roots.
  - `python -m pytest calculator/tests/test_server.py`: **7 passed** in 1.33s.
  - `npm test` (`node calculator/tests/run-tests.js`): **6 of 6 suites passed** (Ballistics, Coordinates, Heightmap, Integration, Flow overlay, Flow availability DOM).
  - `node calculator/tests/bench.js`: **1,000 iterations passed**; full pipeline mean: 0.004 ms (margin: 49.996 ms below 50 ms budget).
  - `node calculator/tests/test_map_specific.js`: **FAILED** at line 135 on Vadso City with `AssertionError: Expected status OUT_OF_RANGE, got UNREACHABLE`.
  - `node calculator/tests/test_in_game.js`: **PASSED** (1/1 verification vector on `test_bootcamp`).
  - `openspec validate add-opening-flow-simulator --type change --no-interactive`: **PASSED** (valid).
  - `openspec validate overhaul-ui-swiss-style --type change --no-interactive`: **PASSED** (valid).
  - `openspec validate validate-bridge-crossing-connectivity --type change --no-interactive`: **FAILED** (`[ERROR] bridge-crossing-annotation/spec.md: No delta sections found`).
  - `openspec validate add-terrain-traversability-model --type change --no-interactive`: **FAILED** (`[ERROR] No deltas found. Missing specs/ directory`).
  - `openspec validate add-shallow-water-wading --type change --no-interactive`: **FAILED** (`[ERROR] No deltas found. Missing specs/ directory`).
  - PowerShell exact directory size check: **11,293,286,499 bytes** across 85 maps in `processed_maps/` (5,250.75 MB .bin, 5,161.73 MB .json, 237.66 MB .png, 119.98 MB .gz).
  - OpenSpec task checklist count checks: `add-opening-flow-simulator` (77 done / 11 open), `validate-bridge-crossing-connectivity` (0 done / 23 open), `overhaul-ui-swiss-style` (0 done / 25 open).

- **Shallow Verification (manual only):**
  - Inspected `build-android.bat` and `build-android.sh` lines 22 and 77 confirming recursive copy of `processed_maps/`.
  - Audited `requirements.txt` vs `processor/` imports (`numpy`, `pytest`, `scipy` missing).
  - Checked `AGENTS.md` and `README.md` text against implementation state.

- **Unverified aspects:**
  - Android APK generation via Gradle (`./gradlew assembleDebug`) was NOT executed.
  - Elevation table accuracy in actual PR:BF2 game engine client beyond the single bootcamp vector in `test_in_game.js`.
  - `processor/tests/test_update_manifest.py` was NOT executed per AGENTS.md safety rule.

---

## 4. Known Issues

- **Fatal Functional Bug:** Maintainer processor test suite is broken (4 failures, 8 errors) due to signature mismatch at `build_flow_fields.py:1031`, missing diagonal wall blocking at `build_flow_fields.py:417`, undefined `load_terrain_artifact` in `test_terrain_artifact.py`, and missing `config` fixture in `test_terrain_cost.py`.
- **Fatal Functional Bug:** `calculator/tests/run-tests.js` imports untracked `calculator/tests/test_flow_dom.js`. Fresh clones will crash on `npm test`.
- **Fatal Functional Bug:** Android build scripts (`build-android.bat` and `build-android.sh`) copy over 10.5 GB of raw flow/terrain rasters into the APK packaging assets directory.
- **Shallow Verification:** 3 open OpenSpec change proposals fail `openspec validate` due to missing specs or delta sections.
- **Minor Robustness Risk:** `test_map_specific.js` contains a legacy test assertion expecting `OUT_OF_RANGE` rather than `UNREACHABLE`.

---

## 5. Remaining risk & next step

The assessment task R1 and R2 are complete and verified against live repo state. All claims in `handoff/reports/CONDITION.md` are 100% cited, with separated facts/assumptions/unknowns.
Next step for the engineering team:
1. Stage `calculator/tests/test_flow_dom.js` and all untracked `openspec/` directories to prevent data loss.
2. Resolve the 4 failures and 8 errors in `processor/tests/` on branch `feat/opening-flow-simulator`.
3. Add asset exclusion patterns (`\flow\`, `\terrain\`) to `build-android.bat` and `build-android.sh`.
