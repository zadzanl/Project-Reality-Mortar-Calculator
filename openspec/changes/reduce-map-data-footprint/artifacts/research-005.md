# research-005 — Recoverability, artifact layout, and baseline scope for `reduce-map-data-footprint`

- **Change:** `openspec/changes/reduce-map-data-footprint` (OpenSpec change; active, not archived)
- **Task record revision:** 1 (new record; no prior worklog exists in the current checkout — the prior `artifacts/task-record.md` is deleted from the working tree; see §1)
- **Mode:** READ-ONLY investigation. No project source or generated map was created, modified, or deleted. No git state was reset, staged, or cleaned. No subagents dispatched. The only file written is this document.
- **Date:** 2026-10-10
- **Repo:** `C:\Projects\Project_Reality-Mortar-Calculator`
- **Branch / HEAD:** `feat/opening-flow-simulator` @ `0976b65` ("test(processor): add map artifact baseline regression harness")
- **Working tree:** DIRTY (in-flight `add-opening-flow-simulator` work). Left untouched.

---

## 0. Environment fingerprint (actual commands + Python environment)

Recorded by running the commands below in the repo root (`pwsh`):

| Command | Output |
|---|---|
| `python --version` | `Python 3.11.4` |
| `python -c "import sys; print(sys.executable)"` | `C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe` |
| `python -c "import numpy; print('numpy', numpy.__version__)"` | `numpy 1.26.4` |
| `python -m pytest --version` | `pytest 8.3.5` |
| `pytest --version` (bare `pytest` on PATH) | **exit code 1** — `pytest` is not installed as a standalone console script; use `python -m pytest` |
| `node --version` | `v24.11.0` |
| `git --version` | `git version 2.47.0.windows.2` |

**Verified:** NumPy 1.26.4 and pytest 8.3.5 are importable from the global interpreter. **Unknown:** NumPy is not declared in `requirements.txt` (per research-003), and there is no virtualenv in the repo, so reproducibility depends on the machine-global interpreter.

**Verification method note:** no test/build command was executed by this investigation (read-only mode forbids executing build/test commands). All behavioural results attributed to the harness below come from the previously committed `impl-001.md`, not from a re-run in this session. Exact commands that *would* re-verify are listed in §8.

---

## 1. Recoverability from git history — VERIFIED RECOVERABLE

All three code files and all five deleted change artifacts are **present in `HEAD` (`0976b65`) and tracked in the index**. The working-tree deletions are *unstaged* (`git status --short` shows a leading space: ` D`), so the index still holds the blobs. Nothing is lost.

`git ls-tree -r HEAD --name-only -- processor/baseline.py processor/baseline_firing.mjs processor/tests/test_baseline.py` returned all three paths. `git show --stat HEAD` shows the commit added:

| File (in HEAD) | Lines | Status in working tree |
|---|---|---|
| `processor/baseline.py` | 791 | deleted (unstaged) |
| `processor/baseline_firing.mjs` | 110 | deleted (unstaged) |
| `processor/tests/test_baseline.py` | 250 | deleted (unstaged) |
| `openspec/changes/reduce-map-data-footprint/artifacts/task-record.md` | 65 | deleted (unstaged) |
| `openspec/changes/reduce-map-data-footprint/artifacts/impl-001.md` | 76 | deleted (unstaged) |
| `openspec/changes/reduce-map-data-footprint/artifacts/research-001.md` | 248 | deleted (unstaged) |
| `openspec/changes/reduce-map-data-footprint/artifacts/research-002.md` | 209 | deleted (unstaged) |
| `openspec/changes/reduce-map-data-footprint/artifacts/research-003.md` | 240 | deleted (unstaged) |

`git ls-files openspec/changes/reduce-map-data-footprint` lists **15 tracked files**, including `artifacts/baseline-pre-change.json` (2,447,993 bytes) and `artifacts/compare-unchanged-report.json` (1,121 bytes), both of which still exist on disk. `git diff --name-only --cached` is empty → **no staged changes**.

`git log --oneline --follow -- processor/baseline.py` returns exactly one commit: `0976b65`. The harness was introduced in that commit and has no other history.

