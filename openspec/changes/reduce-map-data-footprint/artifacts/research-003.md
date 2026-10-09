# research-003 — Test + Tooling Reconnaissance for `reduce-map-data-footprint`

Read-only reconnaissance. No files were modified (except this artifact). No subagents dispatched.

## Environment fingerprint

| Item | Value |
|---|---|
| Date | 2026-10-09 |
| OS | Windows |
| Repo | `C:\Projects\Project_Reality-Mortar-Calculator` |
| Branch | `feat/opening-flow-simulator` |
| HEAD commit | `f6ba143` |
| Working tree | **DIRTY** (in-flight `add-opening-flow-simulator`; see §7) |
| Python | 3.11.4 |
| NumPy | 1.26.4 |
| Node | v24.11.0 |
| pytest config | none (`pytest.ini`/`setup.cfg`/`pyproject.toml` absent) |
| conftest.py | **none anywhere** (`python -c "glob.glob('**/conftest.py', recursive=True)"` → `[]`; `dir /s /b conftest.py` → nothing) |

---

## Q1 — Test layout and breakage surface

`processor/tests/` (13 test modules, no conftest, no `__init__.py`; `git ls-files` confirms no `processor/__init__.py` or `processor/tests/__init__.py`):

```
test_contour_generation.py      test_gamelayer_extraction.py  test_minimap_extraction.py   test_terrain_artifact.py
test_flow_field.py              test_mapinfo.py               test_obstruction_extraction.py  test_terrain_cost.py
test_functions.py               test_material_table.py        test_terrain_features.py     test_update_manifest.py
                                                              test_vehicle_speeds.py
```

### Import pattern (uniform)

Every test adds `processor/` to `sys.path` and then imports the script by bare module name:

```python
sys.path.insert(0, str(Path(__file__).parents[1]))
import extract_obstructions as extractor
from extract_obstructions import (bf2_to_repo, classify, parse_roads, parse_statics, parse_vegetation)
```
— `processor/tests/test_obstruction_extraction.py:8-10`

Other examples:
- `processor/tests/test_terrain_cost.py:10-14` → `from build_terrain_cost import (...)`, `import build_terrain_cost as terrain`, `from terrain_features import compute_features`
- `processor/tests/test_flow_field.py:11-13` → `import build_flow_fields as bff` + long `from build_flow_fields import (...)`
- `processor/tests/test_terrain_artifact.py:9` → path insert only (the import is **missing** in the worktree — see §7)
- `processor/tests/test_minimap_extraction.py:11` → `str(Path(__file__).parent.parent)` (equivalent form)
- `processor/tests/test_vehicle_speeds.py:8` → `from processor.extract_vehicle_speeds import (...)` — **package-style import**, needs repo root on `sys.path` and relies on namespace-package resolution (no `__init__.py`).

Because there is no conftest, each test file is self-contained; the only shared setup is the `sys.path.insert` line.

### Per-file characterization (the four named files)

