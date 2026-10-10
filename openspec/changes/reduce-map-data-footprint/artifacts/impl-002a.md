# Implementation Report — impl-002a (baseline comparator repair)

2026-10-10. OpenSpec change `reduce-map-data-footprint`. **Worklog revision 2 read and confirmed before any edit.** Scope executed exactly as briefed: repair the baseline comparator per `artifacts/review-001.md`, add synthetic negative tripwire tests, report. Files touched: `processor/baseline.py`, `processor/tests/test_baseline.py`, this report. **Not touched:** `baseline_firing.mjs` (Worker B scope), `baseline-pre-change.json`, `compare-unchanged-report.json`, `tasks.md`, all generated data, unrelated dirty flow files. No subagents dispatched. No new dependencies (stdlib + NumPy only). Public API preserved: `main(argv=None)`, `_cmd_compare(args)`, `compare_maps(baseline_maps, current_maps, max_flow_flips)`, `_grid_fixture(bin_path, entry, rows, cols)`.

Environment fingerprint: Windows, Python 3.11.4, NumPy 1.26.4, Node v24.11.0.

## What changed in `processor/baseline.py`

| Review finding | Fix |
| --- | --- |
| C-01 (report accepted as baseline) | `_cmd_compare` rejects missing/wrong `format` and missing/empty/non-object `maps` with exit 2 **before** any map data is read. |
| C-02 (unknown map passes) | Requested `--maps` names absent from the baseline now exit 2 (was: warning + pass/0). Zero-coverage compares are impossible by construction. |
| C-03 (sampling rule unchecked, zip truncation) | Doc-level: stored `sampling.seed`/`count` must equal this harness's constants, else exit 2. Per-grid (terrain **and** flow): new `_sampling_ok()` requires stored indices to equal `sample_indices(rows*cols)` and `len(values) == len(indices)` before any value comparison; mismatch is a `sampling_integrity` exceedance (exit 1), never silent zip truncation. |
| B-03 / C-05 (blocked sentinel not enforced) | `capture_terrain` now records the sidecar's `blocked_sentinel`. `_compare_terrain` flags a sentinel change as an exceedance, and on `cost.bin` grids any sampled cell equal to the sentinel on either side must be **exactly** equal on the other side (`blocked_sentinel_exact`, tolerance 0) — scale/2 never applies. Contract source: `specs/terrain-traversability/spec.md` quantized round-trip scenario, "blocked/unreachable sentinel cells decode to the exact documented sentinel" — not ambiguous, no format invented. Old baselines lacking `blocked_sentinel` fall back to the current sidecar's value; if neither side has it, a note (not a failure) is recorded. |
| C-06 (firing skip invisible) | All compare notes are now printed as `NOTE ...` lines on stdout even without `--report`. `unavailable` remains a note, exit stays 0 — not promoted to hard fail, per brief. |

Module docstring gained a "Compare integrity (fail-closed)" paragraph; the existing known-ceilings note is unchanged.

## Tripwire evidence — old code first

CLI probes against the **unrepaired** code (both reproduced review-001):

- `compare --baseline .../compare-unchanged-report.json` → `compare: pass (0 exceedances)`, **exit 0** (report accepted as baseline, zero maps).
- `compare --baseline .../baseline-pre-change.json --maps not_a_map` → warning, `pass`, **exit 0**.

Synthetic tripwires: 10 new tests were added to `test_baseline.py` **before** touching `baseline.py` and run against the old code: **8 failed, 12 passed**. The 8 failures are exactly the repaired holes: report-as-baseline, empty/wrong format, unknown map names, seed/count mismatch, shortened sample arrays, reordered flow indices, quantized sentinel drift within scale/2, firing note visibility. The 2 new tests that already passed on old code (`corrupt baseline` — JSON decode already exited 2; `exact quantized sentinel passes` — positive guard) behave identically on new code.

## Verification after repair (all actually run)

- `python -m pytest processor/tests/test_baseline.py -q` → **20 passed, exit 0** (final run 8.79 s; repeated stable).
- CLI probes now fail closed: report-as-baseline → exit 2 ("a compare report is not a baseline"); `--maps not_a_map` → exit 2 ("requested map(s) not in baseline").
- Real-data read-only probe: `compare --baseline .../baseline-pre-change.json --maps adak` → exit 1 with **exactly 2 exceedances, both `firing_mils`**: `C4-5->E5-5` 1350.852789 → 1353.218993, `F11-5->D10-5` 1347.007456 → 1352.136815 (tolerance 0.5). Terrain, flow, obstructions, and all new sampling-integrity checks passed on real adak data; zero sentinel exceedances. Report written to `$TEMP\adak-compare-probe.json` (outside protected trees), not committed.
- Broad safe suite: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py -q` → **exit 1: 4 failed, 110 passed, 8 errors**. NOT green. Failures are in `test_flow_field.py` (2), `test_terrain_artifact.py` (2), errors in `test_terrain_cost.py` (8) — the identical failure set review-001 recorded (then 4 failed / 100 passed / 8 errors; +10 passed are the new baseline tests). I did not modify those files; consistent with the dirty flow-simulator tree and the documented `terrain_generation_id` loader blocker. Attributed as pre-existing by matching review-001's recorded set, not by independent bisection.
- Editor diagnostics: no errors in either edited file.

## Known issues / deviations / unknowns

- **Firing baseline is stale, by design.** `git status` shows `processor/baseline_firing.mjs` modified in the working tree vs HEAD `0976b65` (+58/-43) — the Worker B Y-orientation fix. The tracked baseline JSON holds pre-fix values, so adak firing compare fails until the authorized recapture. The drift matches review-001 B-01's measurement (1350.853 → ~1353.219), corroborating that finding. Recapture was explicitly NOT in my scope and was not performed.
- Two transient `KeyboardInterrupt` aborts interrupted mid-suite pytest runs at unrelated lines (sha256 read loop; compare loop) before a clean 20-pass run; no code cause found, treated as environment noise. Recorded for honesty.
- Broad-suite failures attributed to pre-existing causes by failure-set match with review-001, not by rerunning them on a clean tree.
- No generated-data mutation; no bulk reads of `processed_maps/` beyond the single-map adak compare (normal harness behavior).

## Gate status

The comparator is now fail-closed on zero coverage, wrong documents, tampered sampling, and sentinel drift. Per worklog revision 2 the baseline gate stays **closed** until: Worker B's firing fixture is finalized, the pre-change baseline is recaptured (all eight maps, twice, outside protected trees), an unchanged compare passes, and a fresh independent review approves.
