# Codebase Condition Assessment Report: Project Reality Mortar Calculator

**Date:** 2026-10-09  
**Repository Working Directory:** `c:\Projects\Project_Reality-Mortar-Calculator`  
**Current Git Branch:** `feat/opening-flow-simulator`  
**Assessment Type:** Read-only health assessment  
**Target Audience:** Junior and Senior Maintainers  

---

## Executive Summary

The Project Reality Mortar Calculator codebase is currently in a transitional state between a lightweight, focused mortar ballistic calculator and an ambitious, data-intensive "Opening Flow Simulator" with multi-team terrain traversability, Dijkstra wave-propagation solvers, and bridge modeling.

While core mortar ballistics and coordinate calculations remain exceptionally fast (0.004 ms per solution), accurate, and well-tested (100% pass rate in the JavaScript engine and Flask server), the maintainer-side processor pipeline in the active working tree is in a degraded condition:
- The primary Python processor test suite (`pytest`) has **4 failures and 8 setup errors** out of 102 collected tests (down from 130 tests previously recorded due to uncommitted test deletions).
- 43 modified files, 6 untracked directories, and 1 untracked test file (7 untracked entries total) represent 18,874 lines of uncommitted diff (+15,322 / -3,552) on `feat/opening-flow-simulator`.
- 5 directories under `openspec/changes/` (4 active proposals/records + 1 archive directory) are completely untracked by Git, putting research artifacts and designs at risk of data loss.
- A modified tracked test runner (`calculator/tests/run-tests.js`) imports an untracked test file (`calculator/tests/test_flow_dom.js`), creating an immediate build break for any clean checkout or CI clone.
- The bridge crossing connectivity initiative (`validate-bridge-crossing-connectivity`) is stalled at Phase B/C due to vision-model subagent execution failures.
- `processed_maps/` has swollen to **10.52 GiB / 10,770 MB (11.29 GB decimal)** across 85 maps (5.25 GB in binary arrays, 5.16 GB in JSON sidecars/gamelayers), threatening the Android packaging pipeline.
- `AGENTS.md` and `README.md` have drifted significantly from the actual architecture, map counts, data compression formats, and pipeline dependencies.
- The deliverable report directory `handoff/` is listed in `.gitignore:37`, explaining why `git status` does not show untracked reports unless `--ignored` is supplied.

---

## 1. Test and Build Status

### 1.1 Python Test Suite (Safe Processor Suite)
- **Command:** `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`
  *(Note: Run with `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"` on Windows to avoid plugin autoload hangs)*
