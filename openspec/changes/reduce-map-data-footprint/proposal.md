# Proposal: reduce-map-data-footprint

## Why

The repo carries ~60 GB of generated data: `processed_maps/` is 10.7 GB and is duplicated 1:1 into `www/` (another 10.7 GB) for the Android build. This already OOM-crashes the editor/agent environment and makes git, search, packaging, and CI painful. The flow simulation is not finalized yet, so this is the cheapest moment to change artifact formats before downstream consumers harden around them.

Profiling (2026-10-09, file listings/sizes only) shows where the 10.7 GB actually lives:

| Artifact class | Size | Notes |
|---|---|---|
| `*.json` (11,503 files) | 5.16 GB | `obstructions.json` whales: single files up to 182 MB, written with `indent=2` |
| `*.bin` (9,114 files) | 5.25 GB | terrain grids are raw float32 (1 MB each); flow fields already quantized uint8 |
| `*.png` (198 files) | 0.24 GB | minimaps/contourmaps - not worth touching |
| `heightmap.json.gz` (85 files) | 0.12 GB | already gzipped - NOT the problem |

## What Changes

- **Baseline first (before any format change):** add a regression harness that captures current artifact hashes plus behavioral fixtures (terrain costs at fixed cells, flow arrival times at fixed layers, firing solutions for fixed mortar/target pairs) so every later step is verified against the pre-change state.
- **Compact obstruction artifacts:** write `obstructions.json` with compact separators and round float coordinates to a documented precision. If compaction alone misses the size target, convert to a binary or gzipped form behind the same loader contract.
- **Quantize terrain grids:** convert float32 `terrain/*.bin` grids to uint8/uint16 with per-grid scale/offset recorded in the sidecar; bump the terrain artifact format version (1.1 -> 1.2) and keep the loader reading 1.0/1.1 (all-zero bridge mask fallback stays).
- **Optional gzip for `.bin` artifacts** if quantization alone misses the target; decided in design with measured numbers.
- **Cleanup pass:** delete orphaned artifacts (map folders not in the manifest, superseded format versions) after regeneration is verified.
- **Regenerate and resync:** rebuild `processed_maps/`, regenerate `www/` via `build-android.bat`, resync Android assets.
- **Explicitly NOT changing:** physics numbers (gravity 14.86, speed 148.64, range 1500), the `pixel_value / 65535.0 * height_scale` formula, heightmap 16-bit precision, and heightmap spatial resolution. Heightmaps are 0.12 GB of a 10.7 GB problem - downscaling them trades firing-solution accuracy for ~1% savings.

**Target:** `processed_maps/` + `www/` from ~21.4 GB combined to roughly 6-8 GB. (Note: this cannot yield "60 GB -> 7.5 GB" overall - `android/` is 28 GB of mostly Gradle/build outputs and `raw_map_data/` is 8 GB of source zips; neither shrinks.)

## Capabilities

### New Capabilities
- `map-artifact-regression`: baseline capture and comparison harness that snapshots artifact hashes and behavioral fixtures before a format change and verifies equivalence (within documented tolerances) after regeneration.

### Modified Capabilities
- `terrain-traversability`: the "Deterministic terrain artifacts" requirement changes - cost/feature grids gain a quantized serialization (dtype, scale, offset, sentinel) and a format version bump with backward-compatible loading.
- `map-processor`: obstruction artifact output gains a compact-serialization requirement (separators, coordinate precision, optional binary/gzip form) replacing the current pretty-printed JSON shape.

## Impact

- **Code (writers):** `processor/extract_obstructions.py`, `processor/terrain_artifact.py`, `processor/build_terrain_cost.py`, `processor/build_flow_fields.py` (sidecar/version fields only - flow grids already uint8).
- **Code (readers):** `calculator/static/js/app.js`, `calculator/static/js/heightmap.js`, and any terrain/flow loader in the UI; terrain loader must accept formats 1.0/1.1/1.2.
- **Tests:** new baseline harness under `processor/tests/`; existing suites (`test_terrain_artifact.py`, `test_terrain_cost.py`, `test_flow_field.py`, `test_obstruction_extraction.py`) act as anchors. `test_update_manifest.py` remains excluded from pytest runs (import-time checksum overwrite).
- **Data:** full regeneration of `processed_maps/`; `www/` rebuild; Android asset resync. Tracked files in git (340) change content; untracked bulk is regenerated.
- **Risk:** quantized terrain precision could shift flow arrival times and routing verdicts - mitigated by the baseline harness with documented per-artifact tolerances, and by doing this now while flow is not finalized.
- **No new dependencies** planned (NumPy + stdlib gzip/json suffice).
