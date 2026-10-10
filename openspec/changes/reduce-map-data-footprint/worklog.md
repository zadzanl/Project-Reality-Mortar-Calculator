# Worklog: reduce-map-data-footprint

## Revision 1 - 2026-10-10

### Intent
Reduce generated repository footprint without changing physics constants or heightmap precision. Establish a read-only regression baseline before format changes, then apply only measured serialization and cleanup changes.

### Constraints
- Preserve unrelated working-tree changes on `feat/opening-flow-simulator`.
- Do not reset, clean, or bulk-read generated map data.
- Do not modify `raw_map_data/` or `processed_maps/` during baseline capture/compare.
- Use Python stdlib plus NumPy; no new dependencies.
- Exclude `processor/tests/test_update_manifest.py` from safe pytest runs.

### Evidence and decisions
- OpenSpec status reports 20 pending tasks under the spec-driven change.
- Working tree is dirty with unrelated flow-simulator edits and deleted baseline files.
- Explorer reports `processor/baseline.py`, `baseline_firing.mjs`, and `processor/tests/test_baseline.py` exist in HEAD and can be restored selectively.
- Explorer reports terrain regeneration is currently blocked by missing `terrain_generation_id`; six maps advertise format 1.1 while the current loader accepts only 1.0.
- Explorer reports obstructions are the largest measured win; flow `.bin` files are already uint8 and dominate remaining binary size, so terrain quantization alone cannot meet the size target.
- Browser does not load obstruction JSON or terrain grids; Python readers are the current obstruction consumers.
- `pytest.exe` launcher is broken in this environment; use the Python 3.11 interpreter with `python -m pytest`.
- Veteran Engineer review dispatch failed twice with provider errors; no review verdict was received.

### Handoffs
- `artifacts/research-004.md`: current pipeline and blockers.
- `artifacts/research-005.md`: recoverability, size inventory, and baseline recommendation.

### Verification pending
- Focused baseline tests and unchanged compare.
- Full safe processor suite after focused phase.
- No generated-data mutation performed in this revision.

## Revision 2 - 2026-10-10

### Review and decision
- Independent baseline review: `artifacts/review-001.md`, **NEEDS_REVISION**. Focused tests pass, but compare can pass with zero maps or a report mistaken for a baseline; sampled quantized cost sentinels are not checked exactly; firing fixture samples raw south-first heightmap without the production Y flip.
- Keep the baseline gate closed. Repair comparator coverage/sentinel/index checks, correct firing fixture, rerun checks, recapture the pre-change baseline outside generated-data trees, and request fresh independent review before writer work.
- `impl-001.md` incorrectly calls a failing broad suite PASS; actual recorded outcome is 4 failed, 100 passed, 8 errors (exit 1), with unrelated dirty-flow changes. The existing baseline JSON is tracked at commit `0976b65`.

### Bounded handoffs
- Worker A: `processor/baseline.py`, `processor/tests/test_baseline.py`, `artifacts/impl-002a.md`; fail-closed coverage, exact sampled cost sentinel and sample-index checks, visible firing skip notes. No generated-data edits.
- Worker B: `processor/baseline_firing.mjs`, focused Node regression test, `artifacts/impl-002b.md`; production Y orientation, no changes to production heightmap or physics. Current baseline firing values become stale until recapture.

### Verification pending
- Negative probes must fail on old behavior and pass after correction; rerun focused/broad tests, re-capture all eight maps twice outside protected data trees, compare against corrected baseline, and request new independent review.

## Revision 3 - 2026-10-10

### Evidence
- Workers returned `artifacts/impl-002a.md` and `impl-002b.md`. Checked the scoped diffs; no generated-data source edits. The Python negative tests failed on old code (8 red) and now pass; Node orientation tripwire differed at 4/6 adak coordinates before fix.
- Independently ran `python -m pytest processor/tests/test_baseline.py -q` (20 passed) and `node --test processor/tests/test_baseline_firing.mjs` (6 passed). `git diff --check` on scoped tracked source files passed.
- Captured all eight maps **twice** to two temp JSON files outside generated-data trees. Both have SHA-256 `A7D9D14DD9EB058D8D8DDA21E57239D201D3C5985ACB7F008BDD32D8B01EAD29`, 2,448,239 bytes. Compared to the tracked old document: all file hashes, terrain sampled grids, flow and obstructions identical; firing solutions changed as expected with Y flip, and terrain sidecars now record `blocked_sentinel`. Copied the checked recapture to `artifacts/baseline-pre-change.json`.
- `python processor/baseline.py compare --baseline openspec/changes/reduce-map-data-footprint/artifacts/baseline-pre-change.json --report openspec/changes/reduce-map-data-footprint/artifacts/compare-unchanged-report.json` passed: eight maps, zero exceedances and notes, both firing fixtures `ok`.
- Broad safe suite (excludes `test_update_manifest.py`): **FAIL**, exit 1: 4 failed, 110 passed, 8 errors; failing test names match earlier review. No claim of a green suite. `impl-001.md` corrected to preserve historical evidence without calling a failing run PASS.