- **Result:** **FAILED** (90 passed, 4 failed, 8 errors out of 102 collected tests in 4.00s-8.55s)
- **Collection Drop Analysis:** Prior task records (`task-record.md:28`) documented 130 passed tests on 2026-10-03. The current suite collects only 102 tests. This drop of 28 tests stems from uncommitted deletions in `processor/tests/test_terrain_cost.py` (which deleted `test_confirmed_and_candidate_water_semantics` and stripped parameterization decorators from `test_step_and_ridge_hazards_survive_aggregation_and_roads`, collapsing 4 parameterized cases into 1 unparameterized errored function), combined with test consolidation in `test_flow_field.py`.
- **Breakdown of Failures and Errors:**
  1. `processor/tests/test_flow_field.py::test_land_diagonal_cannot_cut_between_blocked_orthogonal_cells`
     - **Failure:** `AssertionError: assert 1.4142135 == -1.0` (at `test_flow_field.py:59`).
     - **Root Cause:** In `processor/build_flow_fields.py` lines 417-430, `solve_field` iterates over 8-connected diagonal offsets and checks only if the destination cell `idx + delta` is unblocked (`cost_b <= 0`). It fails to verify whether either adjacent orthogonal neighbor `(row, col + d_col)` or `(row + d_row, col)` is blocked, incorrectly permitting diagonal movement through blocked orthogonal corners in 1.414s rather than remaining unreachable.
  2. `processor/tests/test_flow_field.py::test_v2_normal_generation_filters_selected_sources_and_keeps_classes`
     - **Failure:** `TypeError: solve_field() takes 4 positional arguments but 5 were given` (at `processor/build_flow_fields.py:1031`).
     - **Root Cause:** `solve_field` definition at `processor/build_flow_fields.py:371` expects 4 arguments `(costs, sources, speed_ms, cell_size_m)`, but caller at line 1031 passes 5 arguments: `solve_field(terrain["land"]["costs"], cells, speed, terrain["land"]["cell_size_m"], terrain["land"])`.
  3. `processor/tests/test_terrain_artifact.py::test_loader_returns_flow_contract`
     - **Failure:** `NameError: name 'load_terrain_artifact' is not defined` (at `test_terrain_artifact.py:27`).
     - **Root Cause:** Uncommitted deletion removed `from terrain_artifact import load_terrain_artifact` (replacing it with `import hashlib`) in `processor/tests/test_terrain_artifact.py`.
  4. `processor/tests/test_terrain_artifact.py::test_loader_rejects_wrong_grid_length`
     - **Failure:** `NameError: name 'load_terrain_artifact' is not defined` (at `test_terrain_artifact.py:47`).
     - **Root Cause:** Same missing import in `test_terrain_artifact.py`.
  5. `processor/tests/test_terrain_cost.py` (8 parameterized and standard tests):
     - **Error:** `fixture 'config' not found` for:
       - `test_step_and_ridge_hazards_survive_aggregation_and_roads`
       - `test_explicit_roads_exclude_decals_and_keep_terrain_class`
       - `test_water_static_and_dense_vegetation_raise_cost_without_blocking`
       - `test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes[False-2.0]`
       - `test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes[False-8.0]`
       - `test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes[True-2.0]`
       - `test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes[True-8.0]`
       - `test_raw_south_rows_reach_south_artifact_and_minimap`
     - **Root Cause:** Lines 40-74 defining `test_confirmed_and_candidate_water_semantics`, `@pytest.fixture def config():`, and the `@pytest.mark.parametrize` decorators were deleted from `processor/tests/test_terrain_cost.py` during uncommitted working tree edits, breaking 8 downstream test setups.

### 1.2 Python Server Test Suite
- **Command:** `python -m pytest calculator/tests/test_server.py`
- **Result:** **PASSED** (7 passed in 0.49s-0.70s).
- **Coverage:** Flask route security (`secure_filename`), static asset resolution, maps JSON endpoint, index routing.

### 1.3 JavaScript Core Test Suite (Node.js Test Runner)
- **Command:** `npm test` (invoking `node calculator/tests/run-tests.js`)
- **Result:** **PASSED** (6 of 6 test suites passed in active tree).
  - Ballistics tests (`test_ballistics.js`): PASSED
  - Coordinates tests (`test_coordinates.js`): PASSED
  - Heightmap tests (`test_heightmap.js`): PASSED
  - Integration tests (`test_integration.js`): PASSED (5 pipeline scenarios)
  - Flow overlay tests (`test_flow_overlay.js`): PASSED
  - Flow availability DOM tests (`test_flow_dom.js`): PASSED
- **Critical Clean-Clone Fragility:** `calculator/tests/run-tests.js` line 6 was modified to import `calculator/tests/test_flow_dom.js`:
  ```javascript
  import { runFlowDomTests } from './test_flow_dom.js';
  ```
  However, `calculator/tests/test_flow_dom.js` is currently **untracked in Git**. On any clean checkout, fresh clone, or after `git clean -fd`, running `npm test` immediately crashes with `ERR_MODULE_NOT_FOUND: Cannot find module './test_flow_dom.js'`. The file must be tracked in Git immediately.

### 1.4 JavaScript Performance Benchmark
- **Command:** `node calculator/tests/bench.js`
- **Result:** **PASSED** (1,000 iterations over `test_bootcamp` 4096m, 513x513).
  - Grid reference parsing: 0.001 ms (mean)
  - Grid to XY conversion: 0.001 ms (mean)
  - Elevation sampling (bilinear interpolation): 0.001 ms (mean)
  - Firing solution calculation: 0.003 ms (mean)
  - Full pipeline (Grid -> XY -> Elevation -> Solution): 0.004 ms (mean), 0.003 ms (median), 0.055 ms (P99).
  - Performance target (<50 ms): Met with a **49.996 ms margin**.

