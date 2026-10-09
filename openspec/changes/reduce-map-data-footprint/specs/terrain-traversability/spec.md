# terrain-traversability Specification Delta

## MODIFIED Requirements

### Requirement: Deterministic terrain artifacts
The terrain pipeline SHALL produce deterministic per-map outputs containing a compact cost grid, diagnostic metadata, source coverage, configuration provenance, and enough information for a later offline flow solver to consume the grid without recomputing terrain physics. Continuous grids SHALL be serialized as quantized integers (format version "1.2"): each grid's sidecar entry SHALL record `dtype`, `offset`, and `scale`, and dequantization SHALL follow `value = offset + quantized * scale`. Thresholded continuous grids (maximum slope, edge rise, edge grade) SHALL use uint16; non-thresholded diagnostic grids MAY use uint8; masks SHALL remain uint8 with exact sentinel values. The loader SHALL accept format versions 1.0 and 1.1 (float32 grids; 1.0 with an all-zero bridge mask) as well as 1.2.

#### Scenario: Repeatable processing
- **WHEN** the same heightmap, obstruction input, metadata, and terrain configuration are processed twice
- **THEN** the cost grid and sidecar are byte-for-byte equivalent or equivalent under a documented serialization normalization
- **AND** no browser or external service is required

#### Scenario: Later flow integration
- **WHEN** a later flow solver loads the terrain artifact
- **THEN** it can obtain grid dimensions, origin, cell size, units, costs, passability sentinel, source coverage, and movement-parameter provenance from the artifact set
- **AND** it does not need to recalculate slope or roughness

#### Scenario: Quantized round-trip
- **WHEN** a continuous grid is written as format 1.2 and read back
- **THEN** every dequantized cell differs from the writer's float32 value by no more than half the recorded scale
- **AND** blocked/unreachable sentinel cells decode to the exact documented sentinel

#### Scenario: Legacy formats still load
- **WHEN** the loader reads a format 1.0 or 1.1 artifact set
- **THEN** float32 grids load with their original values
- **AND** a format 1.0 set loads with an all-zero bridge mask
- **AND** the sidecar-reported version determines the decode path
