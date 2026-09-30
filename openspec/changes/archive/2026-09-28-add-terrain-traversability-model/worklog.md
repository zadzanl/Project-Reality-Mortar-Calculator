# Worklog

## 2026-09-27 - Phase 1 review terrain-phase1-001

- Admitted and froze review-brief-phase1-001.md for tasks 2.1-2.7.
- Dispatched one Behavioral, one Changeability, and one Security specialist;
  no model overrides. Preserved independent results under review-*-phase1-001.
- Ran independent in-memory LS/edge/ramp/conversion/window checks and mocked
  material update checks. No implementation/config/raw-data writes.
- NEEDS_REVISION: S1-F01 demonstrates incomplete material extraction replacing
  the existing table. Numerical reference checks passed; full pytest not run.
- Full evidence, source limitations, classification and closure validation:
  review-record-phase1-001.md. No implementation fixes made.

## 2026-09-27 - Phase 1 bounded re-review terrain-phase1-002

- Revision loop 1 of 3; froze review-brief-phase1-002.md and dispatched one
  Behavioral, Changeability and Security specialist, without model overrides.
- S1-F01, S1-F02 and C1-F01 closed. O1-N01 remains a nonblocking memory-note
  correction: ~199 MiB is one residual tensor, not measured total peak.
- Validator tests: 3 passed. Mock/temporary-fixture rejection, failed writes,
  failed replacement and successful replacement checks passed. Real archive
  entries equal all 307 configured entries; real config was never rewritten.
- Removing only the inserted memory-note text reproduces the prior terrain
  source SHA-256 exactly, confirming unchanged numerical implementation.
- Verdict APPROVED; execution DEGRADED for retrieval/artifact-delivery warnings.
  Full record and separate preserved specialist evidence: review-record-phase1-002.md.
  No implementation/config/raw-data edits. Full suite/peak profiling not run.

## 2026-09-27 - Resume implementation terrain-resume-001

- Loaded task-record revision R1 after provider disconnect. Core terrain feature and
  cost modules were present; remaining work was regression, QA, loader, and evidence.
- Added synthetic and temporary-archive tests. Fixed a real candidate-water defect:
  central-difference slope can leave an equal-height shoulder around a flat basin;
  candidate detection now evaluates a second border ring while remaining diagnostic-only.
- Added `processor/terrain_artifact.py`, strict binary/sidecar validation, and
  per-cell diagnostic float32 grids. Added deterministic minimap QA renderer with
  independent class, road-mask, water, and coverage layers.
- Corrected static footprint aggregation to use configured metric radii rather than
  silently rounding every radius up to a whole cell. Added invalid road-triangle and
  map-name guards.
- Generated Asad Khal, Adak, Muttrah City 2, and coarse 8 m Andromeda QA artifacts.
  Repeated renderer hashes matched; Andromeda reports `no_server_zip` and remains
  an input-coverage limitation, not a road-absence claim.
- Evidence: `implementation-terrain-001.md`, `implementation-resume-tests-001.md`,
  `qa_terrain_images/`. Verification: 67 safe processor tests passed; browser tests
  passed; full unfiltered processor collection remains unsafe because
  `test_update_manifest.py` mutates raw manifest at import time.

## 2026-09-27 - Orientation advisory ORIENT-001

- Review-Resume-001 did not cover the user's vertical-mirroring advisory; recorded
  ORIENT-001 in task-record R2 and dispatched two independent read-only traces.
- Numeric gameplay-object cross-check selected the existing single raw-to-repository
  row reversal. No second production flip was added: the QA renderer already maps
  artifact row 0 directly to image top.
- Added an asymmetric end-to-end regression covering elevation, water, roads, costs,
  classes, minimap placement, and source-byte preservation. Corrected its evidence
  reference after review.
- Verification: focused terrain/features/cost/artifact tests 33 passed; safe
  processor suite 69 passed; browser suites passed; four representative maps were
  regenerated and rendered. Review `review-record-orientation-001.md` APPROVED,
  execution health COMPLETE.

## 2026-09-28 - Coarse roughness repair and batch resume

- Shipment failure confirmed as a coarse-source limitation: 16 m native
  spacing makes the smallest valid 3-sample roughness window 48 m, exceeding
  the 24 m feature-scale bound.
- Implemented explicit roughness unavailability, centralized the bound, added
  truthful metadata verification status to terrain sidecars, and added tests
  for downstream propagation and batch continuation.
- Review `review-record-repair-r2-001.md` returned APPROVED after revision.
- Focused terrain tests: 37 passed. Resumed Shipment plus the remaining 14
  maps: 15/15 processed. Sidecar and binary dimension checks passed for all 15
  maps. Safe processor suite: 93 passed.