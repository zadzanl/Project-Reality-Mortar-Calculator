# Tasks: Swiss-Style UI Overhaul

## Phase 1 — Design tokens and fonts

- [ ] 1.1 Download Inter woff2 (weights 400/500/700/800) from the official Inter release; place in `calculator/static/fonts/` with the OFL license file; record version in a README note inside the folder
- [ ] 1.2 Add `@font-face` blocks and the token layer (`:root` + `html.dark-mode` overrides) to `styles.css` per `design.md` — spacing, hairlines, type scale, palette
- [ ] 1.3 Verify accent contrast pairs with a contrast checker (AA: 4.5:1 text, 3:1 controls); adjust lightness only if needed

## Phase 2 — HTML restructure (`index.html`)

- [ ] 2.1 Formalize the tabbed tool shell in the template so `restructureToolShell()` in `app.js` has nothing (or minimal) left to build; keep every existing element ID unchanged
- [ ] 2.1a Merge Coordinates and Firing Solution into ONE left side panel (~320px) with native `<details>/<summary>` sections — "Firing Solution" expanded by default, "Coordinates" collapsed by default; map fills remaining width; geometric disclosure markers (depends on 2.1)
- [ ] 2.2 Remove all inline `style="..."` attributes; replace with semantic classes
- [ ] 2.3 Merge the two marker-placement hints into one line; consolidate height-offset help to one line
- [ ] 2.4 Group Show Grid / Terrain Map / Contour Map under a "Map layers" group
- [ ] 2.5 Relabel Map Size override option to "Auto (from metadata)"; control stays in the header
- [ ] 2.6 Slim `restructureToolShell()` in `app.js` to match the now-static shell (depends on 2.1)

## Phase 3 — CSS reskin (both themes)

- [ ] 3.1 Restyle header, tabs, panels, dropdowns, buttons, inputs per design system (square corners, hairlines, olive accent)
- [ ] 3.2 Restyle results panel: mils readout as the typographic centerpiece (32–40px/800), status line with muted military status tones
- [ ] 3.3 Restyle dark theme to the same system with pitch black `#000000` backgrounds, `#2A2A26` hairlines, sage olive accent; controls may carry accent colors on the black field
- [ ] 3.4 Delete the duplicated `.theme-toggle` block and dead pre-restructure panel CSS found in the audit
- [ ] 3.5 Restyle flow-tab controls via CSS only — no ID or structure changes (coordinate with active `add-opening-flow-simulator` before merging)

## Phase 4 — Map chrome

- [ ] 4.1 Restyle Leaflet zoom controls, attribution, and popups/tooltips
- [ ] 4.2 Restyle PR grid labels and range-circle color to the palette
- [ ] 4.3 Replace default Leaflet pins with custom `divIcon` markers: filled blue dot (mortar) and dark-red SVG crosshair (target), including the out-of-range warning treatment

## Phase 5 — Folded-in bug fixes

- [ ] 5.1 Fix map loading overlay not reappearing on subsequent map loads
- [ ] 5.2 Unify status wording ("Ready to calculate" vs JS reset text) into one state model

## Phase 6 — Verification and sync

- [ ] 6.1 Run `node calculator/tests/run-tests.js` — all existing tests pass
- [ ] 6.2 Manual check: light + dark themes, map load flow, marker place/drag, calculate, layer toggles, flow tab renders
- [ ] 6.3 Manual check: Android-width viewport (<768px) and tablet (768–1200px) per layout spec
- [ ] 6.4 Run `build-android.bat` to regenerate `www/` and sync to Android assets
- [ ] 6.5 Reconcile the "Three-Column Desktop Layout" requirement in `openspec/specs/calculator-ui/spec.md` with the implemented shell (via this change's spec delta)
