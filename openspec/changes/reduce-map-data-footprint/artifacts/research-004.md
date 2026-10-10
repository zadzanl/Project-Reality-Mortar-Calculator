# research-004 — reduce-map-data-footprint: current writers/loaders/tests on the dirty branch

- Change: `reduce-map-data-footprint` (approved)
- Task record: revision 1 (new record; no prior worklog in this checkout)
- Mode: READ-ONLY exploration. No source edited, no build/test executed for effect.
- Date: 2026-10-10
- Author: Explorer (research only)

## 0. TL;DR (what a junior dev must know first)

1. The working tree is **broken for regeneration**: `processor/build_terrain_cost.py` imports
   `terrain_generation_id` from `terrain_artifact.py`, but that function **does not exist**
   (`hasattr(terrain_artifact,'terrain_generation_id') == False`). `write_artifacts()` therefore
   raises `ImportError` at runtime. Nothing under `processed_maps/` can currently be regenerated.
2. The **phase-1 baseline harness is gone from the working tree**: `processor/baseline.py`,
   `processor/baseline_firing.mjs`, `processor/tests/test_baseline.py` were committed at HEAD
   (`0976b65`) and then **deleted in the working tree** (verified `Test-Path` = False). Only the
   captured data (`artifacts/baseline-pre-change.json`) and the pass report
   (`artifacts/compare-unchanged-report.json`) survive. The prior research/worklog
   (`research-001/002/003.md`, `task-record.md`, `impl-001.md`) are also deleted in the worktree.
3. **6 maps on disk are terrain format `1.1`** (with `bridge_mask.bin`) but the code only writes
   and reads `1.0`. `load_terrain_artifact('processed_maps/albasrah_2/terrain')` raises
   `ValueError: unsupported terrain artifact format`. So the on-disk artifacts are AHEAD of the code.
4. The design's size model is **partly wrong**: the real `.bin` whale is the **flow fields
   (uint8, ~3.71 GB)**, which are already quantized, not the terrain float32 grids (~1.40 GB).
   Quantization alone (D2) cannot reach the 3–4 GB target; **D3 (gzip `.bin`) is likely mandatory**,
   not optional. The single biggest win is still gzipping `obstructions.json` (5.10 GB).

---

## 1. Sources searched

### 1.1 Files read (working tree unless noted)
- `openspec/changes/reduce-map-data-footprint/{proposal,design,tasks}.md`, `.openspec.yaml`
- `openspec/changes/reduce-map-data-footprint/specs/{terrain-traversability,map-processor,map-artifact-regression}/spec.md`
- `openspec/changes/reduce-map-data-footprint/artifacts/compare-unchanged-report.json`
- `processor/extract_obstructions.py` (full)
- `processor/terrain_artifact.py` (full)
- `processor/build_terrain_cost.py` (header, `write_artifacts`, `process_map`, diffs)
- `processor/build_flow_fields.py` (header, `quantize_field`, `write_field`, `load_shipped_fields`, `process_map`, `_write_v2_field`, `process_map_v2` head, CLI)
- `processor/process_one_map.py`
- `processor/tests/test_obstruction_extraction.py`, `test_terrain_artifact.py`, `test_update_manifest.py` (+ def lists for `test_terrain_cost.py`, `test_flow_field.py`)
- `calculator/static/js/heightmap.js`, `calculator/static/js/flow/flow_core.js`, `calculator/static/js/app.js` (grep)
- `calculator/server.py` (routes)
- `build-android.bat`, `package.json`, `capacitor.config.json` (listed)
- `processed_maps/README.md`, `processor/README.md`, `mapsList.json`
- HEAD-only (via `git show`): `processor/baseline.py` (structure + header)

### 1.2 Searches run
- `Select-String` for: `format_version`, `bridge_mask`, `terrain_generation_id` across `processor/*.py`.
- `Select-String` for `terrain|obstruction` across `calculator/**` (js/html/py).
- `Select-String` for `obstructions.json` across non-bulk repo files.
- `Select-String` for `tofile|write_bytes|write_text|.bin|astype|gzip|def main|argparse` in the writers.
- `git grep -n` (`terrain_generation_id`) in HEAD and worktree; `git show HEAD:<path>`; `git diff --stat`; `git status --porcelain`.
- Filesystem listings/sizes only (no bulk reads): `processed_maps` grouped by extension and by filename.
- Read-only runtime probe: `import terrain_artifact` + `load_terrain_artifact` on adak/albasrah_2.

