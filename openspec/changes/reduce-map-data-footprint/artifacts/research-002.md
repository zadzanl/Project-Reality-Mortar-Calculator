# research-002 — Writer-side loader contract for `reduce-map-data-footprint`

Scope: pin the writer-side (processor) contract for the planned change:
(a) `obstructions.json` → `obstructions.json.gz` (compact separators, coords rounded to 0.1 m);
(b) float32 `terrain/*.bin` → quantized uint8/uint16 with per-grid `{dtype, offset, scale}` in the
sidecar, `format_version "1.2"`, loader backward-compatible with 1.0/1.1.

Mode: READ-ONLY reconnaissance. No files modified except this artifact.
All evidence is from the **working tree** (dirty) on branch `feat/opening-flow-simulator`.

---

## 0. Environment fingerprint

- OS: Windows; shell pwsh. Date: 2026-10-09T16:21 +07:00.
- Branch: `feat/opening-flow-simulator`; HEAD `f6ba143` ("Merge remote-tracking branch 'origin/main' into feat/opening-flow-simulator"), parents `2c06b7b` (feature) + `0ff4224` (main).
- Working tree: DIRTY. Modified (relevant): `processor/build_flow_fields.py`, `processor/build_terrain_cost.py`, `processor/extract_gamelayers.py`, `processor/extract_obstructions.py`, `processor/extract_vehicle_speeds.py`, `processor/terrain_features.py`, `processor/movement_params.json`, `processor/terrain_params.json`, several `processor/tests/*`, `calculator/**`, many `processed_maps/*/metadata.json`. Untracked: `openspec/changes/reduce-map-data-footprint/` and several other change dirs.
- `processor/terrain_artifact.py` is **clean** (working tree == HEAD).
- `processed_maps/` is **gitignored** (`.gitignore:25`), so artifacts are untracked generated data.

---

## CRITICAL DISCREPANCY (read before trusting the plan's premise)

The plan states the loader must "stay backward-compatible with 1.0/1.1". **The current codebase
does not support format 1.1 at all**, and the working tree is internally inconsistent:

1. `processor/terrain_artifact.py` (82 lines, working tree == HEAD) contains ONLY:
   - `BLOCKED = -1.0` (line 14)
   - `load_terrain_artifact(path, profile="infantry")` (line 17)
   - a strict guard: `if sidecar.get("format_version") != "1.0" or sidecar.get("artifact") != "terrain_cost": raise ValueError("unsupported terrain artifact format")` (line 21).
   - It reads only `cost.bin` (`<f4`), `classes.bin` (`u1`), `road_mask.bin` (`u1`), `water.bin` (`u1`) and `diagnostics`. There is **no** `bridge_mask.bin`, **no** `version == "1.1"` branch, and **no** `terrain_generation_id` symbol.
   - Verified three ways: `read_file`, `Get-Content`, and a live import — `python -c "...import terrain_artifact as t; print(hasattr(t,'terrain_generation_id'))"` → `False`; module attrs = `['BLOCKED','Path','json','load_terrain_artifact','np','re']`.

2. `processor/build_terrain_cost.py` (working tree, line 522) does `from terrain_artifact import terrain_generation_id` and (line 530) `sidecar["generation_id"] = terrain_generation_id(sidecar)`. **That symbol does not exist anywhere in the repo** (grep `terrain_generation_id` over all `*.py` outside android/www/node_modules/processed_maps/raw_map_data → only these two lines). ⇒ `write_artifacts()` raises `ImportError` at runtime in the current working tree. This is an uncommitted in-flight addition (see `git diff`, which shows the import added by the dirty change) whose dependency was never added to `terrain_artifact.py`.

3. `git log --all -S 'bridge_mask' -- processor/` → **empty**. `git log --all -S 'terrain_generation_id' -- processor/` → **empty**. No stash (`git stash list` empty), single worktree. So the bridge/1.1 implementation was **never committed on any branch**; it existed only as an earlier uncommitted worktree state that is now gone. The feature tip `2c06b7b:processor/terrain_artifact.py` is also the 1.0-only version.

