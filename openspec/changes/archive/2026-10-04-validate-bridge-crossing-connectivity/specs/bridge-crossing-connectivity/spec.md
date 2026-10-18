## ADDED Requirements

### Requirement: Bridge crossing validation

The terrain pipeline SHALL distinguish decoded bridge geometry from a validated vehicle crossing. For every finite decoded bridge deck, it SHALL derive two endpoint approach regions, evaluate bounded local passable connectivity with and without the deck, and emit a deterministic verdict of `validated`, `rejected`, `unavailable`, or `unknown` with provenance and an actionable reason. Map-wide mainland component membership SHALL NOT be required for validation.

#### Scenario: Validated crossing connects distinct approaches

- **WHEN** a decoded deck has finite nonzero geometry, both endpoint approaches are passable, the approaches belong to distinct passable components with the deck removed, and the deck reconnects them when enabled
- **THEN** the bridge crossing is recorded as validated for the configured policy
- **AND** its endpoint cells, deck cells, component identifiers, and source mesh reference are recorded
- **AND** candidate policy keeps the crossing labelled `candidate` and `unverified`

#### Scenario: Ordinary road is not a bridge crossing

- **WHEN** bridge-named geometry is already connected to the same passable component at both endpoints within the bounded local corridor without using the deck
- **THEN** the crossing is rejected as non-separating geometry
- **AND** it does not create a vehicle bridge route

#### Scenario: Isolated lake or island crossing

- **WHEN** both endpoint approaches are passable and locally disconnected without the deck but reconnect through the deck, while neither approach belongs to a map-wide mainland component
- **THEN** the crossing is validated locally
- **AND** absence of a global mainland component does not reject or invalidate the bridge

#### Scenario: Missing or invalid geometry

- **WHEN** the referenced client mesh is absent, corrupt, non-finite, degenerate, or produces no rasterized cells
- **THEN** the bridge record is marked unavailable or rejected with a specific reason
- **AND** no vehicle route is granted

### Requirement: Bridge crossing artifact provenance

The terrain artifact SHALL publish per-bridge crossing records separately from the legacy bridge mask. Each record SHALL identify the source reference, status, policy permission, endpoint and approach cells, deck-cell count, connectivity verdict, and rejection reason when applicable. The artifact SHALL remain deterministic and SHALL reject mixed or dimensionally inconsistent bridge records.

#### Scenario: Candidate crossing is visible but unverified

- **WHEN** a candidate bridge passes geometric and graph connectivity validation under `candidate_permitted`
- **THEN** the terrain sidecar records `candidate_permitted`, `candidate`, and `unverified`
- **AND** the flow sidecar exposes the same provenance
- **AND** the browser displays the provenance without claiming in-game drivability

#### Scenario: Invalid crossing is excluded

- **WHEN** a bridge candidate fails endpoint, component, or deck-continuity validation
- **THEN** its mask cells are not used to make a vehicle route
- **AND** the sidecar retains the failure reason for QA and recovery

### Requirement: Individual bridge flow verification

The offline validation pipeline SHALL test each selected bridge crossing as a route between its two approaches independently of the normal multi-source browser visualization. It SHALL report whether a vehicle source on either approach can reach the opposite approach through the crossing.

#### Scenario: Synthetic bridge route

- **WHEN** a synthetic vehicle cost grid contains two separated passable regions and a validated bridge deck joining them
- **THEN** the vehicle flow solver reaches the opposite region through the bridge
- **AND** removing the bridge leaves the opposite region unreachable

#### Scenario: Representative bridge report

- **WHEN** a selected real map is processed in an isolated output tree
- **THEN** the report contains one verdict and reachability result per decoded bridge
- **AND** total candidate-cell counts alone are not accepted as proof of a crossing
