# Review Record — review-003

## Identity and frozen brief

- **Identity:** review-003, baseline-gate review after the corrected baseline and task record were committed.
- **Date:** 2026-10-10.
- **Objective:** approve or reject the trustworthy pre-change regression gate before any map-artifact rewrite. This review does not approve or review obstruction/terrain writer implementation.
- **User intent, relayed 1:1:** “Please read that openspec change. i would like to reduce the size of this repo, and i would prefer doing it now when the flow simulation isnt finalised. Plan looks good. Please proceed with implementation. I've switched your environment from Planning (previous) to Orchestration (current). Make sure to delegate and orchestrate the tasks with subagents when applicable and worthwhile. Please continue”.
- **Acceptance target:** fail-closed baseline identity and map selection; exact sampled sentinel and sampling-index integrity; production south-first heightmap Y orientation; reproducible focused checks; durable corrected baseline; current unchanged compare; honest broad-suite status. No generated-data rewrite before this gate is approved.
- **Changed surface:** `processor/baseline.py`, `processor/baseline_firing.mjs`, focused Python/Node tests, corrected `baseline-pre-change.json`, `compare-unchanged-report.json`, current OpenSpec specs/tasks, `impl-001.md` corrected, `impl-002a.md`, `impl-002b.md`, and worklog revision 4.
- **Constraints:** no source or generated-data edits; no bulk reads of `processed_maps/` or `raw_map_data/`; do not run `processor/tests/test_update_manifest.py`.

## Admission and route decisions

The brief was understandable and frozen before dispatch. Worklog revision 4 was confirmed before review.

| Dimension | Decision and controlled tags | Instances | State |
|---|---|---:|---|
| Behavioral (B) | **YES** — `defect-regression`, `data-integrity`, `error-recovery`, `behavioral-validation`; numerical and format migration gate | 2 attempts (1 initial no-output, 1 retry) | COMPLETE, usable retry result |
| Changeability (C) | **YES** — `teammate-safety`, `interface-contract`, `dependency-shape`; durable operator gate | 2 attempts (1 initial no-output, 1 retry) | COMPLETE, usable retry result |
| Security (S) | **NO** — no new trust, authorization, credential, privacy, network, or external security boundary in this offline read-only gate | 0 | NOT_SELECTED |

The retry was justified because review-002 had no usable Behavioral or Changeability specialist output and the user explicitly required both. The first no-output attempts are preserved as execution warnings; the retry results are the usable source reports. No Gate agent was used. The repository-local `.agents/skills/review-protocol/SKILL.md` does not exist; the maintained global protocol at `c:\Users\lenovo\.copilot\skills\review-protocol\SKILL.md` was used.

## Attempt log and evidence

Environment observed: Windows PowerShell, Python 3.11.4, NumPy 1.26.4, Node v24.11.0.

Checks actually run by this review:

- `python -m pytest processor/tests/test_baseline.py -q` → **20 passed, exit 0**.
- `node --test processor/tests/test_baseline_firing.mjs` → **6 passed, 0 failed, exit 0**.
- Wrong document probe using `compare-unchanged-report.json` as baseline → actionable rejection, **exit 2**.
- Unknown map probe `--maps not_a_map` → actionable rejection, **exit 2**.
- Comma-only map probe `--maps ","` → **`compare: pass (0 exceedances)`, exit 0**. This is a newly confirmed residual defect.
- Full unchanged compare against `baseline-pre-change.json` → eight maps read, **pass with 0 exceedances, exit 0**.
- Baseline durability: `git rev-parse HEAD:.../baseline-pre-change.json` and `git hash-object .../baseline-pre-change.json` both equal `03a1a357f7738eec658377c4701416974edb1135`; SHA-256 is `A7D9D14DD9EB058D8D8DDA21E57239D201D3C5985ACB7F008BDD32D8B01EAD29`.

