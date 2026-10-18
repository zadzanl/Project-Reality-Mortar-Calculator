## Context

The existing bridge implementation decodes bridge-named client meshes, rasterizes their triangles into `bridge_mask.bin`, and permits candidate cells in the wheeled-vehicle cost grid. It does not establish that a candidate deck joins two distinct traversable regions. Production evidence confirms the gap: Krivaja Valley has 398 candidate cells, but only 133 and 265 are reachable for the two truck source sets, and none overlap confirmed water. The browser therefore renders a normal expanding frontier without proving a bridge crossing.

The repair must remain offline and deterministic, use the existing terrain and flow artifacts, avoid raw archive edits and new dependencies, and preserve boat, helicopter, infantry, ordinary-road, and ballistics behavior.

## Goals / Non-Goals

**Goals:**

- Determine per decoded bridge whether its deck forms a usable vehicle crossing between two distinct approach regions.
- Produce actionable endpoint, deck, component, and rejection diagnostics.
- Permit only validated candidate or confirmed crossings to affect vehicle flow fields.
- Keep candidate/unverified provenance explicit and preserve backward-readable terrain artifacts where practical.
- Validate individual bridges with synthetic fixtures and representative map reports before regeneration.

**Non-Goals:**

- Proving in-game collision meshes, bank collision, vehicle physics, or multiplayer gameplay truth.
- Inferring bridges from names, static templates, minimap colors, flatness, or ordinary road-over-water geometry.
- Changing boat navigation, helicopter movement, infantry movement, mortar ballistics, or browser-side pathfinding.
- Automatically repairing malformed raw archives or publishing the full map corpus.

## Decisions

### 1. Add a bridge-crossing capability instead of rewriting the old flow feature

The existing Flow specification describes field consumption and visualization; it does not own bridge evidence semantics. This change adds `bridge-crossing-connectivity` and modifies the terrain-traversability contract. The earlier candidate behavior remains historical context rather than being silently redefined.

### 2. Validate crossings by local separation and reconnection

For each decoded bridge mesh:

1. Rasterize the finite deck triangles exactly as today, without dilation.
2. Derive two endpoint neighborhoods from the deck's dominant axis and endpoint bands.
3. Find passable vehicle cells near both endpoints using the same terrain profile that flow consumes.
4. Build a bounded local corridor around the deck and its endpoint approaches; do not require either endpoint to belong to a map-wide land component.
5. Temporarily remove the bridge cells and test whether the two local approaches are disconnected within that corridor.
6. Enable the deck and require the two local approaches to reconnect within that corridor.

The local rule is intentional: a bridge on an island or in a lake can be valid even when the surrounding map has no connected mainland component. Global component IDs remain diagnostic only. This does not depend on confirmed-water detection, which is incomplete on current fixtures. It rejects a bridge-named mesh that is already connected through nearby ordinary terrain, while avoiding false rejection of isolated legitimate bridges.

### 3. Keep masks, add explicit crossing records

Retain `bridge_mask.bin` for diagnostics and artifact compatibility, but populate its routing-permitted values only from crossing records that pass validation. Add a sidecar `bridge_crossings` collection containing endpoint cells, approach cells, deck cell count, component identifiers, verdict, policy permission, and rejection reason. Existing candidate values remain visibly unverified; an unvalidated candidate receives no vehicle route.

### 4. Keep solver changes narrow

The Dijkstra solver continues consuming a cost grid and existing diagonal-corner guard. The terrain stage gates which bridge cells become passable; the flow stage propagates crossing provenance and runs individual-crossing reachability checks in validation. No browser solver or special client-side bridge logic is introduced.

### 5. Test the bridge as a route, not as a painted region

Synthetic tests SHALL place sources on opposite approaches and assert that the opposite side is reachable only when a validated crossing is enabled. Representative validation SHALL report per-bridge results, not just total mask cells. A passing slider screenshot is supplementary UI evidence, not a crossing proof.

## Risks / Trade-offs

- **[Risk]** Endpoint search may reject narrow or diagonally oriented real decks. → Use geometry-derived endpoint bands, configurable bounded search radius, exact diagnostics, and fixture-driven tuning; never silently widen the deck.
- **[Risk]** Vehicle cost hazards may block a real deck approach. → Report the blocking feature and preserve the hard hazard by default; add an explicit reviewed connector rule only if representative evidence supports it.
- **[Risk]** A bridge may cross an undetected barrier rather than confirmed water. → Local graph separation/reconnection detects whether the deck is functionally necessary without claiming the barrier is water.
- **[Risk]** An isolated lake or island bridge may have no useful map-wide land component. → Global component membership is never a validation prerequisite; bounded endpoint-to-endpoint reconnection is authoritative.
- **[Risk]** Terrain format changes can leave stale flow generations. → Include crossing records and all bridge-dependent terrain inputs in generation identity; reject mixed sidecars and regenerate only approved fixtures first.
- **[Risk]** Candidate routing can still be mistaken for in-game truth. → Keep `candidate`/`unverified` labels and document the collision/bank ceiling in sidecars, UI, and QA reports.

## Migration Plan

1. Implement and test diagnostics without changing production outputs.
2. Run isolated validation on Carentan, Krivaja Valley, Tad Sae, Kunar Province, and Al Basrah 2; inspect per-bridge verdicts.
3. Regenerate only explicitly approved fixture maps and compare protected non-bridge outputs.
4. If a regression appears, revert the crossing-permission gate while retaining additive diagnostics and the prior format loader.
5. Expand map coverage only after representative evidence and review approve it.

## Open Questions

- What endpoint search radius best matches the 4 m and 8 m grids without inventing a road connection?
- Should an endpoint blocked only by a documented bridge-deck slope/edge artifact receive a reviewed connector exception, or remain rejected?
- How should a bridge with a valid local crossing but no global mainland component be surfaced in the UI? The proposed answer is `candidate/unverified`, not rejection.
- Which Al Basrah asset represents its apparent crossings if no bridge mesh is decoded from the current server/client pair?