### 1.3 Explicitly NOT read
- No file contents from `processed_maps/` bulk data beyond small sidecars/`mapsList.json`. `obstructions.json` (up to 182.6 MB) and `.bin` grids were never opened — only listed/sized.

---

## 2. Environment fingerprint (verified)

| Tool | Version / value |
|---|---|
| OS | Windows |
| Python | 3.11.4 — `C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe` |
| NumPy | 1.26.4 |
| pytest | 8.3.5 |
| Node | v24.11.0 |
| git | 2.47.0.windows.2 |
| Branch | `feat/opening-flow-simulator` |
| HEAD | `0976b65` "test(processor): add map artifact baseline regression harness" |

Note: `calculator/__pycache__/server.cpython-314.pyc` exists, implying a Python 3.14 was used at some point, but the active interpreter is 3.11.4.

---

## 3. Git / dirty-tree state (Verified)

- `git diff --cached --stat` → **empty** (nothing staged).
- `git diff --stat` (unstaged, 52 files, +15327/−5546) includes, as **deletions**:
  - `processor/baseline.py` (−791)
  - `processor/baseline_firing.mjs` (−110)
  - `processor/tests/test_baseline.py` (−250)
  - `openspec/changes/reduce-map-data-footprint/artifacts/{research-001,research-002,research-003,task-record,impl-001}.md`
- `Test-Path` = **False** for `processor/baseline.py`, `processor/baseline_firing.mjs`, `processor/tests/test_baseline.py` → confirmed deleted from disk.
- `Test-Path` = **True** for `artifacts/baseline-pre-change.json` (2,447,993 bytes) and `artifacts/compare-unchanged-report.json`.
- `git show --stat HEAD` → HEAD (`0976b65`) ADDED the baseline harness + firing fixture + `test_baseline.py` + all change artifacts (research-001..003, task-record, impl-001). So the worktree **reverted phase 1** after it was committed.
- Working-tree modified (unstaged) source of interest: `processor/build_flow_fields.py`, `build_terrain_cost.py`, `extract_obstructions.py`, `extract_gamelayers.py`, `extract_vehicle_speeds.py`, `terrain_features.py`, `movement_params.json`, `terrain_params.json`, plus tests and many `processed_maps/*/metadata.json`.
- Untracked (new): `calculator/tests/test_flow_dom.js`, `openspec/changes/{add-shallow-water-wading,add-terrain-traversability-model,overhaul-ui-swiss-style,review-9th-oct-progress,validate-bridge-crossing-connectivity}/`.

**Risk flag:** the deletions above are *existing worktree edits*; the task said "preserve all existing edits", so they were left untouched.

---

## 4. Exact writers / loaders / callers (Verified, with line numbers)

Line numbers are from the **current working tree**.

### 4.1 Obstruction serialization — `processor/extract_obstructions.py`
- Output object built in `process_map()`: `output = {"map_name":..., "format_version": "1.0", "roads":..., "statics":..., "vegetation":..., "counts": {...}}` — **line 201**.
- `destination = OUT / name / "obstructions.json"` — **line 206**.
- `destination.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")` — **line 207**. ← this `indent=2` is the 5.10 GB whale.
- `main()` — **line 213**; `maps = sorted(... path.name not in EXCLUDED ...)` — **line 214**; `EXCLUDED = {"the_falklands"}` — **line 21**.
- **No CLI / argparse** in this file (processes all maps). This **contradicts AGENTS.md**, which claims `extract_obstructions.py` accepts optional map-name args.
- Unused-looking constants from the dirty change: `STATIC_OBJECTS_ARCHIVE`, `MAX_STATIC_TEMPLATE_BYTES`, `MAX_STATIC_TEMPLATE_EXPANSION` (defined ~lines 16–18; not referenced in the read bodies).
- Other functions: `parse_object_blocks` (returns `props` + `lines`), `classify`, `bf2_to_repo`, `parse_statics`, `parse_vegetation`, `scan_road_references`, `parse_roads`, `np_is_finite`, `read_member`.

