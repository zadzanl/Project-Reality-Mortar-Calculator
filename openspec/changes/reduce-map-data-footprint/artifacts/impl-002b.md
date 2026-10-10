# Implementation Record — impl-002b (Worker B: firing fixture production elevation path)

2026-10-10. OpenSpec change `reduce-map-data-footprint`. Worklog **revision 2 read and confirmed** before starting (Worker B handoff: `processor/baseline_firing.mjs`, focused Node regression test, this artifact; production Y orientation; no changes to production heightmap or physics).

## Scope and files touched

- `processor/baseline_firing.mjs` — MODIFIED (only in-scope source file).
- `processor/tests/test_baseline_firing.mjs` — NEW regression test.
- `openspec/changes/reduce-map-data-footprint/artifacts/impl-002b.md` — this file.

NOT touched by this worker: `processor/baseline.py`, `processor/tests/test_baseline.py` (both show uncommitted modifications in `git status` — those are Worker A's parallel edits per worklog revision 2, left untouched), `calculator/static/js/heightmap.js` (clean), `artifacts/baseline-pre-change.json` (clean), no generated-data trees, no tasks.md. No new dependencies. No subagents dispatched.

## Environment

- Windows, pwsh. Node.js **v24.11.0** (observed in review-001 and re-confirmed by test runs). No Python needed for this handoff.

## Finding being fixed (review-001, B-01)

Pre-fix `baseline_firing.mjs` interpolated the raw south-first heightmap array WITHOUT the Y flip, while production `calculator/static/js/heightmap.js::getElevation` (lines ~357-365) flips Y (`flippedPixelY = (resolution - 1) - pixelY`; storage row 0 = south, world Y=0 = north). The app calls the production lookup (`app.js` ~970-971), so the fixture did not reflect the production path.

## Pre-edit tripwire (expected FAIL — confirmed)

Throwaway probe (temp file, deleted after run) compared the exact pre-fix formula against production `getElevation` on real `processed_maps/adak` at the six fixed grid references:

```
C4-5: old=24.411904 production=72.000806 diff=47.588902
E5-5: old=0.748241 production=22.760026 diff=22.011785
H7-5: old=14.037509 production=14.037509 diff=0.000000
J9-5: old=0.000000 production=0.000000 diff=0.000000
F11-5: old=22.923683 production=38.186131 diff=15.262448
D10-5: old=38.730789 production=0.768664 diff=-37.962125
TRIPWIRE: 4/6 samples MISMATCH - old fixture does not match production path
exit=1
```

(H7-5/J9-5 sit on flat terrain, so the flip is invisible there; 4/6 samples diverge by up to ~47.6 m.)

Pre-edit run of the new regression test also failed as expected:

```
node --test processor/tests/test_baseline_firing.mjs
SyntaxError: The requested module '../baseline_firing.mjs' does not provide an export named 'computePairs'
tests 1 / pass 0 / fail 1, exit=1
```

## Change made

`processor/baseline_firing.mjs`:

- Deleted the local `getElevationAtXY` bilinear copy. Elevation now comes from imported production `getElevation` (`../../calculator` -> `../calculator/static/js/heightmap.js`) via a thin exported wrapper `elevationAt(heightmap, metadata, x, y)`. `/65535.0` formula, physics constants, coordinate conventions untouched (all live in the production modules, which were not modified).
- Refactored for testability, preserving the CLI contract exactly: exported `loadMap(mapDir)` (gunzip + `Uint16Array` conversion, unchanged logic), `elevationAt(...)`, `computePairs(heightmap, metadata, pairs = PAIRS)`. `main()` runs only when invoked as CLI (`import.meta.url === pathToFileURL(resolve(process.argv[1])).href` guard); stdout JSON structure `{"map": ..., "pairs": [...]}` and exit codes (2 usage, 1 error) unchanged.
- Header comment updated: documents the production elevation path and forbids reimplementing it locally.

`heightmap.js` is pure ESM with no top-level browser references (`fetch`/`window` only inside loader functions), so importing `getElevation` in Node is safe — verified by the passing runs below. Production `getElevation` was suitable for Node; no second implementation was written.

## Post-edit verification (all commands actually run by this worker)

1. `node --test processor/tests/test_baseline_firing.mjs` — **6/6 pass, exit 0**:
   - loader gunzips and converts data to `Uint16Array` (16-bit) — pass
   - `elevationAt` matches production `getElevation` with Y flip, integer pixels, **Y=0 north edge reads storage row 3**, south edge reads row 0, corner (0,0) — pass
   - bilinear at non-center fractional pixels on asymmetric 4x4 south-first synthetic map (flipped vs unflipped differ by construction) — pass
   - `computePairs` output deep-equals full production `calculateFiringSolution` at fixed grid refs (incl. mortar exactly at (0,0)) — pass
   - regression guard: pre-fix unflipped formula disagrees with fixture output — pass
   - CLI preserved: `node baseline_firing.mjs <map_dir>` prints the same JSON shape with default 3 pairs — pass
2. `node processor/baseline_firing.mjs processed_maps/adak` — **exit 0**, all three pairs `valid: true, status: "OK"`. Notably `C4-5 -> E5-5` now yields `elevationMils: 1353.218993`, matching the production-lookup figure (~1353.219) quoted in review-001, vs the stale fixture's 1350.852789.

Synthetic test map: resolution 4, map_size 3000 m, height_scale 100, `value(yy,xx) = xx*100 + yy*10000` (max 30300, uint16), written to an OS temp dir and deleted after the run. No files under `processed_maps/` or `raw_map_data/` were created, modified, or deleted.

## Attempt log

1. Read worklog (revision 2 confirmed), review-001, production `heightmap.js`, `coordinates.js`, `ballistics.js`, spec `map-artifact-regression`.
2. Wrote tripwire probe; first run failed with `ERR_UNSUPPORTED_ESM_URL_SCHEME` (Windows ESM requires `file:///` URLs for absolute imports) — fixed imports, reran: 4/6 mismatch, exit 1 (expected).
3. Wrote `test_baseline_firing.mjs`; pre-edit run failed on missing exports (expected red).
4. Edited `baseline_firing.mjs` (production `getElevation` + exports + CLI guard).
5. First post-edit test run: 5/6 pass; one failure traced to MY hand-computed expectation in the fractional-pixel test (used wrong raw values 1100/1200/2100/2200 instead of 10100/10200/20100/20200 for rows 1-2). Fixture code was correct; fixed the test expectation. Rerun: 6/6 pass, exit 0.
6. Adak CLI run: valid pairs, exit 0. Deleted the throwaway probe. Confirmed via `git status` that only `baseline_firing.mjs` (M) and `test_baseline_firing.mjs` (??) changed among my in-scope files.

## Consequences and unknowns

- **Baseline firing data is now STALE**: `artifacts/baseline-pre-change.json` firing values (tracked at commit `0976b65`) were captured with the unflipped path and must be recaptured by the orchestrator (outside generated-data trees) before the baseline gate can close. Not recaptured here — outside this handoff's scope and authorization.
- Not verified by this worker: `baseline.py`'s subprocess invocation of the fixture end-to-end (Worker A owns `baseline.py`; CLI contract and JSON shape were preserved and CLI-tested, so no interface break is expected, but the integration was not run here).
- Not run by this worker: the Python suite (`test_baseline.py` etc.) — out of scope; review-001 B-02's true suite status remains Worker A's/orchestrator's reporting duty.
- Known ceiling (unchanged): fixture unavailability still degrades to "unavailable" in `baseline.py`, not a hard failure.