**Recovery commands (do not reset the tree; these touch only the named paths):**
```powershell
git restore --source=HEAD -- processor/baseline.py processor/baseline_firing.mjs processor/tests/test_baseline.py
git restore --source=HEAD -- openspec/changes/reduce-map-data-footprint/artifacts/task-record.md
git restore --source=HEAD -- openspec/changes/reduce-map-data-footprint/artifacts/impl-001.md
git restore --source=HEAD -- openspec/changes/reduce-map-data-footprint/artifacts/research-001.md
git restore --source=HEAD -- openspec/changes/reduce-map-data-footprint/artifacts/research-002.md
git restore --source=HEAD -- openspec/changes/reduce-map-data-footprint/artifacts/research-003.md
```
`git show HEAD:<path> > <path>` is an equivalent fallback. `git restore` does not disturb the other dirty files (`calculator/**`, `processed_maps/*/metadata.json`, `processor/*.py`).

**Gitignore interaction (Verified, important):**
- `.gitignore:19` is a global `artifacts/` rule. `git check-ignore -v openspec/changes/reduce-map-data-footprint/artifacts/research-005.md` → `.gitignore:19:artifacts/`. **Any newly written artifact file in this folder is gitignored and must be `git add -f`'d** (the existing ones were force-added).
- `git check-ignore -v` on the already-tracked `baseline-pre-change.json` returns nothing → tracked files are unaffected by the ignore rule.
- `.gitignore` also ignores `processed_maps/`, `www/`, `raw_map_data/*`, `*.zip`, `node_modules/`.

---

## 2. Current map artifact layout (filenames/sizes only)

Measured with `Get-ChildItem -Recurse -File | Measure-Object Length -Sum` and per-map recursive listings. **No artifact file was opened.**

### Totals
| Tree | Files | Size |
|---|---|---|
| `processed_maps/` | 20,903 | **10.52 GB** |
| `www/` | 20,891 | **10.51 GB** |

### Top-level map set
- `processed_maps/` directories: **85**; `mapsList.json` `count`: **85**.
- `dirs_not_in_list`: **[]**; `list_not_in_dirs`: **[]** → **no orphan top-level map folders and no manifest entries without a folder.**
- `the_falklands` is **absent** (correctly excluded). `andromeda` is **present**.
- `obstructions.json`: **84** files. `obstructions.json.gz`: **0**. `*.gz` total: **85** (all `heightmap.json.gz`).

### Representative map layout (`processed_maps/adak`, sizes in bytes)
| Path | Bytes | Notes |
|---|---|---|
| `contourmap.png` | 506,245 | |
| `gamelayers.json` | 249,035 | |
| `heightmap.json.gz` | 1,266,168 | already gzipped, out of scope |
| `metadata.json` | 520 | tracked |
| `minimap.png` | 1,413,123 | |
| `obstructions.json` | 6,261,345 | pretty-printed JSON whale |
| `terrain/sidecar.json` | 67,417 | |
| `terrain/edge_grade_max.bin` | 4,194,304 | float32 |
| `terrain/edge_rise_m_max.bin` | 4,194,304 | float32 |
| `terrain/elevation_mean.bin` | 4,194,304 | float32 |
| `terrain/roughness_m_mean.bin` | 4,194,304 | float32 |
| `terrain/slope_deg_max.bin` | 4,194,304 | float32 |
| `terrain/slope_deg_mean.bin` | 4,194,304 | float32 |
| `terrain/static_multiplier.bin` | 4,194,304 | float32 |
| `terrain/vegetation_dense.bin` | 4,194,304 | float32 |
| `terrain/road_mask.bin` | 1,048,576 | uint8 mask |
| `terrain/water.bin` | 1,048,576 | uint8 mask |
| `terrain/infantry/cost.bin` | 4,194,304 | float32 |
| `terrain/infantry/classes.bin` | 1,048,576 | uint8 |
| `terrain/infantry/sidecar.json` | 583 | |
| `terrain/wheeled_vehicle/cost.bin` | 4,194,304 | float32 |
| `terrain/wheeled_vehicle/classes.bin` | 1,048,576 | uint8 |
| `terrain/wheeled_vehicle/sidecar.json` | 593 | |
| `flow/**` | 1,048,576 per `.bin` + small `.json` | uint8 flow fields |

Byte math: `4,194,304 = 1024 × 1024 × 4` → 1024×1024 **float32** grid; `1,048,576 = 1024 × 1024` → 1024×1024 **uint8** grid. This matches research-002's 1024² accounting (~44 MiB terrain for adak).

