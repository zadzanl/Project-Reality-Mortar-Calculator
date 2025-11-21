# Add Dark Mode Toggle

## Why

Players use the calculator during night gameplay sessions. Current light-only interface causes eye strain in low-light conditions. Add dark mode toggle to reduce eye fatigue.

## What Changes

**Add to header (after map size override):**
- Checkbox-based toggle with "Dark Mode" label
- Styled for consistency with existing controls

**CSS architecture:**
- Define CSS variables in `:root` for light theme (base)
- UI default: favor dark theme for first-time users (applied at runtime)
- Override variables in `body.dark-mode` selector for dark theme
- Replace ALL hardcoded colors with CSS variables

**JavaScript logic:**
- Read `pr_theme_mode` from localStorage on page load
- Apply theme before CSS loads (prevent flash)
- Toggle `.dark-mode` class on body element
- Save preference to localStorage

**Color palette:**
- Light theme: Current colors (white panels, gray background)
- Dark theme: Soft grays (avoid pure black #000000)
- Maintain WCAG AA contrast (4.5:1 for text, 3:1 for UI components)

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
