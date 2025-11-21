# Implementation Tasks

## 1. Add CSS Theme Variables

- [x] Open `calculator/static/css/styles.css`
- [x] Insert CSS variables block after line 19 (after `body {...}` closes)
- [x] Add `:root` selector with light theme variables (backgrounds, text, borders, buttons, status, map)
- [x] Add `body.dark-mode` selector with dark theme overrides
- [x] Use soft grays (#1a1a1a) not pure black (#000000) for dark backgrounds
- [x] Verify all 44 CSS variables defined (11 in :root + 11 overrides in each section)

## 2. Replace Hardcoded Colors in CSS

- [x] Replace `color: #333;` with `color: var(--text-primary);`
- [x] Replace `background-color: #f5f5f5;` with `background-color: var(--bg-body);`
- [x] Replace `background-color: white;` with `background-color: var(--bg-panel);`
- [x] Replace `background-color: #ffffff;` with `background-color: var(--bg-panel);`
- [x] Replace `background-color: #2c3e50;` with `background-color: var(--bg-header);`
- [x] Replace header `color: white;` with `color: var(--text-light);`
- [x] Replace `color: #2c3e50;` with `color: var(--text-header);`
- [x] Replace `color: #34495e;` with `color: var(--text-header);`
- [x] Replace `color: #555;` with `color: var(--text-secondary);`
- [x] Replace `color: #666;` with `color: var(--text-secondary);`
- [x] Replace `border: 1px solid #ddd;` with `border: 1px solid var(--border-color);`
- [x] Replace `border: 1px solid #ccc;` with `border: 1px solid var(--border-color);`
- [x] Replace `border-right: 1px solid #ddd;` with `border-right: 1px solid var(--border-color);`
- [x] Replace `border-left: 1px solid #ddd;` with `border-left: 1px solid var(--border-color);`
- [x] Replace `border-bottom: 2px solid #3498db;` with `border-bottom: 2px solid var(--border-focus);`
- [x] Replace `border-left: 3px solid #3498db;` with `border-left: 3px solid var(--border-focus);`
- [x] Replace `border-color: #3498db;` with `border-color: var(--border-focus);`
- [x] Replace `background-color: #3498db;` with `background-color: var(--btn-primary);`
- [x] Replace `background-color: #2980b9;` with `background-color: var(--btn-primary-hover);`
- [x] Replace `background-color: #27ae60;` with `background-color: var(--btn-calculate);`
- [x] Replace `background-color: #229954;` with `background-color: var(--btn-calculate-hover);`
- [x] Replace `background-color: #f8f9fa;` with `background-color: var(--bg-info);`
- [x] Replace ready status `background-color: #d4edda;` with `background-color: var(--status-ready-bg);`
- [x] Replace ready status `color: #155724;` with `color: var(--status-ready-text);`
- [x] Replace ready status `border: 1px solid #c3e6cb;` with `border: 1px solid var(--status-ready-border);`
- [x] Replace warning status `background-color: #fff3cd;` with `background-color: var(--status-warning-bg);`
- [x] Replace warning status `color: #856404;` with `color: var(--status-warning-text);`
- [x] Replace warning status `border: 1px solid #ffeaa7;` with `border: 1px solid var(--status-warning-border);`
- [x] Replace error status `background-color: #f8d7da;` with `background-color: var(--status-error-bg);`
- [x] Replace error status `color: #721c24;` with `color: var(--status-error-text);`
- [x] Replace error status `border: 1px solid #f5c6cb;` with `border: 1px solid var(--status-error-border);`
- [x] Replace map `background-color: #e0e0e0;` with `background-color: var(--map-bg);`
- [x] Replace grid label `background: rgba(0, 0, 0, 0.6);` with `background: var(--grid-label-bg);`
- [x] Replace grid label `color: #fff;` with `color: var(--grid-label-text);`
- [x] Verify no hardcoded hex colors remain except in variable definitions and gradient

## 3. Add Dark Mode Toggle to Header

- [x] Open `calculator/templates/index.html`
- [x] Locate line 42 (after map size override `</div>`)
- [x] Insert dark mode toggle HTML with checkbox input and label
- [x] Set checkbox id to `dark-mode-toggle`
- [x] Add inline styles for flexbox layout and spacing
- [x] Verify toggle appears in header visually

## 4. Add Inline Theme Initialization Script

- [x] Open `calculator/templates/index.html`
- [x] Locate line 234 (BEFORE Leaflet script tag)
- [x] Insert inline script tag with IIFE (Immediately Invoked Function Expression)
- [x] Read `pr_theme_mode` from localStorage
- [x] Apply `dark-mode` class to body if saved theme is dark
- [x] Add DOMContentLoaded listener to update checkbox state
- [x] Wrap in try-catch to handle localStorage errors
- [x] Verify script executes before page renders (no flash)

## 5. Add Theme Toggle Event Listener

- [x] Open `calculator/static/js/app.js`
- [x] Locate `setupEventListeners()` function (around line 804)
- [x] Find grid labels toggle event listener (around line 845)
- [x] Insert dark mode toggle event listener after grid labels toggle
- [x] Call `toggleTheme(e.target.checked)` on change event
- [x] Verify event listener attached to checkbox with id `dark-mode-toggle`

## 6. Add Theme Toggle Function

- [x] Open `calculator/static/js/app.js`
- [x] Locate line 895 (before `window.prCalc` export block)
- [x] Add JSDoc comment with param description
- [x] Create `toggleTheme(enableDark)` function
- [x] Add or remove `dark-mode` class from body based on enableDark
- [x] Save preference to localStorage as `pr_theme_mode` with value "dark" or "light"
- [x] Log theme change to console
- [x] Wrap localStorage operations in try-catch block
- [x] Add error logging for localStorage failures

## 7. Test Theme Functionality

- [x] Start Flask server using `run.bat` or `python calculator/server.py`
- [x] Open browser and navigate to `http://localhost:5000`
- [x] Click toggle and verify theme switches instantly without page reload
- [x] Reload page (F5) and verify theme persists
- [x] Close and reopen browser and verify theme persists
- [x] Verify no flash of wrong theme on initial page load
- [x] Verify first-time user (no saved preference) defaults to dark theme
- [x] Press Tab key to focus toggle and Space key to activate
- [x] Test in Chrome or Edge on Windows
- [x] Test in Firefox on Windows
- [x] Check DevTools console for errors (should be none)
- [x] Test with localStorage disabled (theme works but doesn't persist)

## 8. Verify Visual Appearance

- [x] Verify all text readable in light theme
- [x] Verify all text readable in dark theme
- [x] Verify buttons visible and properly styled in light theme
- [x] Verify buttons visible and properly styled in dark theme
- [x] Verify dropdown menus styled correctly in both themes
- [x] Verify ready status messages distinguishable in both themes
- [x] Verify warning status messages distinguishable in both themes
- [x] Verify error status messages distinguishable in both themes
- [x] Verify map grid lines visible in both themes
- [x] Verify blue mortar marker visible in both themes
- [x] Verify red target marker visible in both themes
- [x] Verify range circle visible in both themes
- [x] Verify no visual regressions in light mode (original appearance preserved)

## 9. Verify WCAG Contrast Ratios

- [x] Open WebAIM contrast checker (https://webaim.org/resources/contrastchecker/)
- [x] Test light theme body text (#333 on #ffffff) - expect ≥ 4.5:1
- [x] Test light theme secondary text (#666 on #ffffff) - expect ≥ 4.5:1
- [x] Test light theme button text (#fff on #3498db) - expect ≥ 4.5:1
- [x] Test dark theme body text (#e0e0e0 on #2d2d2d) - expect ≥ 4.5:1
- [x] Test dark theme secondary text (#b0b0b0 on #2d2d2d) - expect ≥ 4.5:1
- [x] Test dark theme button text (#fff on #4a9eff) - expect ≥ 4.5:1
- [x] Test all six status message types in light theme
- [x] Test all six status message types in dark theme
- [x] Verify all tests pass WCAG AA requirements

## 10. Code Quality Check

- [x] Verify 2-space indentation used in all modified files
- [x] Verify JSDoc comment added to `toggleTheme()` function
- [x] Verify BEM naming convention followed for CSS classes
- [x] Verify try-catch blocks used for localStorage operations
- [x] Verify console.log statements added for theme changes
- [x] Verify CSS comments explain theme variable structure
- [x] Verify no commented-out code left in files
- [x] Verify all files saved and no unsaved changes remain