### Tracked vs untracked artifact scope
- Tracked files in the repo: **561**; tracked under `processed_maps/`: **340** = `README.md` + 85 maps × 4 shipped files (`contourmap.png`, `heightmap.json.gz`, `metadata.json`, `minimap.png`).
- The large artifacts (`obstructions.json`, `terrain/*`, `flow/*`) are **untracked** (gitignored by `processed_maps/`).
- `git status` shows **many `processed_maps/*/metadata.json` modified** — tracked metadata is dirty from the in-flight flow work; it is part of the tree that must not be reset.

### Stale-generation / cleanup scope
- `generations` directories: **737**; `v2-*` generation directories: **892**.
- Example: `processed_maps/adak/flow/gpm_cq_64/generations` contains **4** generation folders (`v2-adak-1abbd7e784db`, `v2-adak-gpm_cq_64-231f038caa17`, `v2-adak-gpm_cq_64-9681c68deef4`, `v2-adak-gpm_cq_64-f1f72ec44dfc`) though only one is the active pointer target. **Inferred:** a large fraction of the 892 generation dirs are stale and are the primary in-folder cleanup candidate; the exact active/stale split was not computed (it requires reading `class_manifest.json` pointers, which was out of scope for a listing-only probe).

---

## 3. Harness contract as recovered from HEAD (`processor/baseline.py` header + `impl-001.md`)

**Verified from `git cat-file -p HEAD:processor/baseline.py`:**
- CLI: `capture` / `compare`; exit codes `0` pass/capture-written, `1` tolerance exceedance, `2` usage/I-O error.
- Dependencies: Python stdlib + NumPy only. **READ-ONLY** against `processed_maps/` and `raw_map_data/`; refuses to write output inside either tree (`_guard_output_path`).
- **Deliberately does NOT import `processor/terrain_artifact.py` or any processor module** — artifacts are decoded directly from sidecar JSON + `np.fromfile`. (This is why the harness still works while the writer is broken; see §5.)
- Deterministic sampling: `rng = numpy.random.default_rng(20261009)`; 64 indices per grid, same seed per grid by design.
- Grid decode contract: shape from the sidecar; dtype from the sidecar entry; legacy defaults `cost.bin "<f4"`, `classes.bin "u1"`, `road_mask`/`water`/`bridge_mask "u1"`. Format-1.2 quantization entry `{dtype, offset, scale}` accepted nested/top-level/sidecar-level, resolved in the single function `_entry_with_quant()`.
- `DEFAULT_MAPS` (8, verified): `adak`, `albasrah_2`, `muttrah_city_2`, `fields_of_kassel`, `ascheberg`, `korbach_offensive`, `road_to_damascus`, `shijiavalley`.
- `FIRING_MAPS = ("adak", "muttrah_city_2")`.
- `TOLERANCES` present; firing tolerance `FIRING_TOL_MILS`; obstruction bbox tolerance `BBOX_TOL_M`.
- Known ceilings (documented in the header): the firing-solution fixture needs `node` on PATH and covers only `FIRING_MAPS`; on failure it records `{"status": "unavailable", "reason": ...}` and capture continues; compare treats unavailable-on-either-side as a note, not a failure.

**Verified from the committed `impl-001.md` (previous session, not re-run here):**
- `baseline-pre-change.json` = **2,447,993 bytes** (2.4 MB), captured over all 8 maps in **179.9 s**; a second capture was **byte-identical** (`BYTE_IDENTICAL=True`) — the document contains no timestamp.
- `compare-unchanged-report.json`: `result: pass`, `exceedance_count: 0`, `notes: []`, `files_informational` `added/changed/missing = 0` for all 8 maps.
- `python -m pytest processor/tests/test_baseline.py -q` → `10 passed`.
- Full safe suite `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py -q` → `4 failed, 100 passed, 8 errors`; the failures/errors are pre-existing and unrelated (2× `test_flow_field`, 2× `test_terrain_artifact`, 8 errors in `test_terrain_cost`).

---

## 4. Safe deterministic baseline scope

**Verified:**
- The baseline document is deterministic: no timestamp, seeded sampling, and a real byte-identical re-capture was recorded in `impl-001.md`. A second capture is therefore a valid re-verification of "nothing changed".
- Scope = the 8 `DEFAULT_MAPS`; masks/counts/sentinels compared **exactly**; continuous grids within `scale/2`; flow arrivals within `max(2%, 1.0 s)` with a capped flip count; obstruction bbox within 0.1 m; firing mils within 0.5.
- The baseline is small JSON (2.4 MB) and already tracked — it is the right thing to commit.