Evidence inspected: `review-001.md`, `review-002.md`, corrected `impl-001.md`, `impl-002a.md`, `impl-002b.md`, worklog revision 4, current tasks, baseline/report summaries, the current baseline harness and focused tests, and the named OpenSpec/spec surfaces. No unsafe manifest test was run. No generated-data mutation was performed.

The broad safe suite remains accurately recorded as **4 failed, 110 passed, 8 errors, exit 1**; it is not a green suite. This review did not rerun that broad suite because the required current result is already recorded and the focused gate checks were the bounded verification requested. The earlier broad command in the session context also ended exit 1; no claim of green status is made.

## Preserved specialist results

### Behavioral Assurance — retry instance, COMPLETE

The specialist independently reproduced the focused Python and Node suites, wrong-baseline and unknown-map failures, full eight-map compare, committed baseline equality, and the honest broad-suite result. It confirmed production `getElevation` Y-flip and live sampled sentinel coverage.

Source findings:

- **B-01:** `--maps ","`, `",,"`, or whitespace can parse to an empty selection and still return pass/0. This contradicts the claimed zero-coverage fail-closed invariant. Required closure: reject a requested-but-empty map list with actionable exit 2 in compare, and guard capture similarly. Validation: comma-only and whitespace selections exit 2; valid `--maps adak` still passes.
- **B-02:** `--report` can resolve to the same path as `--baseline` and overwrite the baseline with a small compare report while returning success. Required closure: reject equal resolved paths with exit 2 and leave the baseline unchanged. Validation: same-path probe fails and preserves bytes; distinct report path still works.

Specialist limits: sample-based rather than exhaustive grid proof; byte-identical double capture remains worklog evidence, not recaptured here; firing-unavailable visibility was source-checked rather than simulated.

### Changeability — retry instance, COMPLETE

The specialist independently reproduced the focused suites, bounded negative probes, broad-suite status, and baseline blob equality. It found:

- **C-01:** a bare `.gitignore` `artifacts/` rule silently ignores evidence directories; worklog-cited `research-004.md` and `research-005.md` are not committed, and new review artifacts require force-add awareness. Required closure: make tracking intent explicit and commit cited handoffs, or document and enforce the force-add policy. Validation: `git check-ignore`/`git ls-files` demonstrate the intended durable chain.
- **C-02:** subset compare (`--maps adak`) exits pass without console indication that only 1 of 8 maps was checked. Required closure: print coverage or require explicit partial-run acknowledgement. Validation: subset and full runs visibly identify coverage.
- **C-03:** the “see --report” truncation hint can mention a report that was not requested. Required closure: make the message conditional or tell the operator to rerun with `--report`.
- **C-04:** tolerance prose is duplicated rather than derived from numeric constants. This is a nonblocking maintainability note carried from review-001.
- **C-05:** capture writes the baseline directly and is not atomic. This is a recovery/maintainability note; interrupted capture can truncate the prior output, although compare then fails closed.

Specialist limits: no edits or commits; no bulk generated-data read; no independent recapture; no global verdict or severity classification.

## Classified findings

### MAJOR — blocking

#### R-003-B01 — BLOCKING_DEFECT — empty requested map selection passes with zero coverage

- **Provenance:** Behavioral Assurance, B-01.
- **Evidence:** this review reproduced `compare --baseline baseline-pre-change.json --maps ","` as exit 0 with `compare: pass (0 exceedances)` and zero maps.
- **Impact:** an operator/CI variable containing only delimiters can approve the migration without checking any map. This directly violates the baseline gate’s fail-closed acceptance target.
- **Required change:** reject a non-null `--maps` argument that parses to an empty list; apply the equivalent guard to capture.
- **Validation:** comma-only, repeated-comma, and whitespace-only selections return exit 2 with an actionable message; valid nonempty selection and default full selection continue to work.

#### R-003-B02 — BLOCKING_DEFECT — compare report can overwrite the baseline

