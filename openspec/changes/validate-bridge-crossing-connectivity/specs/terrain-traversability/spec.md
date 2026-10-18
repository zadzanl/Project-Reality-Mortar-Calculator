## MODIFIED Requirements

### Requirement: Continuous terrain movement cost
The pipeline SHALL produce one continuous movement cost per simulation cell by combining configured terrain signals, including slope and optional roughness, with separately sourced water, vegetation, static-obstruction, and road evidence. It SHALL preserve the distinction between low-cost terrain and explicit road membership. A reviewed bridge rectangle SHALL NOT make every interior cell traversable by itself; only a rectangle whose two derived approach regions pass the configured local separation and reconnection validation may alter vehicle passability.

#### Scenario: Flat terrain without road geometry
- **WHEN** the pipeline processes passable flat terrain without decoded road geometry or approved bridge annotations
- **THEN** the cells receive ordinary baseline terrain cost
- **AND** they are not labeled as roads solely because they are flat

#### Scenario: Approved crossing
- **WHEN** an approved rectangle has usable approaches that are disconnected with the rectangle disabled and connected with the rectangle enabled
- **THEN** only the validated connector cells may receive the configured vehicle crossing cost
- **AND** the original water and ordinary-road evidence remains independently available

#### Scenario: Rectangle without valid banks
- **WHEN** a rectangle has no passable approach on one side or its sides are already connected without the rectangle
- **THEN** no vehicle route is granted
- **AND** the failure reason is retained in diagnostics

#### Scenario: Water, vegetation, or static obstruction
- **WHEN** a cell is identified as water, vegetation-heavy, or a heuristic static obstruction
- **THEN** its cost increases according to configured multipliers
- **AND** bridge validation does not bypass those hazards except for explicitly validated connector cells.

### Requirement: Deterministic terrain artifacts
The terrain pipeline SHALL produce deterministic per-map outputs containing a compact cost grid, diagnostic metadata, source coverage, configuration provenance, approved bridge annotation hashes, connector records, and enough information for a later offline flow solver to consume the grid without recomputing terrain physics.

#### Scenario: Repeatable bridge artifact
- **WHEN** the same map, annotation, review disposition, terrain inputs, and configuration are processed twice
- **THEN** connector masks, records, cost grids, and sidecars are byte-for-byte equivalent or equivalent under documented serialization normalization

#### Scenario: Invalid or mixed annotation provenance
- **WHEN** annotation or review files are missing, dimensionally inconsistent, or have hashes that do not match the sidecar
- **THEN** processing fails closed without enabling bridge routing
- **AND** the diagnostic identifies the missing or mismatched input.