**Caveats that bound how "safe" it is:**
- The baseline snapshots the **current on-disk artifacts**, i.e. the bytes produced by whatever generated `processed_maps/` before this session. It is a *pre-change truth* only so long as nothing else regenerates those artifacts. The in-flight `add-opening-flow-simulator` change could regenerate `processed_maps/` independently and invalidate the baseline (flagged in the recovered `task-record.md`). **Inferred:** the baseline should be re-verified (or re-captured) immediately before phase 2 begins if the flow work lands first.
- The baseline does **not** establish that regeneration is reproducible; it establishes that *if* regeneration reproduces the semantics, compare passes. Regeneration determinism itself is blocked today (§5).

---

## 5. Can full regeneration/cleanup proceed without destructive operations? — NOT YET

### 5a. Regeneration is currently blocked (Verified)
The working tree's terrain writer is broken:

```
processor/build_terrain_cost.py:522   from terrain_artifact import terrain_generation_id
processor/build_terrain_cost.py:530   sidecar["generation_id"] = terrain_generation_id(sidecar)
```
`processor/terrain_artifact.py` defines only `load_terrain_artifact` (L17) and its inner `read_grid` (L37). A repo-wide search across `processor/`, `calculator/`, `openspec/` finds `terrain_generation_id` **only** in `build_terrain_cost.py` — it is **defined nowhere**. Therefore `write_artifacts` raises `ImportError` at call time. This confirms (independently) the HIGH risk recorded in the recovered `research-002.md`; the situation persists at HEAD `0976b65`.

**Consequence:** regenerating terrain artifacts with the current working tree is impossible until `terrain_generation_id` is restored or implemented. The baseline harness is unaffected (it does not import the writer).

### 5b. Format-1.1 maps are unloadable by the shipped loader (from research-002; consistent with `terrain_artifact.py` having no version branch)
`terrain_artifact.py` validates `format_version != "1.0"` → raises; there is no 1.0/1.1/1.2 branch. Several production maps carry format 1.1 (`bridge_mask.bin`). The plan's "1.2 backward-compatible with 1.0/1.1" therefore requires restoring 1.1 support, not merely adding 1.2. **Verified by file inspection:** `terrain_artifact.py` exposes only `load_terrain_artifact`; no version branch is present.

### 5c. What is genuinely non-destructive today
| Operation | Destructive? | Notes |
|---|---|---|
| `git restore` of the 3 code files + 5 artifacts from HEAD | No | Only touches named paths; leaves all other dirty files intact |
| Reading/listing `processed_maps/`, `raw_map_data/` | No | Source of truth `raw_map_data/` is never modified |
| Running `baseline.py compare` (read-only, writes report outside the trees) | No | Refuses to write inside `processed_maps/`/`raw_map_data/` |
| Regenerating `processed_maps/` artifacts | **Yes (overwrite)** | Reversible only by regeneration from `raw_map_data/` + `git restore` of the 340 tracked files; currently blocked (§5a) |
| Deleting stale generations / superseded `obstructions.json` | **Yes (irreversible for untracked bulk)** | Must follow a verified regeneration; keep the baseline until the change archives |
| `git clean -x` / `git reset --hard` | **Yes, and dangerous here** | Would also delete the untracked/ignored baseline artifacts and the dirty flow work — do not use |

**Verified cleanup findings:** there are **no orphan top-level map folders** (85 dirs == 85 manifest entries), so "map folders not in the manifest" is currently an empty set. The real cleanup surface is *inside* map folders: 892 `v2-*` generation dirs (stale generations), plus superseded `obstructions.json` after a `.gz` rollout, plus superseded format files. Deleting these is a destructive filesystem act on untracked data and must be gated behind a passing `baseline.py compare`.

---

## 6. Unknowns