4. **Production artifacts disagree with the loader.** 5 maps ship `format_version "1.1"` sidecars + `bridge_mask.bin` (kunar_province, albasrah_2, carentan, krivaja_valley, tad_sae — from sidecar scan). The 1.1 sidecar adds top-level key `bridges`, and `units.classes["7"] = "bridge_deck"`, `units.bridge_mask = "uint8; 0 none, 1 confirmed, 2 candidate/unverified"`. The current loader **rejects** these (`!= "1.0"` → ValueError), so `build_flow_fields.load_terrain_artifact` would fail on those 5 maps.

**Implication for the plan:** a 1.0/1.1/1.2 version branch cannot be written "backward-compatible with 1.1"
unless 1.1 support is first restored/implemented. AGENTS.md ("Terrain format 1.1 adds `bridge_mask.bin`…")
documents behaviour that is not present in the code. This must be resolved/decided before phase 3.

---

## Q1. `extract_obstructions.py` — exact JSON schema, float serialization, consumers

File: `processor/extract_obstructions.py` (dirty; the dirty diff only adds `normalize_mesh_reference`, a `lines` map for error messages, and `np_is_finite` validation — the **output schema is unchanged**).

Writer (lines 200–208):
```python
201  output = {"map_name": name, "format_version": "1.0", "roads": roads,
202            "statics": statics, "vegetation": vegetation,
203            "counts": {"roads": ..., "road_triangles": ...,
204                       "statics_classified": ..., "statics_unclassified": ...,
205                       "vegetation": ...}}
206  destination = OUT / name / "obstructions.json"
208  destination.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
```

Top-level keys (exactly): `map_name`, `format_version` (`"1.0"`), `roads`, `statics`, `vegetation`, `counts`.

Record schemas:
- `roads[]` (line 150): `{"name": <Object.create template>, "triangles": [ [[x,y],[x,y],[x,y]], ... ]}`. `x,y` are repository-space meters (float, from `bf2_to_repo`).
- `statics[]` (lines 92–93): `{"template": <str>, "class": <building|wall|fence|container|vegetation|unclassified>, "x": <float>, "y": <float>, "rotation_deg": <float>}`.
- `vegetation[]` (line 108): `{"template": <str>, "x": <float>, "y": <float>}` (no class, no rotation).
- `counts` (lines 203–205): `{"roads": int, "road_triangles": int, "statics_classified": int, "statics_unclassified": int, "vegetation": int}`.

Float serialization: **`json.dumps(output, indent=2)`, no rounding, no compact separators** (line 208). Coordinates are Python floats serialized at full `repr` precision (e.g. `1234.5678901234567`); `encoding="ascii"`, trailing `\n`. There is no `round()` anywhere in the writer. ⇒ The planned `indent=None/compact separators` + `round(x,1)` is a genuine change to this call site.

Consumers of `obstructions.json` (repo-wide, excluding `processed_maps/`, `www/`, `android/`, `node_modules`, `.github/chat/chat.json`):
- `processor/build_terrain_cost.py:592` reads it (fields read: `roads`, `statics`, `vegetation`; also `obstructions_path.exists()` for coverage). Note: it does **not** read `counts` and does **not** read a `bridges` key in the working tree (lines 592–600).
- `processor/build_terrain_cost.py:516` records the path string in the sidecar `provenance.obstructions = "processed_maps/<map>/obstructions.json"` (a string, not a read).
- `processor/render_obstruction_qa.py:31` (`json.loads((directory / "obstructions.json")...)`).
- `processor/spike_material_map.py:37` (`OBSTRUCTIONS_PATH = .../obstructions.json`).
- `processor/tests/test_terrain_cost.py:190,253` (writes fixtures named `obstructions.json`).
- Writer: `processor/extract_obstructions.py:206`.
- **Not** consumed by `calculator/**` (no JS/server reference to `obstructions`), **not** by any `processor/*.ipynb` (notebook scan found no matches), **not** by `build_flow_fields.py`.
⇒ Renaming to `.gz` requires updating exactly the 4 real readers above + tests + the provenance string. (Confirm whether `render_obstruction_qa.py` / `spike_material_map.py` are maintainer-only; they are not shipped to the browser.)

Footprint (metadata only; files never opened): 84 `obstructions.json` present, total **5.10 GB**, avg 60.7 MB, max **182.6 MB** (`fields_of_kassel`), min ≈0. No `.gz` exists yet. This is the single largest per-map JSON and the main motivation for the gz change.

---

## Q2. `build_terrain_cost.py` — rasterization, cell size, 0.1 m verdict, fields read

