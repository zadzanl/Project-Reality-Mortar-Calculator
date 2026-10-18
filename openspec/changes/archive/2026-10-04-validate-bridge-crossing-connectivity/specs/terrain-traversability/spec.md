## MODIFIED Requirements

### Requirement: Continuous terrain movement cost

The pipeline SHALL produce one continuous movement cost per simulation cell by combining configured terrain signals, including slope and optional roughness, with separately sourced water, vegetation, static-obstruction, and road evidence. It SHALL preserve the distinction between low-cost terrain and explicit road membership. Decoded bridge geometry SHALL NOT become a vehicle route merely because its triangles rasterize; only bridge cells belonging to a validated crossing record may alter vehicle passability.

#### Scenario: Flat terrain without road geometry

- **WHEN** a map has passable flat terrain but no decoded road triangles
- **THEN** the terrain cells receive ordinary baseline terrain cost
- **AND** they are not labeled as explicit roads solely because they are flat

#### Scenario: Explicit road geometry

- **WHEN** a road triangle covers a simulation cell
- **THEN** the cell records road membership separately from terrain class
- **AND** the configured road modifier may lower its movement cost
- **AND** road membership does not bypass configured extreme-slope or step hazards

#### Scenario: Validated bridge crossing

- **WHEN** a bridge deck belongs to a validated crossing record permitted by policy
- **THEN** its deck cells may receive the configured bridge/road movement cost for land vehicles
- **AND** its endpoint and approach connectivity is retained in provenance
- **AND** the original water and ordinary-road masks remain independently available

#### Scenario: Unvalidated bridge geometry

- **WHEN** bridge-named geometry lacks validated endpoint connectivity
- **THEN** it does not make blocked vehicle cells passable
- **AND** the sidecar records the rejection or unknown reason

#### Scenario: Water, vegetation, or static obstruction

- **WHEN** a cell is identified as water, vegetation-heavy, or a heuristic static obstruction
- **THEN** its cost increases according to configured multipliers

### Requirement: Deterministic terrain artifacts

The terrain pipeline SHALL produce deterministic per-map outputs containing a compact cost grid, diagnostic metadata, source coverage, configuration provenance, bridge crossing records, and enough information for a later offline flow solver to consume the grid without recomputing terrain physics.

#### Scenario: Repeatable bridge artifact

- **WHEN** the same map, raw source archives, configuration, and bridge policy are processed twice
- **THEN** bridge masks, crossing records, cost grids, and sidecars are byte-for-byte equivalent or equivalent under a documented serialization normalization

#### Scenario: Flow-compatible bridge artifact

- **WHEN** the flow generator loads a terrain artifact
- **THEN** it can obtain validated bridge permission, endpoint provenance, grid dimensions, origin, cell size, costs, passability sentinel, source coverage, and movement-parameter provenance without re-decoding bridge meshes
