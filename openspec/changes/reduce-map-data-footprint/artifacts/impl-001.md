# impl-001 — Baseline regression harness (tasks 1.2, 1.3, 1.4)

## Status

COMPLETE. All five verification steps ran and passed; results below are copied from real runs.

Environment fingerprint: Windows 11 (pwsh), Python 3.11.4, NumPy 1.26.4, node v24.11.0, branch `feat/opening-flow-simulator` (dirty working tree, not touched). Date: 2026-10-09.

## Objective

Build the pre-change safety net for `reduce-map-data-footprint`: `processor/baseline.py` with `capture` / `compare` subcommands that snapshot the 8 fixed maps' artifacts (file hashes + decoded behavioral fixtures) and verify regenerated artifacts within the spec's tolerances. Stdlib + NumPy only, read-only against `processed_maps/` and `raw_map_data/`, no processor-module imports.

## Changes Made

- `processor/baseline.py` (new, ~640 lines): CLI with `capture` / `compare`. Per map: (1) streamed sha256+size of every file under `processed_maps/<map>/` (informational, never fails compare); (2) terrain fixtures — every `.bin` under `terrain/` (diagnostics from the sidecar's own `dtype`, masks `road_mask/water/bridge_mask`, per-profile `cost.bin`/`classes.bin`), decoded via sidecar shape + `np.fromfile`, sampled at 64 deterministic flat indices (`default_rng(20261009)` fresh per grid, rule recorded in the document header); (3) flow fixtures — v1 `team<N>/<class>.bin` layer-root grids plus the ACTIVE v2 generation resolved via `class_manifest.json` (keyed `<layer>/v2/...`, never by build_id, which legitimately changes on regeneration), sampled values stored as arrival seconds (`None` = 255 sentinel) plus whole-grid unreachable counts; (4) obstruction fixtures — total/per-type/road-triangle counts, bbox, and a normalized sha256 over records with every float rounded to 0.1 m (idempotent: survives the planned rounding + gzip); reads `obstructions.json` or `obstructions.json.gz`; (5) firing fixture via subprocess for `adak` + `muttrah_city_2` only, recording `{"status": "unavailable", "reason": ...}` and continuing on any failure (documented known ceiling). Compare enforces: masks/counts/sentinels exact; continuous grids exact when the NEW sidecar is unquantized, else `<= scale/2` from the NEW sidecar's quantization entry; flow arrivals `<= max(2% baseline, 1.0 s)` with flips `<= --max-flow-flips` (default 0); obstruction hash exact, bbox within 0.1 m; firing mils within 0.5. Exit 0/1/2; `--report` writes JSON; refuses to write outputs inside `processed_maps/` or `raw_map_data/`. No timestamp in the document, so repeat captures are byte-identical.
- `processor/baseline_firing.mjs` (new): headless node ESM script; gunzips `heightmap.json.gz` (node:zlib), reads `metadata.json` for `height_scale`, computes 3 fixed grid-ref pairs (`C4-5→E5-5`, `H7-5→J9-5`, `F11-5→D10-5`; max ~890 m on a 4096 m map, inside the 1500 m range) using `coordinates.js` + `ballistics.js`, with bilinear elevation `(pixel/65535.0)*height_scale` mirrored from `calculator/tests/test_in_game.js`. Prints JSON to stdout.
- `processor/tests/test_baseline.py` (new, 10 tests): synthetic 16×16 map folders under `tmp_path`; covers round-trip pass, byte-identical re-capture, mask flip → exit 1 with correct report fields, quantized-within-scale/2 pass, quantized-beyond-scale/2 fail (synthesized 1.2-style sidecar entry), flow arrival drift fail, unreachable-count + flip fail, dropped obstruction record fail, firing skipped for non-firing maps, and output-inside-`processed_maps/` refusal.
- `openspec/changes/reduce-map-data-footprint/artifacts/baseline-pre-change.json` (new, 2,447,993 bytes): the captured pre-change baseline (task 1.5's artifact; not committed — no git operations performed per constraints).
- `openspec/changes/reduce-map-data-footprint/artifacts/compare-unchanged-report.json` (new): the exit-0 compare report.

## Verification

1. `python -m pytest processor/tests/test_baseline.py -q` → **PASS** (`10 passed in 4.52s`).
2. `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py -q` → **PASS (as specified)**: `4 failed, 100 passed, 8 errors in 15.29s`. Failures are exactly the pre-existing ones: `test_flow_field` ×2, `test_terrain_artifact` ×2, 8 errors all in `test_terrain_cost.py`. No new failures; the 100 passed include the 10 new tests. Pre-existing breakage not touched.
3. `python processor/baseline.py capture --out openspec/changes/reduce-map-data-footprint/artifacts/baseline-pre-change.json` → **PASS**: completed all 8 maps; runtime **179.9 s**; output **2,447,993 bytes** (2.4 MB).
4. Second capture to `%TEMP%/baseline-second.json` → **PASS**: `BYTE_IDENTICAL=True` (2,447,993 bytes, exact match). The document contains no timestamp, so nothing was excluded from the determinism check.
5. `python processor/baseline.py compare --baseline .../baseline-pre-change.json --report .../compare-unchanged-report.json` → **PASS**: `compare: pass (0 exceedances)`, `COMPARE_EXIT=0`, report `result: pass`, notes empty, files informational `added/changed/missing = 0` for all maps.

Spot checks on the real baseline document: adak has 655 hashed files, 14 terrain grids (format 1.0), 93 flow grids (v1 + active v2); albasrah_2 decoded as format 1.1 with `bridge_mask.bin` captured; firing fixture `status: ok` for both adak and muttrah_city_2 (all 3 pairs valid, e.g. adak `C4-5→E5-5`: 1350.852789 mils); fields_of_kassel obstructions: 44,783 records, 638,676 road triangles.

## Acceptance Criteria checklist

- [x] `capture`/`compare` subcommands, stdlib + NumPy only, read-only against `processed_maps/`/`raw_map_data/` (verified: guard test + no writes observed; only reads).
- [x] Fixed DEFAULT_MAPS = adak, albasrah_2, muttrah_city_2, fields_of_kassel, ascheberg, korbach_offensive, road_to_damascus, shijiavalley; `--maps` override works.
- [x] Per-map sha256+size of every file, informational only.
- [x] Terrain fixtures: sidecar-driven dtype/shape, deterministic 64-cell sample, sampling rule in header, floats rounded to 6 decimals.
- [x] Flow fixtures: per layer/team/class arrival grids, seconds + unreachable counts; active v2 generation resolved via `class_manifest.json`.
- [x] Obstruction fixtures: counts, bbox, normalized 0.1 m hash; `.gz` variant supported.
- [x] Firing fixture: node subprocess for adak + muttrah_city_2; unavailable → record and continue (known ceiling).
- [x] Compare tolerances exactly as specified; per map/artifact/cell exceedance reporting; exit 0/1/2; `--report` JSON; `--max-flow-flips`.
- [x] Tests: round-trip, determinism, mask flip, quantized within/beyond scale/2, flow drift, dropped obstruction record — all pass.
- [x] Real-data capture, byte-identical re-capture, exit-0 compare on unchanged data.

## Decisions Made

- **No timestamp in the baseline document.** Determinism requirement is "byte-identical"; omitting the field is simpler than excluding it from diffs.
- **Flow v2 fixtures keyed `<layer>/v2/team<N>/<class>`, not by build_id.** `v2_build_id` hashes terrain bytes, so it changes on every terrain regeneration; keying by it would make every post-change compare fail spuriously. Active build_id is recorded informationally per layer. Stale (non-active) generations are hashed (files section) but not fixture-sampled.
- **Flow values stored as seconds** (`raw * quantum_s`, `None` for 255), not raw uint8: the quantum legitimately changes between runs; seconds are the semantic quantity the tolerance is expressed in.
- **Grid classification (mask vs continuous) is sidecar-driven**: integer dtype without a quantization entry → mask (exact); float dtype or any quantization entry → continuous. This keeps `classes.bin` exact while letting 1.2-quantized uint8/uint16 continuous grids use the scale/2 rule.
- **1.2 quantization contract** (`{dtype, offset, scale}` nested under a grid entry's `quantization` key, as top-level entry keys, or in a sidecar-level `quantization` dict keyed by terrain-relative path) is resolved in one function, `_entry_with_quant()` — the single point of change if the phase-3 writer picks a different shape. Documented in the module header.
- **Normalized obstruction hash rounds every float in every record to 0.1 m** (not just x/y): rounding is idempotent, so the hash matches whether or not the future writer rounds any given numeric field.
- **Missing baseline-keyed artifacts at compare = failure; extra new artifacts = note only.** Regeneration must reproduce the baseline layout; additions are not behavioral drift of captured fixtures.
- **Firing unavailability on either side = note, not failure** (documented known ceiling; prevents a missing node install from masking or faking drift verdicts).

## Failures and Recovery

None. No test failures, no capture/compare errors, no retries needed. The pre-existing suite breakage (4 failed + 8 errors, all in `test_flow_field`/`test_terrain_artifact`/`test_terrain_cost`, caused by the in-flight `terrain_generation_id` refactor per research-002) was left untouched as instructed.

## Risks-Notes

- The harness decodes artifacts directly and does NOT import `processor/terrain_artifact.py` (mid-refactor in the dirty tree); if the 1.2 writer's sidecar shape differs from the contract above, update `_entry_with_quant()` only.
- Capture runtime is ~3 min for the 8 maps (dominated by ~780 MB of obstructions JSON parsing + hashing ~several GB of flow generations). One map at a time with `gc.collect()`; peak memory stayed bounded (largest single parse: fields_of_kassel, 182.6 MB).
- Compare currently re-decodes everything capture does; runtime is therefore similar (~3 min). Acceptable for a phase-4 gate.
- The firing fixture covers only adak + muttrah_city_2 and requires node on PATH; phase 4.4's spot check can reuse `processor/baseline_firing.mjs` directly for other maps if wanted.
- The baseline document (2.4 MB) is small JSON and safe to commit in task 1.5; `processed_maps/` was never modified (read-only verified by the unchanged file-hash informational section: 0 added/changed/missing across all 8 maps between two captures).

## Files Modified

Created only (no existing files modified, no git commits):

- `processor/baseline.py`
- `processor/baseline_firing.mjs`
- `processor/tests/test_baseline.py`
- `openspec/changes/reduce-map-data-footprint/artifacts/baseline-pre-change.json`
- `openspec/changes/reduce-map-data-footprint/artifacts/compare-unchanged-report.json`
- `openspec/changes/reduce-map-data-footprint/artifacts/impl-001.md` (this report)
