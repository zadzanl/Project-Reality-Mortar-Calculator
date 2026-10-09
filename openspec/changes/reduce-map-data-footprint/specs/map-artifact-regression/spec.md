# map-artifact-regression Specification

## Purpose

Baseline capture and comparison harness that snapshots generated map artifacts (hashes plus decoded behavioral fixtures) before a format change and verifies equivalence within documented tolerances after regeneration, so footprint reductions cannot silently alter terrain, flow, or obstruction behavior.

## ADDED Requirements

### Requirement: Baseline capture

The harness SHALL capture, per selected map, a sha256 of every artifact file and decoded behavioral fixtures: terrain cost/feature values at a deterministic fixed cell sample, flow arrival times at fixed cells per layer and agent class, and obstruction record counts with bounding boxes. The baseline SHALL be stored as compact JSON outside `processed_maps/` and SHALL be reproducible by re-running capture on unchanged data.

#### Scenario: Capture from current artifacts
- **WHEN** the harness runs in capture mode against `processed_maps/` before any format change
- **THEN** it writes one baseline document containing per-map artifact hashes and the decoded fixtures
- **AND** a second capture run on the same data produces an identical baseline document

#### Scenario: Fixed map and cell selection
- **WHEN** the baseline is captured
- **THEN** the map set includes at least adak, albasrah_2, and muttrah_city_2 plus the five maps with the largest obstructions artifacts
- **AND** sampled cells are chosen by a deterministic rule (seeded or index-based) recorded in the baseline

### Requirement: Post-change comparison with tolerances

The harness SHALL compare regenerated artifacts against the baseline: masks, obstruction record counts, and unreachable sentinels MUST match exactly; dequantized continuous grids MUST be within quantization error (no more than half the recorded scale per cell); flow arrival times MUST stay within a documented tolerance with a capped count of flipped unreachable cells. Any exceedance SHALL be reported per map, per artifact, per cell.

#### Scenario: Equivalent regeneration passes
- **WHEN** artifacts are regenerated after a serialization-only change and compared
- **THEN** masks and counts match exactly
- **AND** every dequantized grid cell differs from baseline by no more than half its sidecar scale
- **AND** flow arrivals differ by no more than the documented tolerance

#### Scenario: Behavioral drift is caught
- **WHEN** a regenerated terrain cost grid differs from baseline beyond quantization error at any sampled cell
- **THEN** the comparison fails
- **AND** the report names the map, artifact, cell indices, baseline value, and new value

### Requirement: Offline, dependency-free operation

The harness SHALL run locally with Python stdlib and NumPy only, SHALL NOT require a browser, network, or the game installation, and SHALL NOT modify files under `raw_map_data/` or `processed_maps/` while capturing or comparing.

#### Scenario: Read-only harness
- **WHEN** capture or compare runs
- **THEN** no file under `raw_map_data/` or `processed_maps/` is created, modified, or deleted
- **AND** the run completes without network access
