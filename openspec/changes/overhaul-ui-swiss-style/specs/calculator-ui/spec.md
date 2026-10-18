# calculator-ui Spec Delta: Swiss-Style UI Overhaul

## ADDED Requirements

### Requirement: Swiss Design System

The system SHALL style all UI chrome (header, tabs, panels, controls, results) from a single design-token layer of CSS custom properties: an 8px spacing base unit, 1px hairline borders as the primary grouping device, square corners (`border-radius: 0`) on UI chrome, and a reduced palette of a monochrome base plus olive drab as the single primary accent and dark red reserved for target/out-of-range/error semantics.

#### Scenario: Token-driven themes
- **WHEN** the page loads in either theme
- **THEN** all colors, spacing, and typography resolve from CSS custom properties
- **AND** no inline `style` attributes remain in `index.html`

#### Scenario: Accent discipline
- **WHEN** any interactive element is rendered
- **THEN** olive drab marks primary actions, active tab state, and focus rings
- **AND** dark red appears only for the target marker, OUT OF RANGE status, and error states
- **AND** contrast meets WCAG AA (>= 4.5:1 body text, >= 3:1 controls) in both themes

#### Scenario: Dark theme parity
- **WHEN** the user toggles dark mode
- **THEN** the same grid, typography, and token structure applies with pitch black `#000000` backgrounds, visible hairlines, and a lighter olive accent
- **AND** the `pr_theme_mode` localStorage behavior is unchanged

### Requirement: Vendored Typography

The system SHALL load the Inter typeface from woff2 files vendored under `calculator/static/fonts/` (OFL licensed, license file included) via `@font-face`, with a system sans-serif fallback stack. The UI SHALL NOT load fonts from any CDN or external origin.

#### Scenario: Offline font loading
- **WHEN** the app loads with no network connection
- **THEN** Inter renders in weights 400/500/700/800 as declared
- **AND** if the font files fail to load, the fallback stack renders without layout-breaking shifts

#### Scenario: Typographic hierarchy
- **WHEN** the results panel displays a firing solution
- **THEN** the mils value is the typographic centerpiece (largest type on screen)
- **AND** section titles use uppercase letter-spaced micro-labels

### Requirement: Restyled Map Chrome

The system SHALL style Leaflet zoom controls, attribution, popups, PR grid labels, and the range circle consistently with the design-token palette in both themes.

#### Scenario: Controls match theme
- **WHEN** a map is displayed in either theme
- **THEN** zoom controls, attribution, and popups use token colors and square corners
- **AND** grid labels remain legible over terrain imagery
- **AND** the range circle uses the palette-defined color at 30% fill opacity

#### Scenario: Thematic markers
- **WHEN** mortar and target positions are placed on the map
- **THEN** the mortar marker is a filled blue dot
- **AND** the target marker is a dark-red geometric crosshair (thin-stroke circle with four outward ticks)
- **AND** the two markers differ by shape as well as color

### Requirement: Simplified Control Surface

The system SHALL present each piece of guidance exactly once: a single marker-placement hint, a single height-offset help line, and one grouped "Map layers" control set. The Map Size override SHALL remain available in the header, labeled "Auto (from metadata)" for its automatic option.

#### Scenario: No duplicated hints
- **WHEN** the user views the inputs and results panels
- **THEN** marker-placement instructions appear exactly once
- **AND** height-offset guidance appears exactly once

#### Scenario: Map size override retained
- **WHEN** the user needs to correct unreliable map metadata
- **THEN** the Map Size override is available in the header with options Auto (from metadata), 1km, 2km, 4km

### Requirement: Single Side Panel with Collapsible Sections

The system SHALL present Coordinates and Firing Solution as two collapsible sections within a single side panel on the left (~320px), using native disclosure elements; the map SHALL fill all remaining viewport width. The tool-shell structure SHALL be described statically in `index.html`; runtime JavaScript SHALL NOT reparent panels to construct the layout.

#### Scenario: Default section states
- **WHEN** the page loads
- **THEN** the "Firing Solution" section is expanded
- **AND** the "Coordinates" section is collapsed

#### Scenario: Section toggle
- **WHEN** the user activates a collapsed section header
- **THEN** the section expands to reveal its controls
- **AND** the interaction is keyboard accessible

#### Scenario: Static shell
- **WHEN** the page loads with JavaScript disabled
- **THEN** the header, tabs, side panel, and map region are present in the DOM as authored

## REMOVED Requirements

### Requirement: Three-Column Desktop Layout

**Reason:** Superseded by the single-side-panel shell (user decision, 2026-10-02). Coordinates and Firing Solution merge into one collapsible left panel; the map fills the remaining width.
