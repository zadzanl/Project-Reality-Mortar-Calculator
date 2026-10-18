# Design: Swiss-Style UI Overhaul

## Direction

International Typographic Style ("Swiss"), adapted for a milsim tool: the grid organizes, typography carries hierarchy, one accent color has one job. Reference: swissthemes.design "8 Swiss-Style Website Examples" — specifically the shared traits (grid-first, type-led hierarchy, reduced palette, whitespace as structure), not any single template.

## Accent color decision (user asked for recommendation)

User proposed military dark green + dark red. **Accepted, with discipline:** Swiss style tolerates exactly one decorative accent; a second color survives only if it carries fixed semantics. This app already has semantic colors worth keeping (blue mortar / red target / cyan range circle). So:

| Role | Color (light theme) | Dark theme | Job |
|------|--------------------|-----------|-----|
| Primary accent | Olive drab `#4B5320` | Sage olive `#8A9A5B` | Calculate button, active tab, focus ring, links |
| Semantic red | Dark red `#8B1A1A` | Muted red `#C0392B` | Target marker, OUT OF RANGE, errors |
| Mortar blue | `#2563EB` (unchanged) | `#60A5FA` | Mortar marker only |
| Range circle | Olive-tinted cyan replaced by olive drab at 30% fill | same | Max-range indicator |
| Status: in-range | olive tones | olive tones | IN RANGE |
| Status: extended | muted amber `#8A6D1A` | `#D4A017` | EXTENDED RANGE |
| Status: out | dark red | muted red | OUT OF RANGE |

Contrast check required during implementation: `#4B5320` on `#FAFAF8` ≈ 7.6:1 (passes AA); `#8A9A5B` on `#121210` ≈ 8:1 (passes). Verify final picks with a contrast checker; adjust lightness, never hue family.

## Tokens

- Base unit: 8px. Spacing scale: 4 / 8 / 16 / 24 / 32 / 48.
- Corners: `border-radius: 0` everywhere (map markers and flow objective dots excepted — they are map symbols).
- Borders: 1px hairlines (`#D8D8D2` light / `#33332E` dark) as the primary grouping device. No drop shadows on panels.
- Type scale (Inter): 11px uppercase letter-spaced micro-labels (section titles), 13px body, 16px values, 32–40px/800 for the primary mils readout.
- Backgrounds: light paper `#FAFAF8`, panels `#FFFFFF`; dark theme is **pitch black `#000000`** for body and panels (user decision, 2026-10-02 — overrides the earlier "no pure black" guidance from the dark-mode proposal, which never landed in the consolidated spec; pitch black wins on OLED phone screens during night ops, and WCAG AA contrast only gets easier). Dark hairlines lighten to `#2A2A26` so separation survives on black. Controls (buttons, dropdowns, checkboxes, toggle) may carry accent colors directly on the black field. No pure white body text.

## Typography

- Inter woff2, weights 400/500/700/800, vendored at `calculator/static/fonts/` with the OFL license text file. `@font-face` per weight, `font-display: swap`, fallback `-apple-system, 'Segoe UI', Roboto, Arial, sans-serif`.
- Source: official Inter release (rsms.me/inter or github.com/rsms/inter releases). Verify woff2 file integrity after download; record version + license in the fonts directory.

## Layout / shell

- Formalize in `index.html` the shell that `app.js` `restructureToolShell()` currently builds at runtime (tabs + tool panels). The template should describe the real structure so JS stops performing DOM surgery.
- **Single side panel (user decision, 2026-10-02):** the Coordinates and Firing Solution panels merge into ONE side panel on the LEFT (~320px); the map fills all remaining width. The panel holds two collapsible sections built on native `<details>/<summary>` (keyboard-accessible for free):
  1. **Firing Solution** — expanded by default (it is what the player reads in-game).
  2. **Coordinates** — collapsed by default (map click/drag is the primary positioning path; dropdowns are precision fallback).
- Disclosure markers are geometric (plus/minus or rotating triangle), never emoji.
- Reconcile the stale "Three-Column Desktop Layout" spec requirement with the implemented shell as part of this change (spec delta: REMOVE old layout requirement, ADD single-side-panel requirement).
- Header becomes a single rule-delimited bar: title (micro-label weight), map controls left-to-right, theme toggle last. Map Size override stays in the header, relabeled "Auto (from metadata)".

## Map markers

- **Mortar:** filled blue dot — a dot is the right symbol for "a position".
- **Target:** dark-red crosshair — thin-stroke circle (~14px, 2px) with four short outward ticks at 12/3/6/9 o'clock, small gap between circle and ticks, no fill. Accepted over a plain dot because the crosshair is constructed geometry with a functional meaning ("aim point"), which fits the Swiss reduction rule; it also differentiates target from mortar by shape, not just color (colorblind-safe). Implemented as Leaflet `divIcon` with inline SVG; replaces the current default Leaflet teardrop pins.
- Out-of-range target state: crosshair gains a warning treatment (thicker stroke or amber halo), distance display turns red — per existing spec behavior.

## Simplification decisions (from audit)

- One hint, bottom of the inputs panel: "Click: place target · Shift+Click: place mortar · Drag markers to refine."
- Height offset keeps its input; one help line only ("Each building floor ≈ 2.5m").
- Calculate button stays (spec-required) even though edits auto-calculate; it remains the visually primary action.
- Layer checkboxes grouped under "Map layers" in the results panel.
- Status model: one `#result-status` line with three states; map overlay used only while a map is actively loading (fixing the repeat-load bug).

## Out of scope (guardrails)

- No physics, coordinate, or server changes. No new JS dependencies. No CDN links.
- Flow-tab controls: restyle via CSS only; no ID or structural changes (owned by `add-opening-flow-simulator`).
- All existing element IDs are frozen (JS queries by ID; full list in `artifacts/research-ui-redundancy-audit.md`).

## Known ceiling

Inter is a static (non-variable) woff2 subset of 4 weights. If a future change needs more weights or a condensed cut for the mils readout, re-vendor from the same Inter release and add the `@font-face` block — no structural change needed.