**Obstruction readers (callers) — the only consumers:**
- `processor/build_terrain_cost.py`:
  - `obstructions_path = map_dir / "obstructions.json"` — **line 592**
  - `obstructions = json.loads(obstructions_path.read_text(encoding="utf-8"))` — **line 595**; `.get("roads"/"statics"/"vegetation")` — **596–598**.
  - provenance string `"obstructions": "processed_maps/%s/obstructions.json"` — **line 516**.
- `processor/render_obstruction_qa.py` — **line 31** `json.loads((directory / "obstructions.json").read_text(...))` (maintainer QA only).
- `processor/spike_material_map.py` — **lines 37, 297, 340** (a NO-GO material spike; not part of the normal pipeline).
- **No browser/JS reader.** No `obstructions` reference exists anywhere under `calculator/` (Verified by grep).

### 4.2 Terrain artifact format/loader — `processor/terrain_artifact.py` (unmodified vs HEAD)
- `BLOCKED = -1.0` — **line 16**.
- `load_terrain_artifact(path, profile="infantry")` — **line 19**.
- **Format gate:** `if sidecar.get("format_version") != "1.0" or sidecar.get("artifact") != "terrain_cost": raise ValueError("unsupported terrain artifact format")` — **line 21**. Only `"1.0"` accepted; **no 1.1/1.2 branch**.
- Nested `read_grid(filename, dtype)` — **line 37**; size-checks against `rows*cols*itemsize`; `np.fromfile(...).reshape(rows, cols)`.
- Grids read: `profile + "/cost.bin"` `<f4` (**55**), `classes.bin` `u1` (**56**), `road_mask.bin` `u1` (**57**), `water.bin` `u1` (**58**). **No `bridge_mask.bin`.**
- Diagnostics: requires `info["dtype"] == "<f4"` (**74–75**).
- **`terrain_generation_id` is NOT defined here** (verified by grep + `hasattr(...) == False`). Yet `build_terrain_cost.py` imports it.

### 4.3 Terrain writer — `processor/build_terrain_cost.py` (modified)
- Module docstring output layout: `terrain/sidecar.json`, `road_mask.bin`, `water.bin`, `<profile>/cost.bin`, `<profile>/classes.bin`, `<profile>/sidecar.json` — **lines 15–23**.
- `write_artifacts(...)` — **line 406**:
  - `(terrain_dir/"road_mask.bin").write_bytes(road_mask.astype(np.uint8).tobytes())` — **412**
  - `(terrain_dir/"water.bin").write_bytes(water_mask.astype(np.uint8).tobytes())` — **413**
  - diagnostics loop: `(terrain_dir/filename).write_bytes(array.astype("<f4").tobytes())`, `diagnostic_info[name] = {"file":..., "dtype":"<f4", ...}` — **416–420**
  - per profile: `cost.bin` `<f4` — **425**; `classes.bin` — **426**; `profile_sidecar` — **428–439**
  - `sidecar["format_version"] = "1.0"` — **451**
  - **NEW (dirty)** `from terrain_artifact import terrain_generation_id` — **522**; `sidecar["file_sha256"] = {...}` — **527–529**; `sidecar["generation_id"] = terrain_generation_id(sidecar)` — **530**; `json.dumps(sidecar, indent=2, allow_nan=False)` — **531–532**.
- `main()` — **line 641**; `names = sys.argv[1:]` — **642**; filters `path.is_dir() and path.name not in EXCLUDED` — **645**. Map-name scoping **works** here.
- **No `bridge_mask` is written anywhere** (grep empty across `processor/*.py`).