| Test file | Fixtures | Data source | Breakage surface under a serialization change |
|---|---|---|---|
| `test_obstruction_extraction.py` | none | **Synthetic only.** Inline `.con` text blocks + `FakeClient` dict-backed zip stub (lines 12-16, 25-58). | Exercises the *parsers* (`parse_statics`, `parse_vegetation`, `parse_roads`) and asserts in-memory record fields (`class`, `x`, `y`, `rotation_deg`). It never reads/writes `obstructions.json`. A **write-side** serialization change alone does not touch it; a **record-shape** change (keys/units in the parser output) does. |
| `test_terrain_artifact.py` | none (`tmp_path`) | **Synthetic.** Writes `sidecar.json` + `.bin` files with NumPy, then calls `load_terrain_artifact`. | This is the **serialization contract test**. It hard-codes `format_version:"1.0"`, `artifact:"terrain_cost"`, `grid` keys (`rows/cols/cell_size_m/origin`), byte-length validation (`ValueError "expected 16 bytes"`), dtypes (`<f4`, `u1`), and `blocked_sentinel:-1.0`. Any change to sidecar schema or `.bin` layout/dtype **will** break it. (Also currently broken — §7.) |
| `test_terrain_cost.py` | `config` fixture + `@pytest.mark.parametrize("geometry"...)`/`("height,blocked"...)` in **HEAD** (lines 48-74) | **Synthetic.** `tmp_path` + `monkeypatch` of `terrain.RAW/OUT/CONFIG_PATH`; writes `heightmap.json.gz`, `metadata.json`, `obstructions.json`, `minimap.png`. | Asserts the full terrain artifact: exact `terrain/` file set, sidecar `diagnostics` key set, `grid` keys (`source_spacing_m`, `degraded_source_resolution`, `heightmap_orientation`), `.bin` bytes (`<f4`, `u1`), and **byte-for-byte determinism** (runs `process_map` twice, `second == first`). A serialization change to terrain artifacts breaks multiple tests here. (Also currently broken — §7.) |
| `test_flow_field.py` | none (local helpers) | **Synthetic.** `flat_costs()` NumPy arrays; several tests write flow artifacts to `tmp_path`. | Covers field solve + **v2 publication**: `write_field`, `publish_v2_generation`, `validate_v2_generation`, `class_keyed_race_document`, `v2_build_id`. A change to flow `.bin` format, `manifest.json` pointer ordering, or `class_manifest` breaks these. The dirty tree adds ~177 lines / 12 new tests here (§7). |

`test_terrain_cost.py` also does a **function-local** import of the loader inside one test: `from terrain_artifact import load_terrain_artifact` (`test_terrain_cost.py:229` region, inside `test_raw_south_rows_reach_south_artifact_and_minimap`). This is the pattern that `test_terrain_artifact.py` is currently *missing*.

---

## Q2 — Why `test_update_manifest.py` must be excluded

Confirmed by reading `processor/tests/test_update_manifest.py:1-14`:

```python
import json
from pathlib import Path

p = Path('..') / 'raw_map_data' / 'manifest.json'
manifest = json.loads(p.read_text())
for m in manifest['maps']:
    if m['name'] == 'adak':
        print('Original md5:', m['md5'])
        m['md5'] = 'deadbeefdeadbeefdeadbeefdeadbeef'
        break
p.write_text(json.dumps(manifest, indent=2))
print('Manifest updated')
```

