## 1. Connectivity diagnostics

- [x] 1.1 Define deterministic bridge endpoint and approach-cell derivation from decoded deck triangles, including bounded search configuration.
- [x] 1.2 Implement passable-component analysis with bridge cells disabled and enabled, preserving vehicle terrain hazards and diagonal-corner rules.
- [x] 1.3 Emit per-bridge endpoint, approach, component, deck-continuity, verdict, permission, and rejection-reason records.

## 2. Terrain artifact integration

- [x] 2.1 Integrate crossing validation into terrain generation without changing ordinary road or water masks.
- [x] 2.2 Gate vehicle bridge passability on validated crossing records while retaining candidate/unverified provenance.
- [x] 2.3 Extend terrain artifact validation and generation identity to cover crossing records and reject mixed or inconsistent artifacts.
- [x] 2.4 Preserve legacy format 1.0 loading and keep boat/helicopter/infantry behavior unchanged.

## 3. Flow integration

- [x] 3.1 Load validated crossing provenance in the flow generator and propagate per-bridge status to flow sidecars.
- [x] 3.2 Add an offline individual-crossing reachability diagnostic using sources on both bridge approaches.
- [x] 3.3 Ensure browser slider and sidebar distinguish validated candidate crossings from detected-but-unrouted geometry without adding browser pathfinding.

## 4. Tests and representative validation

- [x] 4.1 Add synthetic tests for separated regions, valid deck reconnection, disconnected decks, blocked endpoints, zero-cell geometry, and ordinary-road false positives.
- [x] 4.2 Add terrain-artifact tests for deterministic crossing records, malformed provenance, version compatibility, and unchanged water bytes.
- [x] 4.3 Add flow tests proving a vehicle reaches the opposite approach only with a validated crossing, while boats, helicopters, and infantry retain existing behavior.
- [x] 4.4 Run isolated representative validation for Carentan, Krivaja Valley, Tad Sae, Kunar Province, Al Basrah 2, Beirut, Lashkar Valley, and Pavlovsk Bay; record one verdict per bridge, including isolated lake/island cases.
- [x] 4.5 Regenerate only explicitly approved fixture maps and compare protected artifacts before any wider rollout.
- [x] 4.6 Add a bounded single-placement static collision probe for Krivaja; preserve raw provenance and fail closed as unresolved/non-routable when format or transform semantics are unverified.

## 5. Documentation and acceptance

- [x] 5.1 Update bridge provenance documentation and maintainer instructions with the crossing-record contract and known collision/bank ceiling.
- [x] 5.2 Run focused processor tests, the safe processor suite, frontend tests, deterministic repeat checks, and diff checks.
- [x] 5.3 Confirm acceptance criteria from the bridge-crossing-connectivity and terrain-traversability specs; record unresolved real-game verification limits.
