# bridge-crossing-annotation Specification

## Purpose
Define deterministic, reviewable bridge annotations sourced from every map minimap.

## Requirements

### Requirement: Complete map annotation inventory
The annotation workflow SHALL create exactly one map record for every canonical processed map, including maps where no bridge is visible.

#### Scenario: Map has no bridge
- **WHEN** annotators inspect a map and find no bridge
- **THEN** its annotation record exists with an empty `bridges` collection
- **AND** the record is marked inspected rather than omitted

#### Scenario: Map has multiple bridges
- **WHEN** a minimap contains multiple bridge crossings
- **THEN** every distinct crossing receives a stable map-local bridge ID
- **AND** no bridge overwrites another record

### Requirement: Flow-compatible rotated rectangle
Each bridge annotation SHALL store center coordinates, angle, width, and length in repository map/world units using the existing top-left, x-east, y-south flow convention. The record SHALL retain map size and source image dimensions.

#### Scenario: Rectangle round trip
- **WHEN** a rectangle is rendered onto the source minimap
- **THEN** its derived corners align with the annotated bridge
- **AND** converting the corners back to world units reproduces the stored geometry within the documented tolerance

#### Scenario: Invalid geometry
- **WHEN** a record has non-finite values, non-positive dimensions, or corners outside map bounds
- **THEN** validation rejects the record with an actionable error
- **AND** no crossing artifact is generated from it

### Requirement: Human uncertainty and disagreement evidence
The core geometry schema SHALL NOT require a confidence score. Annotation and review tools SHALL preserve free-text comments, evidence locations, annotator/reviewer identity, disposition, and unresolved disagreement status in review records.

#### Scenario: Low-confidence observation
- **WHEN** an annotator is uncertain whether an object is a bridge
- **THEN** the annotator records a comment and evidence location
- **AND** the geometry schema remains valid without a confidence field

#### Scenario: Reviewer disagreement
- **WHEN** the reviewer disagrees with an annotation or finds a missing bridge
- **THEN** the review record is flagged for user adjudication
- **AND** the pipeline does not silently choose one geometry

### Requirement: Two-round assignment coverage
The workflow SHALL generate deterministic annotator and reviewer manifests from the canonical sorted map inventory. Ten annotator identities and ten distinct reviewer identities SHALL be assigned so every map is inspected at least twice in each round.

#### Scenario: Coverage validation
- **WHEN** an assignment manifest is validated
- **THEN** it rejects unknown or duplicate map IDs
- **AND** it reports every map with fewer than two annotator or reviewer assignments
- **AND** annotator and reviewer identity sets are disjoint

### Requirement: Annotation QA rendering
The workflow SHALL render every approved rectangle over its source minimap using the same world-to-image transform used by flow overlays.

#### Scenario: QA overlay
- **WHEN** a map annotation is rendered
- **THEN** the output preserves the original minimap pixels
- **AND** each bridge ID and rectangle is visible
- **AND** no coordinate-axis flip is introduced