- **Provenance:** Behavioral Assurance, B-02.
- **Evidence:** specialist reproduced same-path `--baseline X --report X` on a temporary copy; compare returned success and replaced the baseline with a small report.
- **Impact:** a path mistake destroys the gate artifact and can leave an apparent successful comparison. Git recovery limits blast radius but does not make the operation safe.
- **Required change:** reject equal resolved baseline/report paths before writing.
- **Validation:** same-path probe exits 2 and preserves the baseline byte-for-byte; a distinct report path remains valid.

### MAJOR — proof gap / durability risk

#### R-003-C01 — PROOF_GAP — cited evidence chain is vulnerable to silent ignore

- **Provenance:** Changeability, C-01.
- **Evidence:** `.gitignore` contains a bare `artifacts/` rule; specialist reports `research-004.md` and `research-005.md` are not tracked despite worklog references. The corrected baseline itself is durable, but the surrounding evidence chain is not uniformly reproducible from a checkout.
- **Impact:** a future maintainer can follow the worklog and still lack cited handoffs; new review records can disappear from normal `git add` operations.
- **Required change:** make the tracking policy explicit and durable: either unignore the OpenSpec artifacts directory or document the required force-add policy and ensure every cited handoff is committed.
- **Validation:** inspect `git check-ignore` and `git ls-files`; the chosen policy must make the worklog’s cited evidence retrievable from the declared review commit.

### MAJOR — operator safety / assessability

#### R-003-C02 — PROOF_GAP — subset compare is indistinguishable from full gate on console output

- **Provenance:** Changeability, C-02.
- **Evidence:** `--maps adak` returns pass without saying it checked 1 of 8; the JSON report records the subset, but a console-only operator can miscite it as full evidence.
- **Impact:** the migration gate can be weakened by a valid, fast subset invocation.
- **Required change:** print explicit compared/total coverage or require an explicit partial-run acknowledgement.
- **Validation:** subset output identifies `1 of 8`; default output identifies `8 of 8`.

## Nonblocking learn notes

- **R-003-C03:** condition the truncation hint on `--report`, or make the message say to rerun with `--report`.
- **R-003-C04:** derive tolerance descriptions from the numeric constants or remove duplicated prose.
- **R-003-C05:** use a sibling temporary file plus atomic replace for capture durability.
- The deterministic 64-cell sampling is a documented ceiling, not exhaustive proof. Sentinel checks are live and exact at sampled cells; unsampled cells are not proven.
- The broad safe suite is not green: **4 failed, 110 passed, 8 errors, exit 1**. This is an honest known limit and not itself a reason to claim the focused baseline gate passed.

## Verdict and execution health

**Verdict: NEEDS_REVISION.** The focused comparator and firing fixture are materially repaired: required focused tests pass, wrong-baseline and unknown-map inputs fail closed, the corrected baseline is durable at the current commit, and the unchanged eight-map compare passes. However, the live comma-only zero-coverage path is an anchored blocking defect, and same-path report overwrite is a data-loss defect in the gate. The operator evidence-chain and subset-coverage proof gaps reinforce that the gate is not yet trustworthy enough to authorize map-artifact rewriting.

**Execution health: COMPLETE.** Both required specialist routes produced usable reports on retry; all dispatched instances completed. The initial no-output attempts are recorded as warnings, not unresolved required coverage.

No obstruction compaction, terrain quantization, regeneration, cleanup, or generated-data migration is approved by this record.

## Remediation validation

1. Reject empty parsed map selections for capture and compare; add focused regression tests and rerun the Python focused suite.
2. Reject equal resolved baseline/report paths and verify the baseline remains byte-identical after the failed probe.
3. Resolve the artifact tracking policy and commit every evidence file cited by the worklog, or revise the worklog to cite only durable files.
4. Make subset coverage explicit in CLI output or require acknowledgement before it can be used as gate evidence.
5. Rerun the required focused suites, bounded negative probes, committed-object equality, and full unchanged compare. Preserve the broad safe-suite result exactly unless a new authorized run proves otherwise.