### 1.5 Auxiliary and In-Game JavaScript Tests
- **Command:** `node calculator/tests/test_map_specific.js`
  - **Result:** **FAILED** (`AssertionError [ERR_ASSERTION]: Expected status OUT_OF_RANGE, got UNREACHABLE` at line 135 during Vadso City long-range test).
  - **Root Cause:** In `calculator/static/js/ballistics.js` lines 315-320, when trajectory discriminant is negative, `validateFiringSolution` returns `{ status: 'UNREACHABLE' }`. The status `'OUT_OF_RANGE'` is never emitted by the calculation engine. `test_map_specific.js` contains a legacy test assertion expecting `'OUT_OF_RANGE'`, while `test_integration.js` already asserts `UNREACHABLE`.
  - **Observation:** This test is currently not wired into `run-tests.js`.
- **Command:** `node calculator/tests/test_in_game.js`
  - **Result:** **PASSED** (1/1 validation vector on `test_bootcamp`: D6-5 -> F8-5 matched within tolerance).

### 1.6 Build and Deployment Status
- **Desktop/Web Server:**
  - Launchable via `python -m calculator.server` or `run.bat` / `run.sh`.
  - Fully offline: Leaflet and Pako vendored in `calculator/static/lib/`.
- **Android Build Pipeline (`build-android.bat` / `build-android.sh`):**
  - Requires Java 21, Android SDK (`ANDROID_HOME`), and `@capacitor/cli`.
  - Workflow: Cleans `www/`, copies `calculator/static/`, `templates/index.html`, `processed_maps/`, and `mapsList.json`, renames `*.gz` to `*.gzip`, rewrites URLs for `file://` scheme, and invokes `npx cap sync android` + `gradlew assembleDebug` (Windows: `call gradlew.bat assembleDebug`; Unix: `./gradlew assembleDebug`).
  - **Critical Failure Mode:** Both `build-android.bat` (line 22: `xcopy /E /I /Y processed_maps www\processed_maps`) and `build-android.sh` (line 77: `cp -r processed_maps www/`) execute an unrestricted recursive copy of `processed_maps/`.
    `processed_maps/` currently contains **11,293,286,499 bytes (10.52 GiB / 10,770.12 MiB / 11.29 GB decimal)** across 85 maps. Copying this complete directory into `www/` and syncing into `android/app/src/main/assets/public/` causes severe asset explosion (>10.5 GB), overwhelming Android asset packaging limits unless non-essential `flow/` and `terrain/` directories are excluded.

---

## 2. Status of Open OpenSpec Changes

Directory inspected: `openspec/changes/`

| Change ID | Status | Tasks Done vs Open | OpenSpec CLI Validation | Key Blockers & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`validate-bridge-crossing-connectivity`** | **Blocked / Stalled** *(Untracked in Git)* | **0 / 23 tasks marked done** in `tasks.md` | **INVALID (Schema Error)**: `bridge-crossing-annotation/spec.md: No delta sections found` | **Blocked on Vision Delegation:** Delegated annotators (`deepseek-v4.1-flash`) lacked vision capabilities; fallback retry on `gpt-4.1` failed to write disk artifacts. 0 crossing records in production sidecars. Only 6 maps have `bridge_mask.bin`. Directory is untracked in Git. Fails `openspec validate`. |
| **`add-opening-flow-simulator`** | **In Progress / Dirty** | **77 done, 11 open** in `tasks.md` | **VALID** (`Change 'add-opening-flow-simulator' is valid`) | Active branch `feat/opening-flow-simulator`. 43 modified files. Safe pytest suite broken with 4 failures + 8 errors (`solve_field` argument count mismatch, missing `config` fixture). Imports untracked `test_flow_dom.js`. Open tasks include 5 in QA follow-up, 2 in Android sync 3.5, 4 in Phase 4 docs. |
| **`add-terrain-traversability-model`** | **Pending / Incomplete** *(Untracked in Git)* | Archived 2026-09-28; active dir has Revision 2 task record | **INVALID (Schema Error)**: `No deltas found; missing specs/ directory` | B-01 blocking defect at `extract_obstructions.py:224` (false-unavailable branch). `albasrah_2` missing initial base build. Only 6 fixture maps gated (`albasrah_2`, `carentan`, `krivaja_valley`, `kunar_province`, `shijiavalley`, `tad_sae`). Directory is untracked in Git. No `tasks.md`. Fails `openspec validate`. |
| **`overhaul-ui-swiss-style`** | **Proposed / Unstarted** *(Untracked in Git)* | **0 / 25 tasks done** in `tasks.md` | **VALID** (`Change 'overhaul-ui-swiss-style' is valid`) | Untracked proposal/design across 6 phases (including task 2.1a). Blocked awaiting stabilization of flow simulator layout. Passes `openspec validate`. |
| **`add-shallow-water-wading`** | **Proposed / Stub** *(Untracked in Git)* | **0 tasks defined** (plan artifact only) | **INVALID (Schema Error)**: `No deltas found; missing specs/ directory` | Stub containing only `.openspec.yaml` and `shallow-water-wading-plan.md`. Directory is untracked in Git. Fails `openspec validate`. |

