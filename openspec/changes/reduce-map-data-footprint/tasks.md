# Tasks: reduce-map-data-footprint

## 1. Baseline Harness (before any format change)

- [x] 1.1 Read current readers/writers to pin the loader contract: `processor/extract_obstructions.py`, `processor/terrain_artifact.py`, `processor/build_terrain_cost.py`, `processor/build_flow_fields.py`, `calculator/static/js/app.js`, `calculator/static/js/heightmap.js`. Answer the design open questions: does the browser load `terrain/*.bin` today; what coordinate precision does `build_terrain_cost.py` rasterization actually need; can `node` load the ballistics module for a firing-solution fixture. (Answers: NO browser terrain/obstructions loading - processor-only readers; cell_m min 4.0 m so 0.1 m rounding safe; node YES - ballistics.js is pure ESM. See artifacts/research-001/002/003.md)
- [x] 1.2 Implement `processor/baseline.py` with `capture` mode: per-map sha256 of every artifact plus decoded fixtures (terrain grids at deterministic sampled cells, flow arrivals per layer/class at fixed cells, obstruction record counts and bounding boxes) for the fixed map set (adak, albasrah_2, muttrah_city_2 + 5 largest obstructions maps). Stdlib + NumPy only, read-only against `processed_maps/` and `raw_map_data/`.
- [x] 1.3 Implement `compare` mode with tolerances from the `map-artifact-regression` spec (masks/counts/sentinels exact; grids within scale/2; flow arrivals within documented tolerance with capped unreachable flips; per-map/per-cell failure report).
- [x] 1.4 Add regression tests for the harness itself under `processor/tests/` and run the safe suite: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`. (10 new tests pass; suite shows only the 4 failed + 8 errors pre-existing from the in-flight flow-simulator change)
- [x] 1.5 Capture the pre-change baseline from current `processed_maps/` and commit the baseline document (it is small JSON, not bulk data). (artifacts/baseline-pre-change.json, 2.4 MB, byte-identical on re-capture, compare exit 0)

## 2. Obstructions Compaction

- [ ] 2.1 Change `extract_obstructions.py` to write `obstructions.json.gz` with separators `(',', ':')` and coordinates rounded to 0.1 m; report per-map uncompressed/compressed sizes. Verify on `fields_of_kassel` (182 MB pretty-printed): confirm >= 5x compressed reduction and record count/bbox equality within 0.1 m.
- [ ] 2.2 Update all obstructions readers (terrain pipeline + any UI path found in 1.1) to decode gzip, reusing the `heightmap.js` pattern in the browser (native `DecompressionStream`, no new dependencies).
- [ ] 2.3 Update `processor/tests/test_obstruction_extraction.py` for the new serialization and rerun the safe pytest suite.

## 3. Terrain Grid Quantization (format 1.2)

- [ ] 3.1 Add quantized serialization to `processor/terrain_artifact.py`: uint16 for thresholded grids (`slope_deg_max`, `edge_rise_m_max`, `edge_grade_max`, `elevation_mean`), uint8 for non-thresholded diagnostics, masks unchanged; per-grid `{dtype, offset, scale}` in the sidecar; `format_version: "1.2"`.
- [ ] 3.2 Update the terrain loader to accept 1.0/1.1 (float32; 1.0 all-zero bridge mask) and 1.2 (dequantize via `offset + q * scale`, exact sentinel handling).
- [ ] 3.3 Update `processor/build_terrain_cost.py` and `processor/build_flow_fields.py` to consume dequantized grids without recomputing terrain physics.
- [ ] 3.4 Update `processor/tests/test_terrain_artifact.py` and `test_terrain_cost.py` for quantized round-trip (within scale/2, exact sentinels) and legacy-format loading; rerun the safe pytest suite.

## 4. Regenerate, Verify, Measure

- [ ] 4.1 Regenerate all maps (`extract_obstructions.py`, `build_terrain_cost.py`, `build_flow_fields.py` per map, excluding `the_falklands`).
- [ ] 4.2 Run baseline `compare`; iterate on writer bugs until all tolerances pass. Record the final comparison report in the change artifacts.
- [ ] 4.3 Measure resulting `processed_maps/` size. If the ~3-4 GB target is missed, apply design decision D3 (gzip `.bin` grids, native browser decode) and re-verify; otherwise skip D3 and record why.
- [ ] 4.4 Firing-solution spot check: node-based fixture if 1.1 confirmed feasibility, else manual QA of fixed mortar/target pairs on adak and muttrah_city_2 with results recorded (documented known ceiling).

## 5. Cleanup and Resync

- [ ] 5.1 Delete superseded artifacts (old `obstructions.json`, stale format files) and orphaned map folders absent from the manifest; confirm no loader references remain via search.
- [ ] 5.2 Rebuild `www/` via `build-android.bat` and run `npx cap sync android`; smoke-test one map end-to-end in the browser (map load, layer toggles, one firing solution).
- [ ] 5.3 Update AGENTS.md format references (terrain format 1.2, `obstructions.json.gz`, baseline harness usage) and `processed_maps/README.md` if it names formats.
- [ ] 5.4 Final safe pytest run + baseline compare re-run; report exactly what was verified and final sizes.