File: `processor/build_terrain_cost.py` (dirty; 666 lines). Rasterizers all take `grid["cell_m"]`:
- `rasterize_roads(roads, rows, cols, cell_m)` (called line 613 with `grid["cell_m"]`). Uses edge-function point-in-triangle containment tested at **cell centres** `(col+0.5)*cell_m, (row+0.5)*cell_m`; bounding box via `math.floor(coord/cell_m)`.
- `static_multiplier(statics, rows, cols, cell_m, footprints, building_mult)` (called line 620). Fixed-radius proxy: `radius_cells = footprints[kind]/cell_m`; Euclidean test `(cx+0.5-c_center)^2 + (cy+0.5-r_center)^2 <= radius_cells^2`.
- `vegetation_density(vegetation, rows, cols, cell_m, radius_m, dense_count)` (called line 623). Bins each plant with `int(plant["x"] // cell_m)` (floor), then summed-area table within `density_radius_m`.

Cell size (meters): `grid_shape()` (lines 66–82): `cell_samples = max(1, round(cell_size_m/spacing))`; `cell_m = cell_samples * spacing`. Config `requested cell_size_m = 4.0` (`terrain_params.json` `grid.cell_size_m.value`). Observed sidecar values across all maps: **cell_size_m ∈ {4.0 (majority), 8.0, 16.0}**; source spacing ∈ {1.0, 2.0, 4.0, 8.0, 16.0}. Minimum observed cell = **4.0 m** (when spacing ≤ 4 m, `cell_samples=1` ⇒ `cell_m = spacing`; e.g. grostok/korengal/reichswald spacing 1.0 → cell 4.0).

Fields actually read from `obstructions.json` by `build_terrain_cost.py`:
- roads: `road["name"]` (decal filter `DECAL_RE`, line ~57), `road["triangles"]`.
- statics: `item["class"]`, `item["x"]`, `item["y"]` (rotation NOT used).
- vegetation: `plant["x"]`, `plant["y"]` (template/class NOT used).

**0.1 m rounding verdict (nuanced):**
- The decision *scale* is the cell (4–16 m) and the footprint radii (`footprints_m`: building 6.0, wall 3.0, container 3.0, fence **2.0** m). 0.1 m is 1.25–2.5 % of the smallest cell (4 m) and 5 % of the smallest footprint radius (2 m). At grid scale, rounding to 0.1 m cannot move a coordinate by a full cell and is far below all footprint radii.
- **However**, all three rasterizers use exact geometric tests (point-in-triangle at cell centres; Euclidean radius vs cell centres; integer floor division). A coordinate that sits within 0.1 m of a decision boundary **can still flip a borderline cell** — e.g. a road triangle edge passing within 0.1 m of a cell centre, a static within 0.1 m of its footprint radius, or a plant within 0.1 m of a cell boundary. So 0.1 m is **safe at the intended resolution but is NOT a byte-identical guarantee**; expect a small number of boundary-cell membership changes in `road_mask` / `static_multiplier` / `vegetation_dense` and therefore in `cost.bin`/`classes.bin`.
- Recommendation for the plan's regression baseline: assert cell-flip counts are bounded/small on representative maps rather than asserting exact equality, OR round at a precision that provably cannot cross a boundary (not achievable below cell scale). State this explicitly as a known ceiling.

---

## Q3. `terrain_artifact.py` / `build_terrain_cost.py` — grid inventory, sidecar, version branch

### Grids written (writer: `write_artifacts`, `build_terrain_cost.py:406–532`)
| File | dtype on disk | semantic | source line |
|---|---|---|---|
| `terrain/road_mask.bin` | `uint8` (0/1) | **mask** (1 = explicit road member) | 412 |
| `terrain/water.bin` | `uint8` (0 none / 1 confirmed / 2 candidate) | **mask** | 413 |
| `terrain/<profile>/cost.bin` | `float32` little-endian, `-1.0` = blocked | **thresholded** (positive multiplier or hard-block) | 425 |
| `terrain/<profile>/classes.bin` | `uint8` (0..6) | **diagnostic** class per cell | 426 |
| `terrain/<name>.bin` diagnostics (8 files) | `float32` little-endian | **diagnostic** | 417–419 |

