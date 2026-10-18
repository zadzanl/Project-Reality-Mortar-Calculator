# Bridge-aware terrain traversability task record

- Revision: 1
- Intent: preserve and validate bridge evidence before changing terrain costs or regenerating flow artifacts.
- User approval: implement the planned bridge phases with delegated subagents.
- Constraints: no raw archive edits; no new dependencies; do not process `the_falklands`; exclude `processor/tests/test_update_manifest.py`; preserve existing road/water/boat/helicopter behavior unless evidence gates pass.
- Evidence: `artifacts/research-bridge-evidence-001.md`, `artifacts/research-bridge-integration-001.md`.
- Design: `artifacts/design-bridge-001.md`.
- Technical plan: `artifacts/tech-plan-bridge-001.md`.

## Decisions

1. Start with additive extraction only. A bridge name without a server-referenced, successfully decoded mesh is not traversability evidence.
2. Keep bridge candidates separate from ordinary roads and static objects.
3. Do not change terrain costs until the five primary fixture maps pass extraction and geometry review.
4. Bridge-aware terrain artifacts, if approved, will use a versioned additive mask and explicit provenance.

## Handoffs

- Veteran Engineer: HOLD MY BEER; identified the evidence and fixture gate.
- Explorers: research artifacts written under `artifacts/`.
- Designer and Technical Planner: design and implementation plan written under `artifacts/`.

## Resumption (2026-10-03)

- Revision: 2. User resumed bridge remediation with corrections.
- User communication (verbatim):
  > Plan looks good. One slight correction: Lets not regenerate all maps. Lets regenerate only a handful of maps, with two of them being carentan and al basrah, the rest is up to you. Assign an explorer to inspect whether the bridge works by sliding the flow time slider, then revise/adjust according to this explorer inspection. Other than that, please proceed with implementation. I've switched your environment from Planning (previous) to Orchestration (current). Make sure to delegate and orchestrate tasks to subagents.
- Corrected scope: regenerate carentan, tad_sae, albasrah_2 (raw name; user said "al basrah"), kunar_province, krivaja_valley, shijiavalley — NOT full corpus.
- Discovered: albasrah_2 has raw archives but NO processed_maps entry at all; it needs a full processed build, not just bridge regeneration.
- Browser QA is Explorer-led per user instruction, not orchestrator-led.
- Outstanding from prior round: B-01 false-unavailable branch at `extract_obstructions.py:224` (review-bridge-phase1-002.md, NEEDS_REVISION, MAJOR blocking defect, not yet fixed).

## Verification

- Pending Phase 1 extractor implementation and focused tests.
- Pending primary fixture gate before cost integration.
