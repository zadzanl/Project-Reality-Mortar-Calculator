# Add Dark Mode Toggle

## Why

Players use the calculator during night gameplay sessions. Current light-only interface causes eye strain in low-light conditions. Add dark mode toggle to reduce eye fatigue.

## What Changes

**Add to header (after map size override):**
- The header SHALL include a checkbox-based toggle with the label "Dark Mode".
- The toggle control SHALL be styled consistently with existing header controls and SHALL be keyboard accessible (Tab + Space).

**CSS architecture:**
- The application SHALL define CSS variables in the `:root` selector for the base (light) theme.
- The application SHALL use a `body.dark-mode` selector to override CSS variables for the dark theme.
- The application SHALL replace all hardcoded colors with `var(--*)` variables to support theme switching.
- For first-time users, the UI SHALL default to the dark theme (applied at runtime) unless a saved preference exists.

**JavaScript logic:**
- The application SHALL read `pr_theme_mode` from localStorage on page load and apply the saved theme.
- The application SHALL apply the theme before CSS loads to avoid a flash of the wrong theme.
- The application SHALL toggle the `dark-mode` class on the `body` element when the user toggles the control.
- The application SHALL save the user's preference to localStorage under the key `pr_theme_mode` with values `"light"` or `"dark"`.

**Color palette:**
- The light theme SHALL use the current light color palette for panels and backgrounds.
- The dark theme SHALL use soft grays (shall NOT use pure black `#000000`).
- The UI SHALL maintain WCAG AA contrast standards: >= 4.5:1 for body text and >= 3:1 for interactive UI controls.

## Impact

**Modified files:**
- `calculator/templates/index.html` - Add toggle + inline script
- `calculator/static/css/styles.css` - Add CSS variables + dark overrides  
- `calculator/static/js/app.js` - Add theme initialization + event listener

**No changes to:**
- Ballistics calculations
- Flask server
- Map processing
- Coordinate system
