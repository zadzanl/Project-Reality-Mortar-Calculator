## Why

Automatic bridge detection produced unreliable routing evidence. The replacement must begin with deterministic, human-auditable annotations from every map's `minimap.png`, then derive bank connections from approved bridge rectangles instead of inferring bridges from mesh names or incomplete collision data.

## What Changes

- Create one annotation artifact for every processed map, including explicit no-bridge results.
- Represent each bridge as a rotated rectangle in the existing flow/world coordinate convention.
- Dispatch two independent inspection rounds: annotators and reviewers, with deterministic overlap so every map is inspected at least twice per round.
- Record reviewer disagreements for user adjudication instead of silently resolving them.
- Derive the two bridge-side approach regions from rectangle geometry and validate terrain/bank connectivity before enabling vehicle traversal.
- Render bridge annotations and resulting crossing decisions on QA minimaps and regenerate flow maps only for approved outputs.
- Remove the superseded automatic decoded-mesh crossing logic; do not change boats, helicopters, infantry, ballistics, or raw archives.

## Capabilities

### New Capabilities
- `bridge-crossing-annotation`: Defines map annotation files, rotated bridge rectangles, assignment manifests, review evidence, and disagreement handling.

### Modified Capabilities
- `terrain-traversability`: Consumes approved rectangle annotations and derives validated crossing passability without treating every rectangle interior as automatically traversable.

## Impact

Affected areas include new processor annotation/validation tooling, per-map annotation artifacts, terrain-cost integration, flow QA rendering, and OpenSpec documentation. No new dependencies or external services are planned. Existing unrelated dirty work must be preserved during implementation.