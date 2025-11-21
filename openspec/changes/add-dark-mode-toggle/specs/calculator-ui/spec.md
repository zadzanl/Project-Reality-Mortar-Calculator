# calculator-ui Spec: Dark Mode Feature

## ADDED Requirements

### Requirement: Theme Toggle Control

**Purpose:** Allow users to switch between light and dark color schemes.

**Implementation:**
- Checkbox input with label "Dark Mode"
- Located in header after map size dropdown
- Keyboard accessible (Tab + Space)
- Styled inline for simplicity

#### Scenario: Display toggle control
**WHEN** page loads  
**THEN** toggle appears in header right section  
**AND** checkbox reflects current theme (checked = dark)  
**AND** label reads "Dark Mode"

#### Scenario: Toggle dark mode ON
**WHEN** user clicks unchecked toggle  
**THEN** `body` element gets class `dark-mode`  
**AND** all colors switch to dark theme instantly  
**AND** preference saved to localStorage as `pr_theme_mode: "dark"`

#### Scenario: Toggle dark mode OFF
**WHEN** user clicks checked toggle  
**THEN** `dark-mode` class removed from `body`  
**AND** all colors revert to light theme instantly  
**AND** preference saved to localStorage as `pr_theme_mode: "light"`

#### Scenario: Keyboard interaction
**WHEN** user presses Tab key  
**THEN** toggle receives focus with visible outline  
**WHEN** user presses Space key while focused  
**THEN** theme toggles ON or OFF

---

### Requirement: Theme Persistence

**Purpose:** Remember user's theme choice across browser sessions.

**Storage:** localStorage key `pr_theme_mode` with values `"light"` or `"dark"`

#### Scenario: Save theme preference
**WHEN** user toggles theme  
**THEN** choice saved to localStorage immediately  
**AND** console logs: `"Theme: dark"` or `"Theme: light"`

#### Scenario: Restore saved theme
**WHEN** page loads AND localStorage contains `pr_theme_mode`  
**THEN** saved theme applied before page renders  
**AND** toggle checkbox updated to match theme  
**AND** no flash of wrong theme visible

#### Scenario: First-time user (no saved preference)
**WHEN** page loads AND no `pr_theme_mode` in localStorage  
**THEN** dark theme used by default  
**AND** toggle checked

#### Scenario: localStorage unavailable
**WHEN** localStorage throws error (privacy mode, disabled)  
**THEN** theme toggle still works  
**AND** error logged to console  
**AND** theme resets to light on each page load

---

### Requirement: CSS Variable Architecture

**Purpose:** Centralize color definitions for easy theme switching.

**Structure:**
- Define variables in `:root` selector (light theme defaults)
- Override variables in `body.dark-mode` selector (dark theme)
- Replace ALL hardcoded colors with `var(--variable-name)`

#### Scenario: Light theme colors (default)
**WHEN** NO `dark-mode` class on body  
**THEN** CSS uses these variable values:
- Background: `#f5f5f5` (body), `#ffffff` (panels)
- Text: `#333333` (primary), `#666666` (secondary)
- Buttons: `#3498db` (primary), `#27ae60` (calculate)
- Borders: `#dddddd` (default), `#3498db` (focus)

#### Scenario: Dark theme colors
**WHEN** `dark-mode` class present on body  
**THEN** CSS overrides to these values:
- Background: `#1a1a1a` (body), `#2d2d2d` (panels)
- Text: `#e0e0e0` (primary), `#b0b0b0` (secondary)
- Buttons: `#4a9eff` (primary), `#2ecc71` (calculate)
- Borders: `#444444` (default), `#4a9eff` (focus)

#### Scenario: Status message colors
**WHEN** either theme active  
**THEN** status messages use appropriate contrast:
- **Light theme:**
  - Success: Green background `#d4edda`, dark text `#155724`
  - Warning: Yellow background `#fff3cd`, dark text `#856404`
  - Error: Red background `#f8d7da`, dark text `#721c24`
- **Dark theme:**
  - Success: Dark green bg `#1e4620`, bright text `#90ee90`
  - Warning: Dark yellow bg `#4a3c1a`, bright text `#ffd966`
  - Error: Dark red bg `#4a1e1e`, bright text `#ff6b6b`

---

### Requirement: Map Element Theme Support

**Purpose:** Ensure map visualization remains visible in dark theme.

#### Scenario: Grid lines in dark theme
**WHEN** dark theme active  
**THEN** grid lines remain visible  
**AND** labels have sufficient contrast against dark background  
**AND** label background opacity increased to `rgba(0, 0, 0, 0.8)`

#### Scenario: Markers in both themes
**WHEN** either theme active  
**THEN** blue mortar marker clearly visible  
**AND** red target marker clearly visible  
**AND** range circle visible with appropriate opacity

---

### Requirement: Flash Prevention

**Purpose:** Apply theme before page renders to prevent visual flash.

**Implementation:** Inline `<script>` tag before CSS loads

#### Scenario: Prevent theme flash
**WHEN** page loads with saved dark theme  
**THEN** `dark-mode` class applied synchronously  
**AND** CSS loads with correct theme already applied  
**AND** user never sees light theme flash

#### Scenario: Inline script execution
**WHEN** HTML parser reaches inline script  
**THEN** script reads localStorage  
**AND** applies class to `body` immediately  
**AND** execution completes before CSS render

---

### Requirement: Accessibility (WCAG AA)

**Purpose:** Maintain readability and usability for all users.

**Standards:** WCAG 2.1 Level AA
- Text contrast: ≥ 4.5:1
- UI components: ≥ 3:1

#### Scenario: Text contrast in light theme
**WHEN** light theme active  
**THEN** all text meets 4.5:1 contrast minimum  
**EXAMPLES:**
- Body text `#333` on white `#fff` = 12.6:1 ✓
- Secondary text `#666` on white = 5.7:1 ✓

#### Scenario: Text contrast in dark theme
**WHEN** dark theme active  
**THEN** all text meets 4.5:1 contrast minimum  
**EXAMPLES:**
- Body text `#e0e0e0` on `#2d2d2d` = 11.5:1 ✓
- Secondary text `#b0b0b0` on `#2d2d2d` = 6.8:1 ✓

#### Scenario: Interactive element contrast
**WHEN** either theme active  
**THEN** buttons, borders, focus indicators meet 3:1 minimum  
**AND** focus outlines clearly visible

#### Scenario: Avoid pure black
**WHEN** dark theme active  
**THEN** backgrounds use soft grays (NOT `#000000`)  
**REASON:** Pure black causes eye strain and halation effect

---

## UNCHANGED Requirements

All existing calculator-ui requirements remain active:
- Map selection and loading
- Coordinate input dropdowns
- Marker placement and dragging
- Firing solution calculation
- Results display
- Grid overlay
- Elevation sampling

**No changes to:**
- Ballistics engine
- Coordinate system
- Map processing
- Flask server
- Data formats

---

## Implementation Notes

**Files modified:**
1. `calculator/static/css/styles.css` - Add variables + replace colors
2. `calculator/templates/index.html` - Add toggle + inline script
3. `calculator/static/js/app.js` - Add toggle handler + function

**Estimated effort:** 2-3 hours

**Testing priority:**
1. Visual correctness (both themes)
2. Persistence across sessions
3. No flash on load
4. WCAG contrast ratios
5. Keyboard accessibility
