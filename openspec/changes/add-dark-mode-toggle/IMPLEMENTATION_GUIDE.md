# Dark Mode Implementation Guide for AI Agents

## Overview

This change adds a dark mode toggle to the Project Reality Mortar Calculator. Users can switch between light and dark themes, with preference saved across sessions.

---

## Quick Reference

**Changed files:**
- `calculator/static/css/styles.css` - Add CSS variables + replace colors
- `calculator/templates/index.html` - Add toggle + inline script  
- `calculator/static/js/app.js` - Add event listener + toggle function

**Unchanged files:**
- All ballistics, coordinates, heightmap modules
- Flask server (`server.py`)
- Map processing scripts
- Test files

**Estimated time:** 2-3 hours  
**Complexity:** Low-Medium

---

## Implementation Strategy

### Step 1: CSS Variables (Foundation)
Add theme variables at top of `styles.css`. This creates a single source of truth for all colors.

**Why first:** All subsequent color replacements depend on these variables existing.

### Step 2: Replace Hardcoded Colors
Use find/replace to swap ~40 hardcoded color values with variable references.

**Why second:** Must happen after variables defined, before testing begins.

### Step 3: HTML Toggle Control
Add checkbox to header. This is the user-facing control element.

**Why third:** Non-functional until JavaScript wired up, but harmless to add early.

### Step 4: Inline Theme Script
Add script to prevent flash-of-wrong-theme. Runs before CSS loads.

**Why fourth:** Critical for UX, but depends on CSS variables existing.

### Step 5: JavaScript Event Handler
Wire up toggle control to theme switching logic.

**Why fifth:** Final piece that makes feature interactive.

### Step 6: Testing
Verify functionality, persistence, accessibility, and visual correctness.

**Why last:** Tests the complete integrated feature.

---

## Key Technical Decisions

### 1. CSS Variables Over Class-Based Themes
**Choice:** Use CSS custom properties  
**Reason:** Single source of truth, easier to maintain, better performance

### 2. Inline Script for Flash Prevention
**Choice:** `<script>` tag in HTML (not external JS)  
**Reason:** Must execute before CSS loads, external file adds latency

### 3. localStorage for Persistence
**Choice:** localStorage (not cookies or sessionStorage)  
**Reason:** Simple, persistent, no server needed, 5MB storage sufficient

### 4. Checkbox Over Icon Button
**Choice:** Native `<input type="checkbox">`  
**Reason:** Built-in keyboard accessibility, screen reader support, simple styling

### 5. Soft Grays Over Pure Black
**Choice:** `#1a1a1a` instead of `#000000`  
**Reason:** Reduces eye strain, prevents halation effect, better WCAG compliance

---

## Color Palette Rationale

### Light Theme (Unchanged)
Current colors retained for consistency. Users familiar with existing interface.

### Dark Theme (New)
**Backgrounds:**
- Body: `#1a1a1a` - Soft black, not pure black
- Panels: `#2d2d2d` - Slightly lighter than body for depth
- Inputs: `#3a3a3a` - Darker than panels, clear affordance

**Text:**
- Primary: `#e0e0e0` - High contrast (11.5:1 on `#2d2d2d`)
- Secondary: `#b0b0b0` - Medium contrast (6.8:1), meets WCAG AA

**Buttons:**
- Primary: `#4a9eff` - Brighter than light theme blue
- Calculate: `#2ecc71` - Vibrant green, high visibility

**Status Messages:**
- Inverted from light theme (dark backgrounds, bright text)
- Maintains color semantics (green=success, yellow=warning, red=error)

---

## Accessibility Checklist

✓ **Contrast ratios:** All text ≥ 4.5:1, UI components ≥ 3:1  
✓ **Keyboard navigation:** Tab to focus, Space to toggle  
✓ **Screen readers:** Checkbox has label, state announced correctly  
✓ **Focus indicators:** Visible in both themes  
✓ **No pure black:** Avoids halation effect  
✓ **Graceful degradation:** Works without localStorage

---

## Testing Scenarios

### Functional Tests
1. Toggle switches themes instantly
2. Theme persists after F5 reload
3. Theme persists after browser close/reopen
4. Works in Chrome, Edge, Firefox
5. Works in private/incognito mode (no persistence)

