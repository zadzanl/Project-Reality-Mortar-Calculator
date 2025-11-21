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
## ADDED Requirements

### Requirement: Theme Toggle Control

The system SHALL provide a checkbox input labeled "Dark Mode" in the header (immediately after the map size dropdown) that toggles the application between light and dark color schemes.

**Purpose:** Allow users to switch between light and dark color schemes.

**Implementation:**
- Checkbox input with label "Dark Mode"
- Located in header after map size dropdown
- Keyboard accessible (Tab + Space) and activatable with Space
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

The system SHALL persist the user's selected theme across browser sessions by storing a `pr_theme_mode` value in localStorage with the strings `"light"` or `"dark"`.

**Purpose:** Remember user's theme choice across browser sessions.

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

The system SHALL define a set of CSS variables in the `:root` selector for the default (light) theme and SHALL override those variables under the `body.dark-mode` selector for the dark theme. The system SHALL use `var(--name)` variables everywhere instead of hardcoded colors to ensure theme switching works reliably.

**Purpose:** Centralize color definitions for easy theme switching.

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
  ## ADDED Requirements

  ### Requirement: Theme Toggle Control

  The system SHALL provide a checkbox input labeled "Dark Mode" in the header (immediately after the map size dropdown) that toggles the application between light and dark color schemes.

  **Purpose:** Allow users to switch between light and dark color schemes.

  **Implementation:**
  - Checkbox input with label "Dark Mode"
  - Located in header after map size dropdown
  - Keyboard accessible (Tab + Space) and activatable with Space
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

  The system SHALL persist the user's selected theme across browser sessions by storing a `pr_theme_mode` value in localStorage with the strings `"light"` or `"dark"`.

  **Purpose:** Remember user's theme choice across browser sessions.

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

  The system SHALL define a set of CSS variables in the `:root` selector for the default (light) theme and SHALL override those variables under the `body.dark-mode` selector for the dark theme. The system SHALL use `var(--name)` variables everywhere instead of hardcoded colors to ensure theme switching works reliably.

  **Purpose:** Centralize color definitions for easy theme switching.

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

  The map visualization SHALL retain readability and contrast when the dark theme is active. Map grid lines, labels, markers, and overlays SHALL use colors which meet WCAG contrast requirements against the active map background.

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

  The system SHALL apply a saved theme (or default theme for first-time users) synchronously before stylesheets render, via a small inline script in the HTML head, to prevent a flash of the wrong theme.

  **Purpose:** Apply theme before page renders to prevent visual flash.

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

  The system SHALL comply with WCAG 2.1 Level AA for both themes. Text contrast SHALL be at least 4.5:1 and UI components SHALL achieve at least 3:1 contrast.

  **Purpose:** Maintain readability and usability for all users.
