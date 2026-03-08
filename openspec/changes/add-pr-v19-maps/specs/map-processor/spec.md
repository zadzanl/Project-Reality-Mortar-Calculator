## ADDED Requirements

### Requirement: Falklands Map Exclusion Documentation

The system SHALL document in `processed_maps/README.md` and `AGENTS.md` that `the_falklands` map is intentionally excluded from processing due to its non-standard map boundary size.

#### Scenario: Exclusion documented in processed maps README
- **WHEN** a contributor checks `processed_maps/README.md`
- **THEN** a clearly labeled section explains that `the_falklands` is excluded
- **AND** the reason states: primary game area is 8km × 8km but airfields and helicopter carrier extend beyond this boundary, making the total area non-standard
- **AND** the raw data exists in `raw_map_data/the_falklands/` but is intentionally not processed

#### Scenario: Exclusion documented in AGENTS.md
- **WHEN** an agent reads `AGENTS.md` for project context
- **THEN** the note about `the_falklands` exclusion is present
- **AND** agents do not attempt to process this map without explicit instructions