### 4.4 Flow artifact generation — `processor/build_flow_fields.py` (modified, largest diff)
- Imports `from terrain_artifact import load_terrain_artifact` — **line 50**.
- `quantize_field(field)` — **line 567**: float32 arrival seconds → uint8, `255 = unreachable`, `QUANT_CAP_S` cap, quantum = smallest whole-second step ≤254.
- `write_field(flow_dir, team, agent_class, field, ...)` — **line 584**:
  - `(team_dir/(agent_class+".bin")).write_bytes(quantized.tobytes())` — **589** (uint8)
  - sidecar `"format_version": "1.0"`, `"artifact": "flow_field"`, `"quantization": {"dtype":"u1", ...}` — **591–608**
  - `(team_dir/(agent_class+".json")).write_text(json.dumps(sidecar, indent=1) ...)` — **614**
- `race_times_document` — **619** (v1, `format_version "1.0"`); `write_race_times` — **644**; `class_keyed_race_document` — **651** (`format_version "2.0"`).
- v2 publish/validate: `publish_v2_generation` — **696**; `_validate_generation_manifest` — **763**; `validate_v2_generation` — **778**; `load_shipped_fields` — **793** (reads `.bin` as `np.uint8`, `data.reshape((rows,cols))` — **815–820**).
- `process_map` (v1) — **850** (loads `load_terrain_artifact(terrain_dir, profile=...)` per `CLASS_PROFILE` — **862**).
- `_write_v2_field` — **918**; sidecar `.update({"format_version":"2.0", "map":..., "layer":..., "build_id":..., "status":"available"})` — **925**.
- `process_map_v2` — **931**; requires `catalog["format_version"] == "2.0"` — **933–934**; loads `infantry` + `wheeled_vehicle` terrain — **938–939**; `terrain_hashes` from `terrain_dir.rglob("*")` — **940–941**.
- `main()` — **1069**; `argparse` `names` `nargs="*"` — **1072**; `--workers` — **1074**; `--race-times-only` — **1077**. Map-name scoping **works**.
- Flow `.bin` is **already uint8** (design D2 note confirmed).

### 4.5 Browser readers (no terrain, no obstructions)
- `calculator/static/js/heightmap.js`: `loadHeightmap` — **line 57**; tries `/maps/<map>/heightmap.json.gzip`, then `.gz`, then plain; `DecompressionStream('gzip')` — **line 109**; `pako` fallback — **119–125**.
- `calculator/static/js/flow/flow_core.js`: `flowUrls` — **231–238** (`/maps/<map>/flow/<layer>/team<team>/<cls>.bin|.json`); `loadLayerManifest` — **~261**; `loadV2LayerFields` — **~283**; validates `format_version === '2.0'` and manifest identity — **~291–300**.
- `calculator/static/js/app.js`: imports `loadMapData` (line 13) and flow overlay (line 14); **no** `terrain/` or `obstructions` fetch (Verified).
- **Answer to design Open Question #1: the browser does NOT load `terrain/*.bin` today** — only `heightmap.json(.gz)` + flow bins + rendered PNGs (minimap/contour). So the terrain format change (D2) affects **only Python consumers**; only flow/obstruction gzip (if served) touches JS.
- `calculator/server.py`: `serve_map_data` — **line 79**; special-cases `.json.gz` (mimetype `application/json`) — **133–141**; `/processed_maps/<map>/<file>` alias — **147**; path-traversal guarded.