- **FIND:** the exact active-vs-stale split of the 892 `v2-*` generation dirs (requires reading `class_manifest.json` pointers; not done here).
- **FIND:** whether the in-flight flow work will regenerate `processed_maps/` before this change's phase 2, which would invalidate the committed baseline.
- **ASK:** branch strategy — edit on top of the dirty tree, or wait for the flow work to commit first? (Raised in the recovered `task-record.md`; only the user can decide.)
- **ASK:** is restoring format-1.1 loader support in scope for this change, or a separate change? (The plan text assumes it is available.)
- **FIND:** whether `extract_obstructions.py` is supposed to regain per-map CLI args — AGENTS.md says yes, the worktree code ignores `sys.argv` (research-003). Affects the phase-4 per-map regeneration loop.
- **FIND:** the intended per-grid quantization targets (which diagnostics get uint8 vs uint16; whether `cost.bin` becomes uint16) — not specified in the reviewed plan text.
- **FIND:** whether `andromeda` is intentionally heightmap-only (no `obstructions.json`/`gamelayers.json`).

## 7. Risks

1. **HIGH — regeneration blocked:** `terrain_generation_id` is undefined in the working tree (`build_terrain_cost.py:522`). Any attempt to regenerate terrain fails with `ImportError`. Resolve before phase 2/3 verification.
2. **HIGH — 1.1 artifacts unloadable:** the shipped loader rejects `format_version != "1.0"`; the "1.2 backward-compatible with 1.1" goal is not deliverable without restoring 1.1 support.
3. **MEDIUM — dirty-tree entanglement:** `build_terrain_cost.py`, `extract_obstructions.py`, `build_flow_fields.py`, `terrain_features.py`, `calculator/static/js/*`, `templates/index.html`, and many `processed_maps/*/metadata.json` are modified by the in-flight flow work. Regeneration would entangle with uncommitted work and could clobber it.
4. **MEDIUM — baseline invalidation:** the committed baseline reflects current artifact bytes; independent regeneration of `processed_maps/` by the flow change would make every post-change compare fail spuriously.
5. **MEDIUM — new artifacts are gitignored:** `.gitignore:19 artifacts/` means any new file under `.../artifacts/` (including this one) must be `git add -f`'d or it is silently untracked and lost on a later clean.
6. **MEDIUM — 0.1 m rounding is not bit-identical:** boundary cells can flip in `road_mask`/`static_multiplier`/`vegetation_dense` and therefore in `cost.bin`/`classes.bin` (research-002). The harness's bounded-flip / rasterized-output comparison (not raw-JSON equality) is the correct mitigation.
7. **LOW — tooling:** bare `pytest` is not on PATH (exit 1); use `python -m pytest`. NumPy 1.26.4 is undeclared in `requirements.txt` with no venv, so the harness's "stdlib + NumPy only" contract depends on the global interpreter.
8. **LOW — doc/code drift:** AGENTS.md's `extract_obstructions.py <map>` CLI claim does not match the code; AGENTS.md also documents terrain format 1.1 behaviour that the code does not implement.

## 8. Recommendation for the first implementation phase

**Phase 1 = recover the safety net only; make no writer/reader edits and no regeneration.** This is the smallest correct, reversible step and it unblocks everything else.

1. **Recover from HEAD into the working tree** (no reset, no clean, no staging):
   - `git restore --source=HEAD -- processor/baseline.py processor/baseline_firing.mjs processor/tests/test_baseline.py`
   - `git restore --source=HEAD --` each of the five `openspec/changes/reduce-map-data-footprint/artifacts/` files (`task-record.md`, `impl-001.md`, `research-001.md`, `research-002.md`, `research-003.md`).
2. **Re-verify the recovered harness** (implementer/orchestrator runs these; they were *not* run in this read-only session):
   - `python -m pytest processor/tests/test_baseline.py -q` → expect `10 passed`.
   - `python processor/baseline.py compare --baseline openspec/changes/reduce-map-data-footprint/artifacts/baseline-pre-change.json --report <path outside processed_maps/>` → expect exit 0, `0 exceedances`.
   - Optionally re-run the safe suite and confirm the pre-existing `4 failed / 8 errors` are unchanged and no new failures appear.
3. **Do not regenerate or delete anything in phase 1.** `processed_maps/` stays byte-for-byte as captured.
4. **Resolve the two prerequisites before phase 2/3 writer edits** (they block regeneration, not the harness): (a) restore/implement `terrain_generation_id`; (b) restore format-1.1 loader support in `terrain_artifact.py`.
5. **Decide branch strategy with the user** before touching the dirty writers — edit on top of the dirty tree vs wait for `add-opening-flow-simulator` to commit. Record the decision in `task-record.md`.
6. **Remember to `git add -f`** any new file written under `.../artifacts/` (the folder is gitignored).
7. **Re-confirm the baseline is still valid** immediately before phase 2 (re-run `compare`); re-capture if the flow work has regenerated `processed_maps/`.