*Note on Untracked Changes:* In addition to the 4 active untracked change directories above, `openspec/changes/archive/2026-10-04-validate-bridge-crossing-connectivity/` is also untracked, making **5 total untracked directories** under `openspec/changes/`. Out of all 5 changes, only 2 (`add-opening-flow-simulator` and `overhaul-ui-swiss-style`) pass `openspec validate --type change --no-interactive`; the remaining 3 fail schema validation due to missing specs or missing delta sections.

### Deep Dive: `validate-bridge-crossing-connectivity`
1. **Goal:** Replace unreliable automatic bridge name/mesh detection with human-auditable rotated-rectangle annotations from `minimap.png`, derive bank connectivity from terrain elevation, and emit crossing records for vehicle routing.
2. **Current State:**
   - Round 1 smoke test passed (7 maps).
   - Redo-2 Phase A generated 48 tile images and 12 packets/prompts in `handoff/packets/redo2/`.
   - **Hard Blocker:** Subagent dispatch for Phase B (redo annotators) stalled when `deepseek-v4.1-flash` was invoked on image assets without vision support (`status: blocked`). A subsequent single-map retry on `gpt-4.1` was rejected because the generated artifact was not written to disk.
   - User adjudication on disagreements is pending; no bridge crossing records have been approved or merged into production terrain sidecars (`processed_maps/*/terrain/sidecar.json`).
   - Untracked in Git: The entire directory `openspec/changes/validate-bridge-crossing-connectivity/` is untracked.

---

## 3. Drift Between AGENTS.md and Actual Code/Docs