### Visual Tests
6. All text readable in both themes
7. Buttons clearly visible in both themes
8. Status messages distinguishable in both themes
9. Map grid lines visible in both themes
10. Markers (blue/red) visible in both themes
11. No regressions in light mode

### Edge Cases
12. localStorage disabled: Toggle works, doesn't persist
13. First-time user: Defaults to dark theme
14. Rapid toggle clicks: No visual glitches
15. Page refresh during toggle: Correct theme loads

---

## Common Pitfalls for AI Agents

### ❌ Don't Do This

**1. Using pure black (#000000):**
```css
body.dark-mode {
  --bg-body: #000000; /* ❌ Too harsh */
}
```

**2. Forgetting try-catch for localStorage:**
```javascript
function toggleTheme(enableDark) {
  localStorage.setItem('pr_theme_mode', 'dark'); // ❌ Will throw in private mode
}
```

**3. Loading theme in external JS:**
```html
<script src="/static/js/theme.js"></script> <!-- ❌ Causes flash -->
```

**4. Hardcoding colors in inline styles:**
```html
<div style="color: #333;"> <!-- ❌ Won't change with theme -->
```

### ✓ Do This Instead

**1. Use soft grays:**
```css
body.dark-mode {
  --bg-body: #1a1a1a; /* ✓ Reduces eye strain */
}
```

**2. Wrap in try-catch:**
```javascript
function toggleTheme(enableDark) {
  try {
    localStorage.setItem('pr_theme_mode', 'dark'); // ✓ Safe
  } catch (e) {
    console.error('localStorage unavailable:', e);
  }
}
```

**3. Use inline script:**
```html
<script>
  (function() {
    const theme = localStorage.getItem('pr_theme_mode');
    if (theme === 'dark') document.body.classList.add('dark-mode');
  })();
</script> <!-- ✓ No flash -->
```

**4. Use CSS variables:**
```html
<div style="color: var(--text-primary);"> <!-- ✓ Theme-aware -->
```

---

## Verification Steps

After implementation, confirm:

1. **CSS variables defined:** Check `:root` and `body.dark-mode` blocks exist
2. **No hardcoded colors:** Search CSS for `#` hex values (should only be in variable definitions)
3. **Toggle in header:** Visually confirm checkbox appears after map size dropdown
4. **Inline script present:** Check HTML source for theme initialization script
5. **Event listener wired:** Check DevTools > Event Listeners on checkbox
6. **Console logs:** Should see `"Theme: dark"` or `"Theme: light"` when toggling
7. **localStorage key:** Check DevTools > Application > Local Storage for `pr_theme_mode`

---

## Rollback Plan

If implementation breaks:

1. Remove CSS variable definitions (revert to hardcoded colors)
2. Remove HTML toggle control
3. Remove inline theme script
4. Remove JavaScript event listener and function

Feature is additive - removing it restores original functionality completely.

---

## Future Enhancements (Not in This PR)

- Auto-detect system preference (`prefers-color-scheme` media query)
- Sun/moon icon instead of checkbox
- Smooth color transitions (CSS `transition`)
- Custom theme editor (user-defined colors)
- High contrast mode for accessibility

These are explicitly OUT OF SCOPE for this implementation.

---

## Questions for Human Review

If unclear, ask the user:

1. **Toggle placement:** Confirm location in header is acceptable?
2. **Dark theme colors:** Approve the proposed color palette?
3. **localStorage key:** Use `pr_theme_mode` or different name?
4. **Default theme:** Light theme for first-time users, correct?
5. **Browser support:** Chrome/Edge/Firefox sufficient, or need Safari/mobile?

---

## Success Criteria

Implementation is complete when ALL of these are true:

✓ Toggle appears in header  
✓ Clicking toggle switches themes instantly  
✓ Theme persists across page reloads  
✓ Theme persists across browser restarts  
✓ No flash of wrong theme on page load  
✓ All text readable in both themes (WCAG AA)  
✓ Keyboard accessible (Tab + Space)  
✓ Works in Chrome, Edge, Firefox  
✓ No console errors  
✓ No visual regressions in light mode  

---

## Support Resources

**WCAG Contrast Checker:** https://webaim.org/resources/contrastchecker/  
**Dark Mode Best Practices:** https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/  
**CSS Variables Guide:** https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties  
**localStorage API:** https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage  

---

**Last updated:** 2025-11-21  
**Author:** AI Agent Coordinator  
**Reviewer:** Awaiting human review
