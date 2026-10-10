# Implementation Report — impl-003 (baseline gate operator-safety repair)

2026-10-10. OpenSpec change `reduce-map-data-footprint`. **Worklog revision 5 read and confirmed before any edit.** Scope executed exactly as briefed: repair the two blocking CLI safety defects from `artifacts/review-003.md` (R-003-B01 empty `--maps` passes; R-003-B02 same-path `--report` overwrites baseline), make subset coverage and truncation guidance accurate (R-003-C02, R-003-C03), add focused negative tests, report. Files touched: `processor/baseline.py`, `processor/tests/test_baseline.py`, this report. **Not touched:** `baseline_firing.mjs`, Node tests, `baseline-pre-change.json`, `compare-unchanged-report.json`, `tasks.md`, `worklog.md` (its pre-existing dirty state predates this task), `.gitignore`, all generated data, unrelated dirty flow files. No subagents dispatched. No new dependencies (stdlib + NumPy only). Public CLI preserved: same subcommands, same flags, same exit-code contract (0 pass / 1 exceedances / 2 usage or I/O error).

Environment fingerprint: Windows, Python 3.11.4, NumPy 1.26.4, Node v24.11.0.

## Tripwire evidence — old code first (both review-003 defects reproduced)

Run against the **unrepaired** code before any edit:

- `python processor/baseline.py compare --baseline .../baseline-pre-change.json --maps ","` → `compare: pass (0 exceedances)`, **exit 0**, zero maps read. `--maps "  "` (whitespace) → identical, **exit 0**.
- Same-path overwrite on a temp copy of the real baseline: `compare --baseline $TEMP\tripwire-baseline.json --report $TEMP\tripwire-baseline.json --maps adak` → `compare: pass (0 exceedances)`, **exit 0**; temp file went from SHA-256 `A7D9D14DD9EB058D8D8DDA21E57239D201D3C5985ACB7F008BDD32D8B01EAD29` (2,448,239 bytes) to `DCD810F35FC04B8E5BFD36248FCBFBDFC99F0F9AAE6A5FDEA4280B7E7E59AAB5` (404 bytes). **Baseline destroyed, `OVERWRITTEN=True`.** The committed artifact was never touched (probe used a copy).

## What changed in `processor/baseline.py`

| Review finding | Fix |
| --- | --- |
| R-003-B01 (delimiter-only `--maps` passes with zero coverage) | `_parse_maps` now distinguishes `None` (omitted → default set) from an explicit argument that parses to an empty list: the latter raises `ValueError` with an actionable message, which `main()` converts to **exit 2**. Applies to both capture and compare. Compare's guard changed from `if args.maps` to `if args.maps is not None` so an explicit empty/whitespace argument can never fall through to the full default set. A valid nonempty subset (`--maps adak`) is unchanged. |
| R-003-B02 (`--report` == `--baseline` overwrites the gate artifact) | `_cmd_compare` rejects equal resolved paths (`Path.resolve()`, strict=False) with exit 2 **before** the baseline is read, any map is captured, or any file is written. Baseline bytes are trivially unchanged. A distinct report path remains valid. |
| R-003-C02 (subset compare indistinguishable from full gate) | Final console line now prints explicit coverage: `compare: pass (0 exceedances; 1/8 maps)` for a subset, `8/8` for full. The JSON report already recorded `maps_compared`; this closes the console-only operator gap. |
| R-003-C03 (truncation hint implies an unrequested report) | The >50-exceedance line says `... and N more (see --report)` only when `--report` was given; otherwise `... and N more (rerun with --report for full details)`. |

Module docstring gained an "Operator safety (fail-closed; review-003 repairs)" paragraph. Not done (out of scope, recorded in review-003 as nonblocking or separately gated): C-01 artifact tracking policy, C-04 tolerance prose duplication, C-05 atomic capture write.

## What changed in `processor/tests/test_baseline.py`

Ten new focused tests appended under a review-003 tripwire banner; all 20 pre-existing tests untouched:

- `test_capture_rejects_delimiter_only_maps["," / ",," / "   "]` — exit 2, no output file written.
- `test_compare_rejects_delimiter_only_maps["," / ",," / "   "]` — exit 2.
- `test_compare_rejects_report_path_equal_to_baseline` — exit 2 and baseline bytes byte-identical before/after.
- `test_compare_distinct_report_path_still_valid` — positive guard, exit 0, report written.
- `test_compare_prints_subset_and_full_coverage` — two-map synthetic baseline; subset prints `1/2 maps`, full prints `2/2 maps`.
- `test_truncation_hint_matches_report_request` — 64 sampled mask flips (>50 cap); without `--report` the hint says `rerun with --report for full details`, with `--report` it says `see --report`.

## Verification after repair (all actually run, real outputs)

- `python -m pytest processor/tests/test_baseline.py -q -p no:cacheprovider` → **30 passed, exit 0** (11.87 s).
- CLI probes against the committed baseline `baseline-pre-change.json`:
  - `--maps ","` → `error: --maps ',' selects zero maps; ...`, **exit 2**. `--maps ",,"` → **exit 2**. `--maps "  "` → **exit 2**.
  - `capture --out $TEMP\should-not-exist.json --maps ","` → **exit 2**, file not created (`CAPTURE_WROTE=False`).
  - Same-path probe on a fresh temp copy: `compare --baseline $TEMP\tripwire-baseline-fixed.json --report $TEMP\tripwire-baseline-fixed.json --maps adak` → `error: --report path resolves to the --baseline path ...; refusing to overwrite the baseline`, **exit 2**; SHA-256 before == after == `A7D9D14DD9EB058D8D8DDA21E57239D201D3C5985ACB7F008BDD32D8B01EAD29` (`PRESERVED=True`).
  - Subset: `compare --baseline .../baseline-pre-change.json --maps adak` → `compare: pass (0 exceedances; 1/8 maps)`, **exit 0**.
  - Full unchanged: `compare --baseline .../baseline-pre-change.json` → `compare: pass (0 exceedances; 8/8 maps)`, **exit 0**. Eight maps read, zero exceedances.
- Node compatibility check: `node --test processor/tests/test_baseline_firing.mjs` → **pass 6, fail 0, exit 0**.
- `git diff --check -- processor/baseline.py processor/tests/test_baseline.py` → clean, exit 0.
- `git status --short` on scoped paths: only `processor/baseline.py` and `processor/tests/test_baseline.py` modified by this task (plus this report, untracked under the ignored `artifacts/` rule). The `worklog.md` modification predates this task and was not made by me.

## Known issues / deviations / unknowns

- **Broad safe suite NOT rerun in this task.** Its last recorded truth stands: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py -q` → **exit 1: 4 failed, 110 passed, 8 errors** (worklog revisions 3–5; the +10 new tests here would make it 120 passed, same expected failures, but that run was not performed — no claim made). Failures are the pre-existing `test_flow_field.py` / `test_terrain_artifact.py` / `test_terrain_cost.py` set attributed to the dirty flow-simulator tree and the `terrain_generation_id` loader blocker.
- **R-003-C01 (artifact tracking policy) not resolved here** — explicitly outside the bounded handoff (`.gitignore` / commit policy). This report is written under the ignored `artifacts/` path like its predecessors; durability depends on the force-add policy the next gate must resolve.
- Full compare reads all eight maps from `processed_maps/` (normal harness behavior, read-only); no bulk reads into context, no generated-data mutation.
- `--maps ""` (empty string) now also exits 2 in both subcommands — a deliberate fail-closed tightening beyond the letter of the brief (which specified nonempty text); no existing test, caller, or documented usage relied on empty-string-means-default.

## Gate status

Both blocking defects are closed with old-code tripwire evidence and post-fix probes; coverage and truncation output are accurate. Per worklog revision 5 the baseline gate stays **closed** until the artifact tracking policy (R-003-C01) is resolved and a fresh independent review approves. No obstruction/terrain writer work or generated-data migration was performed or is authorized by this report.