| Topic | `AGENTS.md` Statement | Actual Repository State | Impact / Severity |
| :--- | :--- | :--- | :--- |
| **Scope of Application** | Line 55: "Version 1 Scope: One mortar + one target... Flask server that only serves files... High-angle calculation in Mils..." | Codebase includes multi-team Opening Flow Simulator, particle advection, contour layers, terrain cost rasters, vehicle speed catalog. | **High:** New developers assume the codebase is a static math tool and do not anticipate Dijkstra solvers or canvas overlays. |
| **Heightmap Storage Format** | Line 61: "Heightmaps as JSON (not PNG), keeping full 16-bit precision (0 to 65535)." | Heightmaps are stored as compressed `heightmap.json.gz` (renamed `.gzip` for Android). Loaded using `pako.ungzip`. | **Medium:** Uncompressed `.json` does not exist on disk; direct JSON loads fail. |
| **Map Processing Architecture** | Lines 75–77: "Phase 1 - collect_maps.py... Phase 2 - process_maps.ipynb... Keep the phases separate... conversion code only in process_maps.ipynb." | Maintainer pipeline is driven by modular Python CLI scripts: `extract_gamelayers.py`, `extract_obstructions.py`, `build_terrain_cost.py`, `build_flow_fields.py`, `process_one_map.py`. | **Medium:** `process_maps.ipynb` is legacy; following AGENTS.md leads to obsolete workflows. |
| **Safe Processor Test Command** | Line 80: "Safe command: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`." | Running this command fails with 4 failures and 8 errors. Furthermore, bare pytest on Windows hangs on third-party plugin autoload without `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. | **High:** Contributors running the documented test command get misleading failure cascades and potential terminal hangs. |
| **Test Suite Documentation** | Line 80 only documents the Python processor test command. | Codebase includes a comprehensive JavaScript test runner (`npm test` / `node calculator/tests/run-tests.js`), server tests (`python -m pytest calculator/tests/test_server.py`), and benchmarks (`node calculator/tests/bench.js`). None are mentioned in AGENTS.md. | **Medium:** New contributors cannot find or run core client-side test suites from AGENTS.md alone. |
| **Bridge Crossing Authority** | Lines 85–87: "Crossing records are the vehicle-routing authority... bridge_mask.bin (0 none, 1 confirmed, 2 candidate)." | Only 6 of 85 maps have `bridge_mask.bin`. No production terrain sidecar contains validated crossing records; bridges are either Mode B candidate or inactive. | **Medium:** Creates false expectation that validated crossings exist in the current corpus. |
| **Map Count** | Line 78 refers to 85 maps (excluding `the_falklands`). `README.md` line 17 says "Support for all 84 Project Reality maps". | `mapsList.json` explicitly lists `"count": 85` entries. | **Low:** Minor documentation inconsistency. |
| **Android Build Scripts** | Lines 68–69 specify `build-android.bat` exclusively: "Never edit `www/` - `build-android.bat` deletes and regenerates it... run `build-android.bat` (or `npx cap sync android`)". | The repository includes both `build-android.bat` (Windows) and `build-android.sh` (Linux/macOS). `AGENTS.md` omits `build-android.sh` entirely. | **Low:** Unix/macOS maintainers may not discover the native shell build script. |
| **Python Dependencies** | `requirements.txt` lists: `Flask`, `Werkzeug`, `Pillow`, `pyinstaller`, `jaraco.text`. | Missing `numpy`, `pytest`, and `scipy` which are required to run `processor/` and tests. | **Medium:** Clean environment setup per `requirements.txt` cannot execute maintainer scripts or tests. |

---

## 4. Top Risks (Ranked)

### Risk 1: Regressed and Broken Test Suite on Active Branch (`feat/opening-flow-simulator`)
- **Severity:** High
- **Evidence:** `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py` yields 4 failures and 8 errors out of 102 collected tests (regressed from 130 tests on 2026-10-03).
  - `build_flow_fields.py:1031` calls `solve_field` with 5 positional arguments when the signature expects 4.
  - `test_flow_field.py:59` fails because `solve_field` permits diagonal corner cutting between blocked orthogonal cells in 1.414s.
  - `test_terrain_artifact.py` references undefined `load_terrain_artifact` due to deleted import.
  - `test_terrain_cost.py` has 8 setup errors due to deleted `config` fixture and deleted parameterization decorators.
  - `test_map_specific.js` fails with status mismatch assertion (`Expected status OUT_OF_RANGE, got UNREACHABLE` at line 135).
- **Impact:** Contributors cannot rely on test suites for regression testing. CI runs will fail.
- **Concrete Recommended Next Step:** 
  1. Fix the `solve_field` argument count in `processor/build_flow_fields.py:1031`.
  2. Implement orthogonal corner blocking in `solve_field` (`processor/build_flow_fields.py:417-430`).
  3. Restore the `config` fixture and parameterization in `processor/tests/test_terrain_cost.py`.
  4. Restore import `from terrain_artifact import load_terrain_artifact` in `processor/tests/test_terrain_artifact.py`.
  5. Update `test_map_specific.js:232` status assertion from `OUT_OF_RANGE` to `UNREACHABLE` and wire it into `run-tests.js`.

### Risk 2: Android Build Pipeline Asset Bloat (10.52 GiB / 10,770 MB Copied to APK Assets)
- **Severity:** High
- **Evidence:** Both `build-android.bat` (line 22: `xcopy /E /I /Y processed_maps www\processed_maps`) and `build-android.sh` (line 77: `cp -r processed_maps www/`) execute unrestricted recursive copies of `processed_maps/`. `processed_maps/` now measures **11,293,286,499 bytes (10.52 GiB / 10,770.12 MiB / 11.29 GB decimal)** across 85 maps:
  - `.bin` files: **5,250.75 MB** (flow grids and terrain costs)
  - `.json` files: **5,161.73 MB** (race time matrices, gamelayers, and flow sidecars)
  - `.png` files: **237.66 MB** (minimap textures)
  - `.gz` files: **119.98 MB** (compressed heightmaps)
  The core mortar calculator only requires `.gz` (120 MB), `.png` (238 MB), and `metadata.json` (<1 MB).
- **Impact:** Running `build-android.bat` or `build-android.sh` copies over 10.5 GB into `www/` and syncs into `android/app/src/main/assets/public/`, causing Android Gradle packaging failure (`OutOfMemoryError` or `ZipException`) or an unusable multi-gigabyte APK.
- **Concrete Recommended Next Step:**
  1. Modify `build-android.bat` to exclude `flow/` and `terrain/`:
     ```cmd
     xcopy /E /I /Y processed_maps www\processed_maps /EXCLUDE:android_exclude_patterns.txt
     ```
     where `android_exclude_patterns.txt` contains `\flow\` and `\terrain\`.
  2. Modify `build-android.sh` with `rsync` or find-copy exclusions:
     ```bash
     rsync -av --exclude='flow/' --exclude='terrain/' processed_maps/ www/processed_maps/
     ```

### Risk 3: Massive Working Tree Drift, Untracked OpenSpec Directories, and Untracked Test Suite Dependency (`test_flow_dom.js`)
- **Severity:** High
- **Evidence:** 
  - `git status` shows 43 modified files (15,322 additions, 3,552 deletions = 18,874 changed lines), 6 untracked directories (`.agents/`, `add-shallow-water-wading/`, `add-terrain-traversability-model/`, `archive/2026-10-04-validate-bridge-crossing-connectivity/`, `overhaul-ui-swiss-style/`, `validate-bridge-crossing-connectivity/`), and 1 untracked file (`calculator/tests/test_flow_dom.js`), totaling 7 untracked entries on `feat/opening-flow-simulator`.
  - 5 directories under `openspec/changes/` are completely untracked in Git (4 active: `validate-bridge-crossing-connectivity/`, `add-terrain-traversability-model/`, `overhaul-ui-swiss-style/`, `add-shallow-water-wading/`; 1 archive: `archive/2026-10-04-validate-bridge-crossing-connectivity/`).
  - Tracked test runner `calculator/tests/run-tests.js` line 6 explicitly imports untracked file `calculator/tests/test_flow_dom.js`. Any clean clone or `git clean -fd` will immediately fail `npm test` with module-not-found.
- **Impact:** Extreme vulnerability to catastrophic data loss via accidental `git clean -fd`, merge conflicts, and immediate test failure on clean developer machines.
- **Concrete Recommended Next Step:**
  1. Immediately `git add calculator/tests/test_flow_dom.js` to ensure CI test runner does not break on clean clones.
  2. Stage and track all `openspec/changes/` directories in Git so task history and research artifacts are protected.
  3. Audit the 43 modified files against `add-opening-flow-simulator` scope.
  4. Revert unintentional deletions (such as the `config` fixture in `test_terrain_cost.py`).
  5. Commit validated components in atomic conventional commits.

### Risk 4: Stalled Bridge Traversability Pipeline (`validate-bridge-crossing-connectivity`)
- **Severity:** Medium
- **Evidence:** 23/23 tasks open in `tasks.md`. `TASK_RECORD.md` records blocked vision subagent dispatches during redo round 2 (`deepseek-v4.1-flash` without vision; `gpt-4.1` retry did not write files). Only 6 maps have `bridge_mask.bin`.
- **Impact:** Vehicle flow simulation on river maps (e.g. Carentan, Al Basrah, Krivaja Valley) either takes detour routes or uses unverified candidate meshes that may route across broken bridges or impassable banks.
- **Concrete Recommended Next Step:**
  1. Stop automated vision subagent dispatches until an environment with verified multimodal vision APIs is established.
  2. For the 6 critical bridge maps, complete manual or script-assisted bounding box validation into `handoff/bridges_consolidated.json`.
  3. Run `build_terrain_cost.py` and `build_flow_fields.py` only for those approved maps with explicit crossing records.

### Risk 5: Architectural and Documentation Drift in `AGENTS.md` and `requirements.txt`
- **Severity:** Medium
- **Evidence:** `AGENTS.md` does not describe flow simulation, `.json.gz` compression, JavaScript test commands (`npm test`), or the multi-file Python processor pipeline. `requirements.txt` is missing `numpy`, `pytest`, and `scipy`.
- **Impact:** Onboarding new developers or AI agents causes erroneous assumptions, missed dependencies, and broken tool execution.
- **Concrete Recommended Next Step:**
  1. Add `numpy>=1.24.0`, `pytest>=7.0.0`, and `scipy>=1.10.0` to `requirements.txt`.
  2. Update `AGENTS.md` to define the Flow Simulator subsystem, document `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, document all test suites (`npm test`, safe pytest, Flask server tests), and describe the current CLI processor pipeline.