Diagnostics (8, from `dict(agg, static_multiplier=..., vegetation_dense=...)` at the call site line 630–632; all written `astype("<f4")`):
`slope_deg_mean`, `slope_deg_max`, `edge_rise_m_max`, `edge_grade_max`, `elevation_mean`, `roughness_m_mean` (only when roughness available), `static_multiplier`, `vegetation_dense`.
Confirmed against real sidecars (`andromeda`, `carentan`): diagnostics keys = exactly those 8, all `dtype "<f4"`.

Profiles: `config["profiles"]` = `["infantry", "wheeled_vehicle"]` (2 cost+classes pairs). Class names (line 46–54): 0 unknown, 1 smooth_traversable, 2 rough_traversable, 3 slow, 4 extreme_slope, 5 water, 6 water_candidate. (1.1 sidecars add `"7": "bridge_deck"`, absent from code.)

### Sidecar structure (`terrain/sidecar.json`, written lines 450–532)
Top-level keys (working-tree 1.0 writer): `map_name`, `format_version` (`"1.0"`), `artifact` (`"terrain_cost"`), `blocked_sentinel` (`-1.0`), `diagnostics` (`{name: {file, dtype, min, max}}`), `methods`, `grid`, `units`, `water`, `roads`, `statics`, `vegetation`, `surface_material`, `config`, `provenance`, `profiles`. The dirty change additionally appends `file_sha256` (line 527) and `generation_id` (line 530).
- `grid` (lines 468–481): `rows`, `cols`, `cell_size_m`, `map_size_m`, `extent_m`, `requested_cell_size_m`, `origin` (exact string `"top-left; x east, y south; repo world meters"`), `heightmap_orientation`, `source_spacing_m`, `source_resolution`, `degraded_source_resolution`, `cropped_edge_samples`.
- Per-profile sidecar `terrain/<profile>/sidecar.json` (lines 428–439): `profile`, `thresholds`, `class_histogram`, `cost_stats{min,max,blocked_fraction}`.

### Loader functions & where a version branch lives
- Single loader: `processor/terrain_artifact.py::load_terrain_artifact` (line 17). Inner `read_grid(filename, dtype)` (line 37) enforces exact byte length and finiteness, then `np.fromfile(...).reshape(rows, cols)`.
- **Version guard is line 21** (`!= "1.0"` → raise). A 1.0/1.1/1.2 branch belongs here (currently there is none).
- Per-grid dtype/shape selection is lines 51–54 (`cost.bin "<f4"`, `classes.bin "u1"`, `road_mask "u1"`, `water "u1"`); the diagnostics loop is lines 63–66 and **hard-rejects any diagnostic whose `dtype != "<f4"`** (line 64) — this is the exact spot that a `{dtype, offset, scale}` dequantization would need to change.
- Writer counterpart for the format string is `build_terrain_cost.py:451` (`"format_version": "1.0"`) and the dtype literals at lines 417 (`"<f4"`), 419 (`dtype: "<f4"`), 425, 426.
- Returned dict (lines 67–82) exposes `costs`, `classes`, `road_mask`, `water`, `diagnostics`, `passability_sentinel`, `source_coverage`, `provenance`, `config`.

---

## Q4. `build_flow_fields.py` — terrain grids consumed, outputs, direct `.bin` reads?

