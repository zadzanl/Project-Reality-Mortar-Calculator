## Why

The current bridge remediation detects and rasterizes decoded bridge meshes, but it does not prove that a vehicle can travel from one bridge approach to the opposite bank. Production flow fields therefore show expanding frontiers while leaving many bridge decks unreachable; on Krivaja Valley only 133/398 candidate deck cells were reachable for team 1 and 265/398 for team 2, with no candidate cells overlapping confirmed water. The candidate mask is being treated as routing evidence when it is only geometry evidence.

## What Changes

- Add per-bridge endpoint, approach, deck-continuity, and bank-connectivity diagnostics.
- Distinguish decoded bridge geometry from a validated vehicle crossing.
- Define explicit bridge crossing records that flow generation can consume, rather than relying on an undifferentiated bridge-cell mask.
- Reject incomplete, disconnected, blocked-endpoint, or zero-cell crossings with actionable reasons.
- Add synthetic and representative tests that verify source-to-opposite-bank reachability for individual bridges.
- Keep candidate provenance visible; do not claim in-game collision or bank truth without evidence.
- Preserve existing boat, helicopter, infantry, ordinary-road, and ballistics behavior.

## Capabilities

### New Capabilities

- `bridge-crossing-connectivity`: Establishes the contract for validating decoded bridge decks as traversable vehicle crossings and publishing explicit crossing diagnostics and links.

### Modified Capabilities

- `terrain-traversability`: Changes bridge handling from candidate-cell permission alone to endpoint- and connectivity-gated crossing records.

## Impact

- Affects bridge extraction and terrain artifact generation in `processor/extract_obstructions.py`, `processor/build_terrain_cost.py`, and `processor/terrain_artifact.py`.
- Affects vehicle flow generation and sidecar provenance in `processor/build_flow_fields.py`.
- Adds focused processor tests and representative validation reports.
- May change terrain format 1.1 bridge metadata and invalidate regenerated bridge-dependent flow generations.
- No new dependencies, raw archive edits, external services, or browser-side pathfinding.