### Next gate
- Ask for independent review of this changed surface (new review identity); do not start obstruction/terrain writer work or mark phase-1 tasks complete until review clears it.

## Revision 4 - 2026-10-10

### Review and durability
- `artifacts/review-002.md`: **NEEDS_REVISION; execution BLOCKED**. The two required specialist calls yielded no usable results. Reviewer confirmed focused suites and invalid-CLI negative checks; scope was not approved.
- Corrected baseline artifact (SHA-256 `A7D9D14DD9EB058D8D8DDA21E57239D201D3C5985ACB7F008BDD32D8B01EAD29`) and the repaired comparator/firing tests are now committed in `ae56754` (`fix(processor): validate map baseline before migration`); unrelated dirty files were not included. `git add` printed an ignored-artifacts warning for the unchanged compare report but the explicitly tracked baseline was included. The commit has five paths: baseline.py, baseline_firing.mjs, two test files, baseline-pre-change.json.
- Phase-1 tasks 1.1–1.5 are marked complete for the implemented/captured/committed work. This is **not** independent review approval; writer/data migration remains gated on usable specialist verdicts.

### Next gate
- Track the corrected task record and verification reports, then request a new review with the committed artifact and task state. The safe broad suite is still not green (4 failed, 110 passed, 8 errors; exit 1).

## Revision 5 - 2026-10-10

### Review findings
- `artifacts/review-003.md`: **NEEDS_REVISION; execution COMPLETE**. Behavioral and Changeability specialists returned usable reports on retry. They found two blocking CLI safety defects: delimiter-only `--maps` selects zero maps and returns pass; `--report` equal to `--baseline` overwrites the safety artifact.
- Additional proof gaps: subset compare needs visible coverage, truncation output must not imply an unrequested report, and ignored OpenSpec evidence needs an explicit tracking policy. These are bounded operator-safety/documentation fixes; no generated data is involved.

### Bounded handoff
- Worker C: repair `processor/baseline.py` and `processor/tests/test_baseline.py`; reject empty capture/compare selections, reject same resolved baseline/report paths, print compared/total coverage, make truncation guidance accurate, add negative tests. Report to `artifacts/impl-003.md`. No map data, firing fixture, tasks, or unrelated dirty files.

### Verification pending
- Run old-code tripwires first, then focused Python and Node tests, comma/repeated-comma/whitespace probes, same-path preservation probe, subset/full coverage output, committed-baseline compare, and broad safe suite with its true failing status. Resolve ignored evidence references before the next review.

## Revision 6 - 2026-10-10

### Evidence
- Worker C returned `artifacts/impl-003.md`. Old-code tripwires reproduced both review-003 defects: delimiter-only maps passed with zero coverage; same-path report shrank a copied baseline from 2,448,239 bytes to 404 bytes. The worker then added fail-closed guards, coverage output, accurate truncation guidance, and tests.
- Independent verification: `python -m pytest processor/tests/test_baseline.py -q -p no:cacheprovider` -> 30 passed, exit 0; `node --test processor/tests/test_baseline_firing.mjs` -> 6 passed, exit 0; scoped `git diff --check` passed. Real baseline probes: same-path report exit 2 with bytes preserved; comma-only maps exit 2; valid `adak` subset exit 0 with `1/8` coverage.

### Evidence tracking decision
- `.gitignore` previously ignored every `artifacts/` directory, which hid OpenSpec evidence. It now preserves the generated-data ignore rule while unignoring Markdown OpenSpec artifacts and worklogs. The corrected baseline JSON remains explicitly tracked; generated map data remains ignored and untouched.
- Research-004/005 and worker/review records will be committed as small source evidence. Future non-Markdown or large generated artifacts still require an explicit force-add decision.

### Verification pending
- Commit Worker C plus its durable report/evidence policy, rerun full unchanged compare, then request review-004. Do not start obstruction or terrain writer work until review-004 approves.