File: `processor/build_flow_fields.py` (dirty; 1159 lines).
- Reads terrain **only via the loader**: `from terrain_artifact import load_terrain_artifact` (line 50); `process_map` (line 862) builds `terrain = {cls: load_terrain_artifact(terrain_dir, profile=...)}`; `process_map_v2` (lines 938–939) builds `{"infantry": ..., "land": load_terrain_artifact(terrain_dir, profile="wheeled_vehicle")}`.
- Fields consumed from the loader result: `["costs"]` (lines 876, 879, 895, 899, 960, 963, 1029, 1031), `["cell_size_m"]` (876 etc.), `["origin"]` (line 600), `["water"]` (lines 984, 1015, 1019 — boat solver only), `["diagnostics"]["elevation_mean"]` (line 943 — helicopter). It does **not** consume `road_mask` or `classes` directly (grep confirms no such reads).
- Water solver `solve_water_field` (line 444): `costs = np.where(water == 1, 1.0, -1.0).astype(np.float32)` (line 447) — non-confirmed-water cells are `-1.0` blocked for boats.
- Outputs (already uint8 — confirmed): `flow/<mode>_<size>/team<N>/<class>.bin` written via `quantize_field` → `np.uint8` (lines 568–581, `out = np.full(shape, 255, dtype=np.uint8)`), `write_bytes(quantized.tobytes())` (line 596). Plus per-class `.json` sidecars and `race_times.json`. v1 sidecar `format_version "1.0"` (line 591); v2 field/manifest/pointer use `format_version "2.0"` (lines 668, 724, 744, 752, 765, 782, 925, 933). `V2_PIPELINE_VERSION = "v2-4"` (line 66).
- Direct `.bin` read: `np.frombuffer(bin_path.read_bytes(), dtype=np.uint8)` at line 816 reads a **flow** field `.bin` (with its own sidecar) — **not** terrain. Terrain `.bin` is never read directly by this module.
- v2 hashing: `terrain_hashes = {relative_path: sha256(path) for path in terrain_dir.rglob("*") if path.is_file()}` (lines 940–941) feeds `v2_build_id`. ⇒ Any change to terrain `.bin` bytes (quantization) changes `terrain_hashes` and therefore `build_id`, forcing flow regeneration. Relevant to the plan's "retest" phase.

---

## Q5. Sentinel values (exact)

| Sentinel | Value | dtype | Where |
|---|---|---|---|
| Terrain blocked cost | `-1.0` | float32 | `build_terrain_cost.py:39` `BLOCKED = -1.0`; written into `cost.bin`; loader `terrain_artifact.py:14`; guard `costs > 0 | costs == BLOCKED` line 55 |
| Terrain passability sentinel (returned) | `-1.0` | float | `terrain_artifact.py:78` |
| Flow internal unreachable | `-1.0` | float32 | `build_flow_fields.py:60` `UNREACHABLE = -1.0` (comment: "matches terrain BLOCKED") |
| Shipped flow unreachable | `255` | uint8 | `build_flow_fields.py:61` `QUANT_UNREACHABLE = 255` |
| Flow arrival cap | `3600.0` s | float | `build_flow_fields.py:62` `QUANT_CAP_S = 3600.0` (times above saturate; 0..254 = `round(seconds/quantum)`) |
| Water solver blocked | `-1.0` | float32 | `build_flow_fields.py:447` |
| Terrain class (blocked) | `4` (`extreme_slope`) must equal `costs == BLOCKED` | uint8 | `terrain_artifact.py:59` invariant |

---

## Q6. Grid dimensions, cell size, per-map `.bin` byte math

Dimensions across all maps (from sidecar scan of `processed_maps/*/terrain/sidecar.json`):
- `1024×1024`: 21 maps (20× v1.0, 1× v1.1), cell 4.0 m.
- `512×512`: 53 maps (46 v1.0 @4 m, 4 v1.1 @4 m, 2 v1.0 @8 m, 1 v1.1 @8 m).
- `256×256`: 9 maps (3 @4 m spacing1.0, 6 @4 m spacing2.0); `shipment` `256×256` @16 m.
- `128×128`: 1 map (`deagle5`, cell 4.0 m).
Cell size per map = `cell_samples * source_spacing`, min observed 4.0 m (source spacing as low as 1.0 m).

Byte math (verified against measured dir sizes):
- 512² grid: float32 grid = `512*512*4` = **1 MiB**; uint8 grid = `512*512` = **0.25 MiB**.
  - float32 grids per map (1.0) = 8 diagnostics + 2 `cost.bin` = **10 MiB**; uint8 = road_mask + water + 2×classes = **1 MiB** ⇒ **~11 MiB** total. Measured: `andromeda` **11.07 MiB**, `carentan` (1.1, +bridge_mask) **11.32 MiB**.
- 1024² grid: float32 grid = **4 MiB**; uint8 = **1 MiB**.
  - float32 = 10×4 = **40 MiB**; uint8 = 4×1 = **4 MiB** ⇒ **~44 MiB**. Measured: `adak` **44.07 MiB**.
- 256² ≈ 2.75 MiB; 128² ≈ 0.7 MiB.

**Verdict on the "~7 MB float32 per map" claim:** understated. The float32 grids alone are ~10 MiB per 512² map (not 7 MB) and ~40 MiB per 1024² map; whole-terrain totals are ~11 MiB and ~44 MiB respectively. Use the measured numbers when sizing the quantization win. (8 of the 10 float32 grids are diagnostics — the dominant, most quantizable fraction.)

