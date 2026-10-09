# map-processor Specification Delta

## ADDED Requirements

### Requirement: Compact obstruction artifact serialization

The system SHALL write each map's obstruction artifact as gzipped compact JSON (`obstructions.json.gz`) using separators `(',', ':')` with float coordinates rounded to a documented precision of 0.1 meter or finer. The loader contract (field names, nesting, units, coordinate reference frame) SHALL remain identical to the pretty-printed form. The writer SHALL report per-map uncompressed and compressed byte sizes.

#### Scenario: Large map compaction
- **WHEN** obstructions are extracted for a map whose pretty-printed artifact exceeded 100 MB (e.g. fields_of_kassel)
- **THEN** the written artifact is `obstructions.json.gz` with compact separators and rounded coordinates
- **AND** the compressed size is reported and is at least 5x smaller than the pretty-printed form
- **AND** decoding the artifact yields the same record count and bounding boxes within 0.1 meter

#### Scenario: Loader contract unchanged
- **WHEN** a consumer decodes `obstructions.json.gz`
- **THEN** field names, nesting, units, and coordinate reference frame match the previous JSON artifact
- **AND** no consumer changes are required beyond gzip decoding

#### Scenario: Legacy artifact superseded
- **WHEN** the gzipped artifact is written for a map
- **THEN** any stale pretty-printed `obstructions.json` for that map is removed during the cleanup pass
- **AND** the map remains loadable by the terrain pipeline