---

## 5. Separation of Evidence

### 5.1 Observed Facts (Directly verified by command execution or file inspection)
- `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py` produced 90 passes, 4 failures, and 8 errors out of 102 collected tests (in 4.00s-8.55s).
- `npm test` produced 6 passed test suites (0 failures).
- `python -m pytest calculator/tests/test_server.py` produced 7 passes (0 failures).
- `node calculator/tests/bench.js` executed 1,000 iterations with full pipeline averaging 0.004 ms (<50 ms target).
- `node calculator/tests/test_map_specific.js` failed at line 135 on Vadso City with `AssertionError: Expected status OUT_OF_RANGE, got UNREACHABLE`.
- `calculator/tests/run-tests.js` line 6 imports `./test_flow_dom.js`, which is currently untracked in Git status.
- `mapsList.json` contains 85 map entries; `processed_maps/` contains 85 directories.
- `processed_maps/` disk consumption is **11,293,286,499 bytes (10.52 GiB binary / 10,770.12 MiB / 11.29 GB decimal)**, consisting of 5,250.75 MB in `.bin`, 5,161.73 MB in `.json`, 237.66 MB in `.png`, and 119.98 MB in `.gz`.
- Exactly 6 maps have `bridge_mask.bin` in `processed_maps/*/terrain/` (`albasrah_2`, `carentan`, `krivaja_valley`, `kunar_province`, `shijiavalley`, `tad_sae`).
- `git status` shows branch `feat/opening-flow-simulator` with 43 modified files (18,874 changed lines: +15,322 / -3,552), 6 untracked directories, and 1 untracked file (`calculator/tests/test_flow_dom.js`).
- `handoff/` is listed on line 37 of `.gitignore` (`.gitignore:37:handoff/`). As a consequence, `handoff/reports/CONDITION.md` is ignored by Git and does not appear in standard `git status` unless `--ignored` is supplied.
- 5 directories under `openspec/changes/` are untracked in Git (4 active proposals/records + 1 archive directory).
- `openspec validate --type change --no-interactive` passed for `add-opening-flow-simulator` and `overhaul-ui-swiss-style`, but failed for `validate-bridge-crossing-connectivity` (missing deltas in spec), `add-terrain-traversability-model` (missing specs/), and `add-shallow-water-wading` (missing specs/).
- In `openspec/changes/add-opening-flow-simulator/tasks.md`, there are 77 completed checklist items (`- [x]`) and 11 open checklist items (`- [ ]`) across 88 total tasks.
- In `openspec/changes/validate-bridge-crossing-connectivity/tasks.md`, there are 23 total checklist items, all 23 open (`- [ ]`).
- In `openspec/changes/overhaul-ui-swiss-style/tasks.md`, there are 25 total checklist items (including subtask 2.1a), all 25 open (`- [ ]`).
- `requirements.txt` does not list `numpy`, `pytest`, or `scipy`.
- Both `build-android.bat` and `build-android.sh` execute unrestricted recursive copies of `processed_maps/` without exclusions for `terrain/` or `flow/`.

### 5.2 Assumptions (Plausible deductions based on current code and history)
- The 8 fixture errors in `test_terrain_cost.py` arose when a test refactoring deleted lines 40-74 in `processor/tests/test_terrain_cost.py` without updating all parameterized test functions.
- `test_map_specific.js` was excluded from `run-tests.js` intentionally to prevent failing CI when the firing solution returned `UNREACHABLE` rather than `OUT_OF_RANGE` for extreme coordinates.
- The uncommitted 43-file diff has accumulated over multiple agent sessions due to explicit instructions in task records: "do not commit".

### 5.3 Unknowns (Unverified aspects outside current read-only evidence)
- Whether the Android APK compiles cleanly under Java 21 with the current Gradle setup, as no Android build was triggered (to avoid modifying `www/` or requiring local Android SDK/Java 21 setup).
- Whether in-game PR v1.9 mortar elevation tables match the calculated mils for maps with extreme height scales (e.g. Korengal, Kunar Province) beyond the single `test_bootcamp` vector in `test_in_game.js`.
- The exact timeline or resource availability for providing vision-capable model endpoints for the remaining 79 bridge maps.
- Behavior of `processor/tests/test_update_manifest.py`, which was intentionally omitted from execution per AGENTS.md safety guidelines.