**Explicitly out of scope for phase 1:** obstruction compaction (phase 2), terrain quantization (phase 3), regeneration/measurement (phase 4), cleanup/Android resync (phase 5).

---

## Sources searched

- **Git history:** `git show --stat HEAD`, `git ls-tree -r HEAD --name-only -- processor/...`, `git log --oneline --follow -- processor/baseline.py`, `git show HEAD:<path>` for `baseline.py`, `task-record.md`, `impl-001.md`, `research-001.md`, `research-002.md`, `research-003.md`; `git ls-files openspec/changes/reduce-map-data-footprint`; `git ls-files processed_maps`; `git diff --name-only --cached`; `git status --short`; `git check-ignore -v`.
- **Change docs (working tree):** `proposal.md`, `design.md`, `tasks.md`, `specs/map-artifact-regression/spec.md`, `specs/map-processor/spec.md`, `specs/terrain-traversability/spec.md`, `artifacts/compare-unchanged-report.json`.
- **Code:** `processor/build_terrain_cost.py` (L505–540), `processor/terrain_artifact.py` (function index), repo-wide `Select-String` for `terrain_generation_id`.
- **Data (filenames/sizes only, never opened):** `processed_maps/` (85 dirs), `processed_maps/adak/**`, `mapsList.json`, `.gitignore`, `www/` (size only), flow generation-dir counts.

## Worklog (commands + summarized outputs)

| Command (abridged) | Result |
|---|---|
| `Get-ChildItem openspec/changes -Recurse` | located active change + deleted artifacts |
| `git status --short` | DIRTY; ` D processor/baseline.py`, ` D processor/baseline_firing.mjs`, ` D processor/tests/test_baseline.py`, ` D` 5 change artifacts; many ` M` flow/UI/metadata files; untracked new change dirs |
| `git branch --show-current` / `git log --oneline -n 20` | `feat/opening-flow-simulator` @ `0976b65` |
| `git show --stat HEAD` | HEAD added harness (791+110+250 lines) + 5 artifacts + specs + baseline JSON |
| `git ls-tree -r HEAD -- processor/baseline.py ...` | all 3 baseline code paths present in HEAD |
| `git ls-files openspec/changes/reduce-map-data-footprint` | 15 tracked files incl. the 5 "deleted" artifacts |
| `git diff --name-only --cached` | empty (no staged changes) |
| `git check-ignore -v .../artifacts/research-005.md` | `.gitignore:19:artifacts/` → new artifacts gitignored |
| `Get-ChildItem processor` / `processor/tests` | baseline.py/baseline_firing.mjs/test_baseline.py absent from disk |
| `python --version` etc. | Python 3.11.4, NumPy 1.26.4, pytest 8.3.5 (`python -m`), node v24.11.0, git 2.47.0 |
| `python -c "mapsList vs dirs"` | 85 == 85; no orphans; `the_falklands` absent; `andromeda` present |
| `Get-ChildItem processed_maps -Recurse -File -Filter *.gz` | 85 (all heightmaps); `obstructions.json` = 84; `obstructions.json.gz` = 0 |
| `Measure-Object` on `processed_maps` / `www` | 10.52 GB / 20,903 files; 10.51 GB / 20,891 files |
| `git ls-files processed_maps \| Measure-Object` | 340 tracked; 561 tracked repo-wide |
| `Select-String terrain_generation_id` (processor/calculator/openspec) | only `build_terrain_cost.py:522,530`; defined nowhere |
| `Select-String` in `terrain_artifact.py` | 0 matches for `terrain_generation_id`; only `load_terrain_artifact` + `read_grid` defined |
| `git cat-file -p HEAD:processor/baseline.py` (header + `DEFAULT_MAPS`) | 8-map default set + firing maps confirmed; read-only/deterministic contract confirmed |
| flow generation-dir counts | 737 `generations`, 892 `v2-*`; adak gpm_cq_64 has 4 |

**Dead ends / non-findings:** two terminal invocations returned stale/interleaved output from a concurrent process (a `package.json`/`build-android.bat` dump appeared in place of a `git show` result). Affected commands were re-run with explicit `MARKER_START`/`MARKER_END` separators; all values reported here are from the clean runs.
