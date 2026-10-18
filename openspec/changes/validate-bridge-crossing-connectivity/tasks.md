## 1. Annotation contract and inventory

- [ ] 1.1 Define the versioned per-map annotation JSON schema with map metadata, zero-or-many rotated rectangles, and no required confidence field.
- [ ] 1.2 Define review records and comment/disagreement format, including annotator/reviewer IDs, evidence locations, dispositions, and user-adjudication status.
- [ ] 1.3 Generate the canonical sorted 85-map inventory and reject missing or duplicate minimap inputs.
- [ ] 1.4 Implement deterministic assignment manifests with 10 annotators and 10 disjoint reviewers, exactly two or more views per map per round, and a coverage validator that prints under-covered maps.

## 2. Annotation and independent review

- [ ] 2.1 Dispatch 10 annotator subagents over the generated manifest; each inspects assigned minimap.png files and records every visible bridge or an explicit empty result.
- [ ] 2.2 Validate annotator output schema, map coverage, rectangle bounds, finite values, and source image dimensions without silently repairing geometry.
- [ ] 2.3 Dispatch 10 independent reviewer subagents over the reviewer manifest; each inspects minimap.png and annotator output, records an independent disposition, and flags disagreements.
- [ ] 2.4 Produce a consolidated disagreement report for user adjudication; do not promote flagged records to approved routing inputs.
- [ ] 2.5 Freeze the user-approved annotation and review manifests with content hashes.

## 3. Geometry and QA rendering

- [ ] 3.1 Implement world-to-minimap and minimap-to-world conversion using the existing top-left flow convention and preserve 1024/2048 image-size handling.
- [ ] 3.2 Derive rectangle corners and two endpoint bands from center, angle, width, and length; reject invalid or out-of-bounds geometry.
- [ ] 3.3 Render approved rectangles and IDs over source minimaps without changing base pixels; add a deterministic round-trip geometry check.
- [ ] 3.4 Add synthetic tests for axis-aligned, diagonal, boundary, multi-bridge, and no-bridge annotations.

## 4. Crossing validation and terrain integration

- [ ] 4.1 Derive passable approach regions on both rectangle ends from the existing terrain cost grid.
- [ ] 4.2 Validate local separation with the rectangle disabled and reconnection with the reviewed rectangle enabled, preserving terrain hazards and diagonal-corner rules.
- [ ] 4.3 Emit per-bridge connector records with verdict, approach cells, derived corners, rejection reason, and annotation/review hashes.
- [ ] 4.4 Gate only validated connector cells into vehicle terrain artifacts; preserve independent water, ordinary-road, boat, helicopter, infantry, and ballistics behavior.
- [ ] 4.5 Add synthetic regression tests for valid crossings, ordinary roads, missing banks, disconnected rectangles, isolated islands, and mismatched provenance.

## 5. Flow regeneration and acceptance

- [ ] 5.1 Add deterministic QA rendering for connector masks and per-bridge flow reachability diagnostics.
- [ ] 5.2 Run focused processor tests with the unsafe manifest-overwrite test excluded, then run the safe processor suite.
- [ ] 5.3 Regenerate only explicitly approved maps and compare protected non-bridge artifacts before and after.
- [ ] 5.4 Document the minimap evidence ceiling: annotations represent reviewed visual geometry, not proof of in-game collision or bank connectivity.
- [ ] 5.5 Record unresolved disagreements, rejected annotations, test output, hashes, and approved map scope in the change artifacts.