- It is **module-level code with no test functions**. pytest imports every `test_*.py` at collection, so this runs (and writes) on **import**, before any test executes.
- It **clobbers `adak`'s `md5`** in the real `raw_map_data/manifest.json` with the sentinel `deadbeef...` (and rewrites the file with `indent=2`).
- The path is **CWD-dependent** (`Path('..')`): run from repo root, `..` = `C:\Projects` and the file is absent → `FileNotFoundError` (a collection error); run from `processor/`, it resolves to the real manifest and performs the destructive write.
- AGENTS.md documents the exclusion; safe command: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`.

---

## Q3 — Node feasibility for a firing-solution baseline: **YES** (no shim needed)

`calculator/static/js/ballistics.js` is a **pure ES module**:

- Export pattern: `export const PR_PHYSICS = Object.freeze({...})` (`ballistics.js:23`); `export function calculateDistance(...)` (`:56`), `calculateAzimuth` (`:81`), `calculateElevationAngle` (`:123`), `radiansToMils` (`:176`), `radiansToDegrees` (`:190`), `milsToDegrees` (`:204`), `calculateTimeOfFlight` (`:227`), `validateFiringSolution` (`:298`), `calculateFiringSolution` (`:397`).
- **No browser-only APIs**: grep for `window.|document.|fetch(|localStorage|navigator.|XMLHttpRequest` returned **zero** matches. All functions are pure (`calculateFiringSolution` returns a plain object).
- `package.json` declares `"type": "module"` and `"scripts": {"test": "node calculator/tests/run-tests.js"}`.

It is **already imported headlessly** by the existing Node test harness:
- `calculator/tests/test_ballistics.js:4-14` → `import { calculateDistance, ..., calculateFiringSolution, PR_PHYSICS } from '../static/js/ballistics.js';`
- `calculator/tests/run-tests.js:1` → `import { runBallisticsTests } from './test_ballistics.js';` (run via `npm test`).

Even stronger — a firing-solution fixture harness **already exists**:
- `calculator/tests/test_integration.js:8-15` imports `ballistics.js`, `coordinates.js`, and `heightmap.js` (`bilinearInterpolation`, `worldToPixel`), then loads **real** `processed_maps/test_bootcamp` data (`heightmap.json.gz` via `gunzipSync` + `JSON.parse` + `Uint16Array`) and computes firing solutions (`test_integration.js:24-44, 96-160`).
- `calculator/tests/test_in_game.js:1-8, 60-150` loads the same real map data and compares results against `calculator/tests/in_game_vectors.json`.
- `calculator/tests/in_game_vectors.json` currently holds one vector: `mapName:"test_bootcamp"`, `mortarGridRef:"D6-5"`, `targetGridRef:"F8-5"`, `expectedDistance:891.17`, `expectedAzimuth:135.0`, `expectedElevationMils:1272.82`, tolerances `{distance:10, azimuth:2, elevationMils:1}`.
- `calculator/tests/test_in_game.md` states this harness is "intentionally **not** included in the default `npm test` run" (it is manual-input validation).

**Verdict: YES** — node v24.11.0 can `import` and eval `ballistics.js` directly and compute a firing solution headlessly; an ESM import path and a real-data integration fixture already exist in-repo. (Verdict is from static evidence + existing harness code; no test was executed, per read-only constraint.)

Note for the change: the planned `processor/baseline.py` (stdlib + NumPy) is a Python-side baseline; the JS side already has `test_in_game.js` + `in_game_vectors.json` doing the equivalent firing-solution regression.

---

## Q4 — Deterministic map enumeration + 5 largest `obstructions.json`

Two enumeration sources (both small JSON / directory listings only):

1. **Repo-root `mapsList.json`** — `{"count": 85, "maps":[{"name":"adak","path":"adak"}, ...]}` (7,983 bytes). Generated by `processor/generate_maps_list.py`, which scans `processed_maps/*/` for `metadata.json`, sorts by name, and writes the Flask `/maps/list` schema.
2. **`raw_map_data/manifest.json`** (45,543 bytes) — top-level keys `maps, total_maps, maps_with_minimaps, maps_heightmap_only, total_size_bytes, total_size_mb, collection_date, format_version`; `maps` has **84** entries, each with `name`, `server_zip{md5,size_bytes,has_heightmap}`, `client_zip{md5,size_bytes,has_minimap}`, `collected_at`, `source_path`, `status`.

Directory counts (listing only, no bulk read):

| Predicate | Count |
|---|---|
| `processed_maps/` directories | 85 |
| … with `metadata.json` | 85 |
| … with `heightmap.json.gz` | 85 |
| … with `obstructions.json` | **84** |
| … with `gamelayers.json` | 84 |

The single map with `metadata.json`/`heightmap.json.gz` but **no** `obstructions.json` and **no** `gamelayers.json`: **`andromeda`**. (This explains mapsList=85 vs raw manifest=84 vs obstructions=84; `the_falklands` is excluded by `EXCLUDED` in the scripts.)

**5 largest `obstructions.json` by directory listing `Length`** (never opened):

| Rank | Map | Bytes | MB |
|---|---|---|---|
| 1 | `fields_of_kassel` | 191,505,130 | 182.63 |
| 2 | `ascheberg` | 181,329,799 | 172.93 |
| 3 | `korbach_offensive` | 177,806,485 | 169.57 |
| 4 | `road_to_damascus` | 174,351,320 | 166.27 |
| 5 | `shijiavalley` | 156,098,852 | 148.87 |

Reproduction (safe — size only):
```powershell
Get-ChildItem "processed_maps" -Directory | ForEach-Object {
  $f = Join-Path $_.FullName 'obstructions.json'
  if (Test-Path $f) { [PSCustomObject]@{ Map=$_.Name; Bytes=(Get-Item $f).Length } }
} | Sort-Object Bytes -Descending | Select-Object -First 5
```

---

## Q5 — NumPy availability

```
python --version           -> Python 3.11.4
python -c "import numpy; print(numpy.__version__)"  -> 1.26.4
numpy.__file__             -> C:\Users\lenovo\AppData\Local\Programs\Python\Python311\Lib\site-packages\numpy\__init__.py
sys.executable             -> C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe
```

- `requirements.txt` (repo root, 87 bytes) contains only: `Flask==3.1.3`, `Werkzeug==3.1.6`, `Pillow>=10.0.0`, `pyinstaller>=6.0.0`, `jaraco.text>=3.8.0`. **NumPy is NOT declared** — it is a global/system-site install.
- **No virtualenv** in the repo (`venv`, `.venv`, `env` — none found). All processor tests import NumPy from the global interpreter.

---

## Q6 — How processor scripts are invoked per-map today

| Script | CLI surface | Source |
|---|---|---|
| `processor/extract_obstructions.py` | **No map-name CLI args in the current worktree.** `main()` iterates all `RAW` dirs that contain `server.zip`, skipping `EXCLUDED = {"the_falklands"}`. | `main()` at `extract_obstructions.py:213-222`; `EXCLUDED` at `:16`; `if __name__ == "__main__": sys.exit(main())` at `:225`. It also imports `bf2_road_mesh` (`:11`) and reads `raw_game_data/objects_statics_server.zip` (`STATIC_OBJECTS_ARCHIVE`, `:18`). |
| `processor/build_terrain_cost.py` | Positional map names: `names = sys.argv[1:]`; empty ⇒ all `OUT` dirs with `heightmap.json.gz`/`heightmap.json`, minus `EXCLUDED`. | `build_terrain_cost.py:641-645`; `EXCLUDED` at `:46`. |
| `processor/build_flow_fields.py` | `argparse`: `names` (`nargs="*"`), `--workers N`, `--race-times-only`; empty ⇒ all `OUT` dirs with `gamelayers.json`. | `build_flow_fields.py:1069-1080`. |

**Discrepancy to flag:** AGENTS.md claims "`extract_obstructions.py` accepts optional map-name arguments to scope processing (`python processor/extract_obstructions.py carentan`)". The observed worktree code **ignores `sys.argv`** and always processes all maps. Either AGENTS.md is stale/aspirational or the arg support was reverted in the dirty tree.

---

## §7 — CRITICAL: dirty worktree has two broken Python test files

`git status --short` shows the tree is dirty (branch `feat/opening-flow-simulator`, commit `f6ba143`). Among modified files: `processor/tests/test_terrain_artifact.py`, `processor/tests/test_terrain_cost.py`, `processor/tests/test_flow_field.py`, `processor/tests/test_obstruction_extraction.py`, `processor/tests/test_vehicle_speeds.py`, `processor/tests/test_gamelayer_extraction.py`.

`git diff --stat -- processor/tests/`:
```
processor/tests/test_flow_field.py             | 177 ++++++++++++++++++++++++-
processor/tests/test_vehicle_speeds.py         |  45 ++++++-
processor/tests/test_obstruction_extraction.py |   8 +-
processor/tests/test_terrain_artifact.py       |   2 +-
processor/tests/test_terrain_cost.py           |  35 -----
processor/tests/test_gamelayer_extraction.py   |   6 +
```

Two of the four named test files are **currently broken in the worktree**:

1. **`processor/tests/test_terrain_artifact.py`** — HEAD had `from terrain_artifact import load_terrain_artifact`; the worktree **deleted it** (and added `import hashlib`). Both tests call `load_terrain_artifact(root)` with no import → `NameError`.
   ```
   -from terrain_artifact import load_terrain_artifact
   ```
2. **`processor/tests/test_terrain_cost.py`** — the worktree **deleted 35 lines**: `test_confirmed_and_candidate_water_semantics`, the `config` **fixture** (HEAD `:48-71`), and the two `@pytest.mark.parametrize` decorators (HEAD `:73-74`). `test_step_and_ridge_hazards_survive_aggregation_and_roads(config, geometry, height, blocked)` now has four unresolved params and no fixture → pytest error `fixture 'config' not found`.

Consequence: **a baseline `pytest processor/tests/` run today would not be green**, independent of the `reduce-map-data-footprint` change. This is a fact about the current dirty state, not a claim about the change.

The other diffs appear additive (not obviously broken): `test_obstruction_extraction.py` adds imports (`json`, `zipfile`, `numpy`, `import extract_obstructions as extractor`); `test_flow_field.py` adds ~12 tests; `test_vehicle_speeds.py` +45 lines; `test_gamelayer_extraction.py` +6 assertions.

---

## Worklog (searches, probes, dead ends)

- Listed `processor/tests/` and `processor/` (dir listings only).
- Read `test_obstruction_extraction.py`, `test_terrain_artifact.py`, `test_update_manifest.py`, `test_terrain_cost.py` (full), `test_flow_field.py` (head).
- Read `ballistics.js` (full), `package.json`, `index.html` script tags, `app.js` imports.
- Grepped `ballistics.js` for browser APIs (empty) and `export` lines.
- Found and read `calculator/tests/` harness: `run-tests.js`, `test_ballistics.js`, `test_integration.js`, `test_in_game.js`, `in_game_vectors.json`, `test_in_game.md`.
- Listed `raw_map_data/` and `processed_maps/`; read `raw_map_data/manifest.json` (84 maps) and repo-root `mapsList.json` (85); read `processed_maps/README.md`, `CANONICAL_MAPS.txt`, `reduce_size.bat`, `generate_maps_list.py`.
- Enumerated `obstructions.json` by `Length` only (never opened); reconciled 85 dirs / 85 metadata / 84 obstructions (missing: `andromeda`).
- Read CLI surfaces of `extract_obstructions.py`, `build_terrain_cost.py`, `build_flow_fields.py`.
- **Dead end:** initial `Get-ChildItem -Path processor -Recurse -Filter conftest.py` and `cmd /c dir /s /b conftest.py` returned nothing; confirmed no conftest via `python -c "glob.glob(...)"` → `[]`. This exposed that `test_terrain_cost.py`'s fixtures must live in-file (they do, in HEAD).
- **Dead end:** two terminal invocations produced interleaved/leftover output (a `processed_maps\test_bootcamp` listing appeared under a `calculator/tests` command). Re-ran all affected probes with explicit `===MARKER===` separators to get clean results.
- `python -c "import numpy; ..."` → 1.26.4. Node → v24.11.0.
- No test/bench command was executed (read-only constraint); node-loadability is inferred from static ESM evidence plus the pre-existing headless harness.

## Unknowns

- Whether the two broken test files (§7) are intentional mid-edit or an accidental regression — cannot determine without the change owner.
- Whether `andromeda` is intentionally heightmap-only (no `obstructions.json`/`gamelayers.json`).
- Full reconciliation of `mapsList.json` count 85 vs raw manifest 84 is inferred (andromeda), not proven from the raw manifest (which was not searched for `andromeda`).
- Whether `extract_obstructions.py` is supposed to regain per-map CLI args (AGENTS.md says yes; code says no).
- No fresh execution of `node calculator/tests/run-tests.js` (would confirm runtime, but is a test command).

## Risks

1. **OOM trap (high):** `obstructions.json` reaches **191 MB** (`fields_of_kassel`); the five largest are all >148 MB. Any harness must use directory-listing `Length` only — never open these files.
2. **Baseline confound (high):** the dirty tree already fails `test_terrain_artifact.py` and `test_terrain_cost.py`; a "baseline" green run cannot be assumed. Any baseline harness must pin the pre-change state or explicitly account for these failures.
3. **Duplicate effort (medium):** `calculator/tests/in_game_vectors.json` + `test_in_game.js` already implement a firing-solution regression against real `processed_maps` data; a new `processor/baseline.py` may overlap.
4. **Undeclared dependency (medium):** `baseline.py` "stdlib + NumPy only", but NumPy is absent from `requirements.txt` and there is no venv — reproducibility depends on the global interpreter.
5. **Destructive test (medium):** `test_update_manifest.py` writes `raw_map_data/manifest.json` on import; must stay excluded and CWD-controlled.
6. **Doc/code drift (low):** AGENTS.md's `extract_obstructions.py <map>` CLI claim does not match the code.