---

## Worklog (searches, dead ends, verification)

- Read `processor/extract_obstructions.py` (full), `processor/terrain_artifact.py` (full, 82 lines), `processor/build_terrain_cost.py` (full, 666 lines), selected `processor/build_flow_fields.py` (40–100, 440–500, 540–620, 800–960), `calculator/server.py:79–165`.
- Greps: `format_version` across `processor/*.py`; `bridge_mask` across `processor/*.py`; `terrain_generation_id` repo-wide `*.py`; `obstructions.json` repo-wide (excl. huge dirs); `terrain_generation_id|bridge_mask` across `processor,openspec`.
- History: `git log --all -S 'bridge_mask' -- processor/` (empty), `git log --all -S 'terrain_generation_id' -- processor/` (empty), `git stash list` (empty), `git worktree list` (single), `git show HEAD:processor/terrain_artifact.py`, `git show 2c06b7b:processor/terrain_artifact.py` (both 1.0-only).
- Runtime: `python -c "import terrain_artifact; hasattr(...'terrain_generation_id')"` → `False`.
- Data: sidecar scans (metadata only) across all 84 maps; `Get-ChildItem` sizes for `obstructions.json` and `terrain/` dirs.
- Dead ends / false positives:
  - An early mixed terminal capture surfaced a **1.1-capable** `load_terrain_artifact` snippet (with `bridge_mask` and `version == "1.1"`) and a longer `build_terrain_cost.py`. Traced and disproved: that text lives only in `.github/chat/chat.json` (a pasted prior-session payload) and in `openspec/changes/*/artifacts/*.md` review notes — **not** in any tracked or working-tree `.py`. Confirmed by direct file read + `git log -S`.
  - `Select-String` over `calculator/**` matched the vendored pako/Leaflet bundles; irrelevant. No calculator code references `obstructions`.
  - Notebook scan (`processor/*.ipynb`) found no `obstruction` references.

## Unknowns
- Whether restoring format 1.1 (bridge_mask + `bridges` sidecar key) is in scope for `reduce-map-data-footprint`, or handled by a separate change. The plan cannot deliver "1.2 backward-compatible with 1.1" without it.
- The intended quantization targets per grid (which of the 8 diagnostics get uint8 vs uint16; whether `cost.bin` becomes uint16). Not specified in the plan text reviewed.
- Whether `render_obstruction_qa.py` / `spike_material_map.py` are considered supported consumers that must also read `.gz`.
- Whether `terrain_generation_id` (the in-flight, currently-missing function) is meant to hash quantized bytes; if so it interacts with `file_sha256` and `build_id`.
- Exact `offset/scale` schema shape for the sidecar (plan says per-grid `{dtype, offset, scale}`; current `diagnostics` entries are `{file, dtype, min, max}` — schema migration path unspecified).

## Risks
- **HIGH — broken working tree:** `build_terrain_cost.write_artifacts` raises `ImportError: cannot import name 'terrain_generation_id'` as-is. Any "baseline" run of the current tree will fail before producing artifacts; the baseline must either use committed code or the missing function must be added first.
- **HIGH — 1.1 artifacts unloadable:** 5 production maps carry format 1.1 with `bridge_mask.bin`; the shipped loader rejects them. If the change's tests or flow regeneration touch those maps, they will fail for reasons unrelated to quantization.
- **MEDIUM — 0.1 m rounding is not bit-identical:** expect small boundary-cell changes; a strict "artifacts unchanged" regression assertion would be wrong. Use bounded-flip assertions + explicit known-ceiling note.
- **MEDIUM — `.gz` consumer updates:** 4 real readers + tests + the sidecar `provenance.obstructions` string; miss one and `build_terrain_cost` silently degrades to "no obstructions" (it prints a warning and continues with empty roads/statics/vegetation, line 599–600).
- **LOW — server MIME:** `calculator/server.py` already special-cases `endswith('.json.gz')` → `application/json` (lines 139–144), so a `.gz` rename is servable; but no browser code fetches obstructions, so this is moot unless the plan exposes it.
- **LOW — flow regeneration cascade:** v2 `terrain_hashes`/`build_id` change whenever terrain `.bin` bytes change, so quantized terrain forces full flow regeneration on the retest pass.