### 4.6 Android / www packaging
- `build-android.bat` (Windows): `rmdir /s /q www`; `mkdir www`; `xcopy calculator\static → www\static`; `copy calculator\templates\index.html → www\`; `xcopy processed_maps → www\processed_maps`; `copy mapsList.json → www\`; rename every `*.gz` → `*.gzip` under `www\processed_maps`; then PowerShell path rewrites of **`www\index.html`, `www\static\js\app.js`, `www\static\js\heightmap.js` only**; `npm ci`; `npx cap sync android`; `gradlew.bat assembleDebug`.
- `capacitor.config.json` present; `package.json` scripts `test` (node `calculator/tests/run-tests.js`), `android:sync`, `android:build`, `android:run`.
- **Gap:** the path rewrite does **not** touch `www\static\js\flow\flow_core.js` (which builds `/maps/...` URLs). This is a pre-existing Android concern, not introduced by this change — flagged for verification.

### 4.7 Tests (anchors)
- `processor/tests/test_obstruction_extraction.py` (working tree): only parser tests (`test_parsers_transform_and_malformed_blocks`, `test_road_fixture_and_missing_mesh_are_skipped`). **No serialization test** — it does not assert `obstructions.json` shape.
- `processor/tests/test_terrain_artifact.py`: `test_loader_returns_flow_contract`, `test_loader_rejects_wrong_grid_length` (builds a `format_version "1.0"` fixture, writes `<f4` grids).
- `processor/tests/test_terrain_cost.py`: 11 tests incl. `test_compressed_pipeline_coverage_coarse_grid_and_repeatable_bytes` (line 174) and `test_raw_south_rows_reach_south_artifact_and_minimap` (223).
- `processor/tests/test_flow_field.py`: 30+ tests incl. `test_quantize_field_sentinel_and_monotonic` (109), `test_sample_quantized_arrival_uses_shipped_byte_value` (119), `test_v2_publication_switches_manifest_last_and_rejects_rewrite` (253).
- `processor/tests/test_update_manifest.py`: **must stay excluded** — it mutates `raw_map_data/manifest.json` at import time.
- `calculator/tests/run-tests.js`: runs 6 node suites (ballistics, coordinates, heightmap, integration, flow_overlay, **flow_dom** — the last is new/untracked).

---

## 5. Measured data facts (listings/sizes only — Verified)

`processed_maps/`: **85 map dirs** (matches `mapsList.json` count 85; **no orphan map dirs**).

| Class | Files | Size | Notes |
|---|---:|---:|---|
| `.bin` (all) | 9,114 | 5,250.8 MB | |
| `.json` (all) | 11,503 | 5,161.7 MB | |
| `.png` | 198 | 237.7 MB | minimap/contour — out of scope |
| `.gz` (heightmaps) | 85 | 120.0 MB | already gzipped — out of scope |

`.bin` by name (MB):
- flow (uint8): `infantry.bin` 1327.9, `truck_wheeled.bin` 501.1, `vehicles.bin` 473.1, `car.bin` 385.4, `helicopter.bin` 379.1, `tracked.bin` 338.9, `boat.bin` 308.1 → **≈ 3,713.6 MB total**.
- terrain float32: `cost.bin` 279.1 (170 files = 85 maps × 2 profiles); diagnostics `slope_deg_mean/max`, `edge_rise_m_max`, `edge_grade_max`, `static_multiplier`, `vegetation_dense`, `elevation_mean` each 139.6 (85 files) + `roughness_m_mean` 139.3 → **≈ 1,116.5 MB**; float32 grand total **≈ 1,395.6 MB**.
- terrain uint8: `classes.bin` 69.8 (170), `road_mask.bin` 34.9 (85), `water.bin` 34.9 (85), `bridge_mask.bin` **2.2 (6 files)**.

`.json` by name (MB): `obstructions.json` **5,098.1 (84 files, max 182.6 MB)**; `race_times.json` 21.3 (1,447); `gamelayers.json` 18.5 (84); `sidecar.json` 5.6 (255); remaining flow sidecars (`truck_wheeled/car/helicopter/infantry/tracked/boat/vehicles/manifest/class_manifest`) each ≤3.8 MB.

Per-map terrain layout (adak): `terrain/{7–8 diagnostics}.bin` (~4 MB each) + `road_mask.bin`/`water.bin` (1 MB) + `sidecar.json` (67 KB) + `terrain/{infantry,wheeled_vehicle}/{cost.bin(4MB),classes.bin(1MB),sidecar.json}`.

### 5.1 Format versions actually on disk (Verified)
- Terrain root `sidecar.json`: **79 maps `"1.0"`, 6 maps `"1.1"`**.
- The 6 v1.1 maps (each has `terrain/bridge_mask.bin`): **`albasrah_2`, `carentan`, `krivaja_valley`, `kunar_province`, `shijiavalley`, `tad_sae`** (sizes 262144 or 1048576).
- A second `"format_version"` line in each sidecar is nested inside `config.values` (i.e. `terrain_params.json`'s own version), not the artifact version — do not confuse them.
- **Runtime proof:** `load_terrain_artifact('processed_maps/adak/terrain')` → `LOADED (1024,1024)`; `load_terrain_artifact('processed_maps/albasrah_2/terrain')` → `ValueError: unsupported terrain artifact format`.

### 5.2 Flow layout + orphan surface (Verified)
- Per layer: `flow/<mode>_<size>/{class_manifest.json, race_times.json, team1/, team2/, generations/}`.
- `class_manifest.json` (v2) points at `generations/<build_id>` (adak `gpm_coop_128` → `generations/v2-adak-gpm_coop_128-ead53db14565`).
- `generations/` roots = **737**; total generation dirs = **892** → **≈155 stale generation dirs** (candidates for cleanup, task 5.1).
- Legacy v1 flow bins under `flow/<layer>/team{1,2}/` = **2,062** files (the rest of the 7,919 flow bins live under `generations/`).
- No map folder is absent from `mapsList.json` (no orphan *maps*; orphans are *artifacts*).

---

## 6. Worklog (chronological)

1. Enumerated the change dir; read proposal/design/tasks/specs and `compare-unchanged-report.json`.
2. `git status` / `git log` / `git diff --stat`; discovered HEAD added the harness and the worktree deleted it.
3. `Test-Path` confirmed `baseline.py`, `baseline_firing.mjs`, `test_baseline.py` are gone from disk.
4. Read `extract_obstructions.py` + `terrain_artifact.py` in full → found `indent=2` writer and the 1.0-only loader.
5. Grepped `format_version` / `bridge_mask` / `terrain_generation_id` → no `bridge_mask` in code; `terrain_generation_id` imported but undefined.
6. Read `build_terrain_cost.write_artifacts` + diff → confirmed new `file_sha256`/`generation_id` block and the missing symbol.
7. Mapped `build_flow_fields` functions; read `quantize_field`, `write_field`, `load_shipped_fields`, v2 paths, CLI.
8. Grepped `calculator/**` → browser loads heightmaps + flow only; no terrain/obstructions.
9. Read `server.py` routes, `build-android.bat`, `package.json`, `run-tests.js`.
10. Measured `processed_maps` by extension and filename; found flow uint8 ≈3.71 GB vs terrain float32 ≈1.40 GB.
11. Enumerated terrain `format_version` per map → 6× `1.1`; ran read-only loader probe (adak OK, albasrah_2 fails).
12. Measured flow generations (892 dirs) and legacy v1 flow bins (2,062); compared `mapsList.json` (85) vs dirs (85).
13. Read `git show HEAD:processor/baseline.py` header/structure to describe the committed harness.

---

## 7. Unknowns

- **FIND:** Are the 6 v1.1 maps' flow artifacts current (generated from 1.1 terrain) or stale? (Their flow sidecars reference a build_id; whether that build used bridge masks is unknown.)
- **FIND:** Actual compressed size of `obstructions.json.gz` on the worst map (`fields_of_kassel`, 182.6 MB) — the ≥5x claim is not yet measured in this checkout.
- **FIND:** Whether `node` can import the ballistics module for a firing fixture. `baseline_firing.mjs` existed at HEAD, which suggests yes, but it was not executed here.
- **ASK:** Should the deleted phase-1 harness (`baseline.py`, `baseline_firing.mjs`, `test_baseline.py`) be **restored from HEAD** (`git checkout 0976b65 -- …`) or re-implemented? Same question for the deleted `research-001..003`, `task-record.md`, `impl-001.md`.
- **ASK:** Is the `generation_id`/`file_sha256` feature (and thus the missing `terrain_generation_id`) still wanted, or should it be dropped?
- **FIND:** Whether the intended artifact-version bump target is `1.2` (design) while 6 maps already sit at `1.1` — i.e. does 1.2 need to also define `bridge_mask` handling, or is `1.1`+`bridge_mask` a separate in-flight change?
- **FIND:** Whether `www/static/js/flow/flow_core.js` `/maps/...` paths break under Android (the build script does not rewrite that file).

---

## 8. Risks (ranked)

1. **HIGH — regeneration is impossible as-is.** `build_terrain_cost.write_artifacts` raises
   `ImportError: cannot import name 'terrain_generation_id'` (missing from `terrain_artifact.py`).
   Any "regenerate then compare" step fails before writing artifacts.
2. **HIGH — 6 maps are unreadable by the current loader.** Format gate accepts only `"1.0"`;
   `albasrah_2` (1.1) fails. `build_flow_fields` therefore cannot regenerate flow for those 6 maps.
   The 1.2 work must (re)introduce `bridge_mask.bin` + 1.1/1.2 decode paths.
3. **HIGH — phase-1 harness absent.** Capture/compare code was deleted from the worktree; only the
   baseline JSON survives. The change cannot verify equivalence until the harness is restored/rewritten.
4. **MEDIUM — design size model mis-scoped.** `.bin` is dominated by **flow uint8 (3.71 GB)**, already
   quantized; terrain float32 (1.40 GB) is the only `.bin` class quantization can shrink. Post-D1+D2
   estimate: obstructions ≈1 GB + flow 3.7 GB + terrain ≈0.5 GB + png 0.24 + gz 0.12 ≈ **5.5 GB**,
   which **misses the 3–4 GB target** → **D3 (gzip `.bin`) is likely required**, not optional.
5. **MEDIUM — no map scoping in `extract_obstructions.py`.** Per-map regeneration (task 4.1) needs
   this file to accept map-name args (AGENTS.md already documents that behavior, but the code lacks it).
6. **MEDIUM — gzip `.gz` + Android aapt.** Heightmaps already need a `.gz → .gzip` rename in the build
   script. Any new `.gz` artifact (obstructions/flow) must either be handled the same way or be
   decoded by `DecompressionStream` from a served (non-renamed) path; `server.py` currently special-cases
   only `*.json.gz`.
7. **LOW — stale data inflates every measurement.** 892 flow generation dirs (~155 stale) + 2,062 legacy
   v1 flow bins mean footprint work should include the cleanup pass or the target will be judged wrong.
8. **LOW — docs drift.** `processor/README.md` (lines 251, 284 show `format_version "1.0"`) and
   `processed_maps/README.md` (line 3, 34–40) describe current formats and will need updating (task 5.3).

---

## 9. Recommended bounded phase order

Ordered so each phase is independently runnable, verifiable, and reversible. Phases 0 and 1 are
prerequisites; later phases are gated on measurement.

- **Phase 0 — restore + repair (blocking).**
  Restore `processor/baseline.py`, `processor/baseline_firing.mjs`, `processor/tests/test_baseline.py`
  from `0976b65` (or re-implement), and supply/remove the missing `terrain_generation_id` so
  `build_terrain_cost.write_artifacts` imports cleanly. Add a loader branch for terrain `1.1`
  (and `bridge_mask.bin`) so the 6 on-disk maps load. Verification: safe pytest run
  `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`, plus a
  read-only load of one 1.0 map (adak) and one 1.1 map (albasrah_2). *No format change yet.*
- **Phase 1 — obstructions compaction + gzip (biggest, most isolated win).**
  `extract_obstructions.py` → `obstructions.json.gz`, `separators=(",", ":")`, coords rounded 0.1 m;
  update the three Python readers (`build_terrain_cost.py` 592–598, `render_obstruction_qa.py` 31,
  `spike_material_map.py` 37/297/340). Measure on `fields_of_kassel` (182.6 MB) before rollout.
  Expected ≈5.10 GB → ≈1 GB. No browser change needed (nothing in `calculator/` reads it).
- **Phase 2 — terrain quantization (format 1.2) + multi-version loader.**
  `build_terrain_cost.write_artifacts` writes uint16 for thresholded grids / uint8 for diagnostics with
  per-grid `{dtype, offset, scale}`; loader dequantizes `offset + q*scale`, exact sentinels; keep
  1.0/1.1/1.2. Expected ≈1.40 GB float32 → ≈0.4 GB. Python-only consumers.
- **Phase 3 — measure, then decide D3 (gzip `.bin`).**
  If `processed_maps/` is still >3–4 GB (very likely per §8.4), gzip flow + terrain `.bin` and decode in
  the browser via `DecompressionStream('gzip')` (pattern already proven in `heightmap.js` 109–125).
  This is the only lever that can compress the 3.71 GB flow set.
- **Phase 4 — regenerate per map (needs map scoping in `extract_obstructions.py`), compare, cleanup, resync.**
  Baseline compare; delete stale flow generations (~155) and legacy v1 flow bins (2,062) and superseded
  `obstructions.json`; rebuild `www/` via `build-android.bat`; `npx cap sync android`; smoke-test one map;
  update `AGENTS.md`, `processor/README.md`, `processed_maps/README.md`.

Rationale for the order: Phase 1 alone is the majority of the win and touches the fewest, most
isolated call sites; Phase 2 is Python-only and low-risk; Phase 3 is the measured gate for the stated
target; Phase 4 must come last so orphan cleanup and the Android resync happen against final formats.

---

## 10. Verification record (commands actually run)

Read-only only. No source file was created/modified except this research document.

```
# git / tree state
git status --short
git status --porcelain=v1
git branch --show-current
git log --oneline -8
git show --stat HEAD
git diff --stat
git diff --cached --stat
git diff -- processor/build_terrain_cost.py
git diff -- processor/extract_obstructions.py
git diff -- README.md
git diff -- calculator/static/js/app.js
git grep -n "terrain_generation_id" HEAD
git grep -n "terrain_generation_id"
Test-Path processor\baseline.py ; processor\baseline_firing.mjs ; processor\tests\test_baseline.py   # all False

# source / symbol search
Select-String -Path "processor\*.py" -Pattern "format_version"
Select-String -Path "processor\*.py" -Pattern "bridge_mask"                       # (empty)
Select-String -Path "processor\build_terrain_cost.py" -Pattern "format_version|bridge_mask|tofile|..."
Select-String -Path "processor\build_flow_fields.py" -Pattern "^def |tofile|write_bytes|..."
Select-String -Path "calculator\static\js\*.js","calculator\static\js\flow\*.js" -Pattern "terrain|obstruction|..."
Select-String -Path "calculator\server.py" -Pattern "route|send_from_directory|gzip|..."

# data (listings/sizes only)
Get-ChildItem processed_maps -Recurse -File | Group-Object Extension | ...          # sizes by ext
Get-ChildItem processed_maps -Recurse -File -Filter *.bin | Group-Object Name | ... # sizes by name
Get-ChildItem processed_maps -Recurse -File -Filter bridge_mask.bin                 # 6 files
Get-ChildItem processed_maps -Directory | ... sidecar.json format_version ...        # 79×1.0, 6×1.1
Get-ChildItem processed_maps -Recurse -Directory -Filter generations                # 737 roots / 892 dirs
(Get-ChildItem processed_maps -Recurse -File -Filter *.bin | ? FullName -match '\\flow\\[^\\]+\\team[12]\\').Count  # 2062

# read-only runtime probe (no writes)
python -c "import sys; sys.path.insert(0,'processor'); import terrain_artifact as t; print(hasattr(t,'terrain_generation_id'))"
python -c "... load_terrain_artifact('processed_maps/adak/terrain') ..."            # LOADED (1024,1024)
python -c "... load_terrain_artifact('processed_maps/albasrah_2/terrain') ..."      # ValueError unsupported terrain artifact format

# environment fingerprint
python --version            # 3.11.4
python -c "import numpy; print(numpy.__version__)"   # 1.26.4
python -c "import pytest; print(pytest.__version__)" # 8.3.5
node --version              # v24.11.0
git --version               # 2.47.0.windows.2
```

**Not verified / not run:** no regeneration, no `build_terrain_cost.py`/`build_flow_fields.py`
execution, no pytest run (deliberately — read-only task), no `build-android.bat`, no browser smoke test,
no `fields_of_kassel` compression measurement.
