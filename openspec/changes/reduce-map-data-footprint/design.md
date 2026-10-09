# Design: reduce-map-data-footprint

## Context

`processed_maps/` holds 10.7 GB of per-map artifacts and is duplicated 1:1 into `www/` for the Android build. Profiling (2026-10-09, listings/sizes only) shows two whales: `obstructions.json` files written with `indent=2` (single files up to 182 MB; 5.16 GB of JSON total) and float32 `terrain/*.bin` grids (1 MB each; 5.25 GB of `.bin` total, of which flow fields are already uint8). Heightmaps are already gzipped (0.12 GB total) and are explicitly out of scope. The flow simulation is not finalized, so artifact consumers are still few and soft - this is the cheapest moment to change formats. Existing precedent: `heightmap.json.gz` is already served and decoded in the browser, and terrain artifacts already carry a format version (1.0 -> 1.1 added `bridge_mask.bin` with an all-zero fallback for 1.0).

## Goals / Non-Goals

**Goals:**
- Cut `processed_maps/` (and therefore `www/`) by roughly 60-70%: target ~3-4 GB per copy.
- Establish a baseline/regression harness BEFORE any format change; every later step verified against it.
- Keep all formats decodable by stdlib Python + NumPy and native browser APIs (no new dependencies).
- Backward-compatible terrain loading: formats 1.0/1.1 keep working.

**Non-Goals:**
- No changes to physics numbers, the `/ 65535.0` elevation formula, heightmap precision, or heightmap spatial resolution.
- No shrink of `android/` (28 GB, mostly Gradle) or `raw_map_data/` (8 GB source zips).
- No re-architecture of the flow solver; sidecar/version fields only where already anticipated.
- No binary bespoke format for obstructions unless compaction + gzip measurably fails.

## Decisions

### D1: Obstructions - compact JSON, rounded coordinates, gzip (reuse heightmap pattern)
Write `obstructions.json.gz` with compact separators (`(',', ':')`) and float coordinates rounded to 0.1 m. Consumers rasterize obstructions into simulation cells (>= 1 m), so 0.1 m is far below the decision threshold.
- Alternatives: (a) `indent=2` kept - rejected, it is the whale; (b) bespoke binary - rejected for now: new parsers in two languages, junior-hostile, and the repo already proves the `.json.gz` pattern works end-to-end (writer: `process_maps.ipynb`/`compress_heightmaps.py`; reader: `heightmap.js`).
- Expected: 182 MB -> ~10-25 MB per large map (compact+round ~3x, gzip ~4-6x on repetitive numeric text). Measured on `fields_of_kassel` before rollout.

### D2: Terrain grids - per-grid quantization with scale/offset in sidecar (format 1.2)
- `elevation_mean`: uint16, per-grid min/scale in sidecar (~0.01 m resolution at typical height scales).
- Thresholded continuous grids (`slope_deg_max`, `edge_rise_m_max`, `edge_grade_max`): uint16 - uint8's ~0.35 deg step could flip extreme-slope cells near the blocking threshold.
- Non-thresholded diagnostics (`slope_deg_mean`, `roughness_m_mean`, `static_multiplier`, `vegetation_dense`): uint8 with per-grid min/scale.
- Masks (`water`, `road`, `bridge_mask`) already uint8: unchanged bytes.
- Sidecar gains per-grid `{dtype, offset, scale}` and `format_version: "1.2"`. Loader: 1.2 dequantizes; 1.0/1.1 read float32 as today (1.0 keeps all-zero bridge mask fallback).
- Alternatives: (a) all-uint8 - rejected, threshold flips; (b) gzip float32 without quantization - keeps 4-byte entropy, compresses worse than quantized integers, and still ships 4x the bytes pre-compression.
- Expected: ~7 MB of float32 grids per map -> ~2.5-3 MB.

### D3: Gzip for `.bin` - deferred, gated on measurement
After D1+D2, measure. If the combined target (~3-4 GB) is missed, gzip the `.bin` grids and decode in the browser with native `DecompressionStream('gzip')` (Chrome 80+, covers the Android WebView floor; no dependency). Do not speculatively add it.

### D4: Baseline harness before touching writers
New `processor/baseline.py` (stdlib + NumPy only) with `capture` and `compare` modes:
- **Capture (pre-change):** per map: sha256 of every artifact file; decoded fixtures for a fixed map set (adak, albasrah_2, muttrah_city_2 + the 5 largest obstructions maps): terrain cost/feature values at a fixed deterministic cell sample, flow arrival times at fixed cells per layer/class, obstruction record counts and bounding boxes.
- **Compare (post-regeneration):** masks and record counts must match exactly; dequantized grids must be within quantization error (<= scale/2 per cell); flow arrivals within a documented tolerance (proposal: <= 2% or <= 1 s, whichever is larger, with a cap on flipped unreachable cells); obstruction boxes within 0.1 m.
- Firing-solution spot check: the ballistics math is browser JS; if `node` can load the module directly, add M fixed mortar/target pairs to the harness, otherwise this stays a manual QA step and is recorded as a known ceiling.

### D5: Regenerate, verify, then clean up
Order: baseline capture -> writer changes -> regenerate all maps -> baseline compare -> rebuild `www/` (`build-android.bat`) -> Android sync -> delete orphaned artifacts (map folders absent from the manifest, superseded format files) -> commit. Rollback: everything regenerates from `raw_map_data/`; tracked files restorable from git; baseline snapshots kept until the change archives.

## Risks / Trade-offs

- [Quantization flips threshold cells (extreme slope, step hazards)] -> uint16 for thresholded grids; baseline compare caps allowed flips and reports exact cells.
- [Rounding obstruction coordinates shifts `static_multiplier` rasterization] -> 0.1 m is an order of magnitude below cell size; baseline compares rasterized multipliers, not just JSON text.
- [JS loader complexity for gzipped obstructions] -> reuse the existing `heightmap.js` decode path; no new dependency.
- [Regenerating 10 GB is slow and I/O heavy] -> run per-map with progress (existing pattern); capture baseline once, reuse for all compare runs.
- [www/ doubles every mistake] -> `build-android.bat` already regenerates `www/` from `calculator/` + `processed_maps/`; no new sync logic.
- [Known ceiling: firing-solution baseline may be manual] -> documented in harness header with the node-based upgrade path.

## Migration Plan

1. Land harness, capture baseline from current artifacts (pre-change state is the truth).
2. Change writers (obstructions compaction/gzip; terrain quantization + sidecar + version bump) behind the existing per-map CLI flags.
3. Update readers (terrain loader 1.0/1.1/1.2; obstructions `.gz` decode).
4. Regenerate `processed_maps/`, run baseline compare, iterate until tolerances pass.
5. Rebuild `www/`, `npx cap sync android`, smoke-test one map end-to-end in browser.
6. Cleanup pass (orphans, superseded files), update AGENTS.md format references.

## Open Questions

- Does the browser load `terrain/*.bin` today, or only flow bins + rendered layers? (Scopes reader work; answer during task 1 code read.)
- Exact obstruction coordinate precision consumers need (0.1 m assumed; confirm against `build_terrain_cost.py` rasterization).
- Node availability for a firing-solution baseline (else manual QA ceiling).
