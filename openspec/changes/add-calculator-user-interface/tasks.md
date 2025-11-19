# Implementation Tasks: Calculator User Interface

## 1. HTML Structure and Layout

- [ ] 1.1 Create `calculator/templates/index.html` with DOCTYPE and meta tags
- [ ] 1.2 Implement three-column layout structure (inputs | map | results)
- [ ] 1.3 Add header with application title "PROJECT REALITY MORTAR CALCULATOR"
- [ ] 1.4 Create map selector dropdown container
- [ ] 1.5 Create input panel with mortar and target coordinate sections
- [ ] 1.6 Create map visualization container (full height, Leaflet map)
- [ ] 1.7 Create results panel with labeled fields
- [ ] 1.8 Add Calculate button (prominent styling)
- [ ] 1.9 Add footer with version and attribution
- [ ] 1.10 Link CSS and JavaScript modules with correct paths
- [ ] 1.11 Test HTML validates with W3C validator

## 2. Map Selection Interface

- [ ] 2.1 Implement dropdown population from `/processed_maps/` directory listing
- [ ] 2.2 Fetch list of available maps via JavaScript (read directory or manifest)
- [ ] 2.3 Sort map names alphabetically
- [ ] 2.4 Display map names in user-friendly format (replace underscores with spaces)
- [ ] 2.5 Add "Select a map..." placeholder option
- [ ] 2.6 Trigger map load on selection change
- [ ] 2.7 Display loading indicator during map load
- [ ] 2.8 Remember last selected map in localStorage (persist across sessions)

## 3. Coordinate Input Dropdowns

- [ ] 3.1 Create 3 dropdowns for mortar position (Column, Row, Keypad)
- [ ] 3.2 Create 3 dropdowns for target position (Column, Row, Keypad)
- [ ] 3.3 Populate Column dropdown with A through M (13 options)
- [ ] 3.4 Populate Row dropdown with 1 through 13 (13 options)
- [ ] 3.5 Populate Keypad dropdown with 1 through 9 (9 options)
- [ ] 3.6 Set default selections (mortar: D-6-5, target: E-7-5)
- [ ] 3.7 Add change event listeners to sync with map markers
- [ ] 3.8 Validate selections and disable Calculate if invalid
- [ ] 3.9 Style dropdowns consistently (match theme colors)

## 4. Leaflet Map Integration

- [ ] 4.1 Initialize Leaflet map in designated container
- [ ] 4.2 Set initial view to map center with appropriate zoom level
- [ ] 4.3 Disable default Leaflet attribution (offline operation)
- [ ] 4.4 Configure zoom controls (min: 0, max: 5, initial: 2)
- [ ] 4.5 Enable pan controls (click-drag)
- [ ] 4.6 Add custom tile layer for PR maps (if using tiles) OR use ImageOverlay
- [ ] 4.7 Set map bounds to prevent panning outside map area
- [ ] 4.8 Test map loads correctly with processed heightmap data

## 5. PR Grid Overlay

- [ ] 5.1 Calculate grid line positions based on map_size and grid_scale (13×13)
- [ ] 5.2 Draw vertical grid lines (columns A-M) using Leaflet polylines
- [ ] 5.3 Draw horizontal grid lines (rows 1-13)
- [ ] 5.4 Add column labels (A-M) at top of map
- [ ] 5.5 Add row labels (1-13) on left side of map
- [ ] 5.6 Style grid lines (thin, semi-transparent gray)
- [ ] 5.7 Style labels (white text with black outline for visibility)
- [ ] 5.8 Ensure grid persists across zoom levels
- [ ] 5.9 Test grid alignment with coordinate conversions

## 6. Marker Placement and Dragging

- [ ] 6.1 Create custom blue marker icon for mortar position
- [ ] 6.2 Create custom red marker icon for target position
- [ ] 6.3 Implement click-to-place mortar marker functionality
- [ ] 6.4 Implement click-to-place target marker functionality
- [ ] 6.5 Enable marker dragging (Leaflet draggable option)
- [ ] 6.6 Add dragend event handlers to update coordinates and elevation
- [ ] 6.7 Display marker tooltips with grid reference and elevation
- [ ] 6.8 Snap markers to valid map positions (within bounds)
- [ ] 6.9 Test marker placement accuracy matches coordinate conversions

## 7. Range Circle Overlay

- [ ] 7.1 Draw semi-transparent circle around mortar marker (radius = 1500m)
- [ ] 7.2 Style circle (cyan color, 30% opacity fill, 2px stroke)
- [ ] 7.3 Update circle position when mortar marker moves
- [ ] 7.4 Highlight target marker red if outside circle (out of range)
- [ ] 7.5 Test circle renders correctly at all zoom levels

## 8. Real-Time Elevation Display

- [ ] 8.1 Display mortar elevation in input panel (e.g., "Mortar: 45m")
- [ ] 8.2 Display target elevation in input panel (e.g., "Target: 120m")
- [ ] 8.3 Update elevations when markers are dragged
- [ ] 8.4 Update elevations when dropdown selections change
- [ ] 8.5 Format elevation with 1 decimal place
- [ ] 8.6 Show loading indicator during heightmap sampling
- [ ] 8.7 Handle missing elevation data gracefully (display "--" or error)

## 9. Calculate Button and Pipeline

- [ ] 9.1 Style Calculate button prominently (large, bright color)
- [ ] 9.2 Add click event handler to trigger calculation pipeline
- [ ] 9.3 Disable button if inputs are invalid (gray out)
- [ ] 9.4 Show loading state during calculation (spinner or "Calculating...")
- [ ] 9.5 Pipeline step 1: Get mortar XY from dropdowns or marker
- [ ] 9.6 Pipeline step 2: Get target XY from dropdowns or marker
- [ ] 9.7 Pipeline step 3: Sample elevations from heightmap
- [ ] 9.8 Pipeline step 4: Call ballistics engine with positions
- [ ] 9.9 Pipeline step 5: Display results in results panel
- [ ] 9.10 Handle calculation errors and display error messages

## 10. Results Panel Display

- [ ] 10.1 Display horizontal distance in meters (e.g., "1234 m")
- [ ] 10.2 Display azimuth in degrees (e.g., "045°")
- [ ] 10.3 Display elevation delta with +/- sign (e.g., "+45 m" or "-23 m")
- [ ] 10.4 Display elevation in Mils (PRIMARY: large, bold, e.g., "1247 mils")
- [ ] 10.5 Display elevation in Degrees (SECONDARY: smaller, e.g., "70.2°")
- [ ] 10.6 Display time of flight in seconds (e.g., "8.3 s")
- [ ] 10.7 Color-code range status: Green (<1200m), Yellow (1200-1500m), Red (>1500m)
- [ ] 10.8 Clear previous results when Calculate is clicked
- [ ] 10.9 Animate result display (fade in or slide in)
- [ ] 10.10 Format all numbers with appropriate precision

## 11. Visual Warning System

- [ ] 11.1 Implement red banner component for critical errors
- [ ] 11.2 Display "OUT OF RANGE" banner when distance > 1500m
- [ ] 11.3 Display "TARGET UNREACHABLE" banner when shot is physically impossible
- [ ] 11.4 Implement yellow alert component for warnings
- [ ] 11.5 Display "Extreme elevation difference" warning when |ΔZ| > 100m
- [ ] 11.6 Display "Invalid coordinates" error for out-of-bounds positions
- [ ] 11.7 Auto-dismiss warnings after 5 seconds (optional)
- [ ] 11.8 Style warnings to be highly visible but not obtrusive

## 12. Dropdown-to-Marker Synchronization

- [ ] 12.1 When dropdown changes, convert grid ref to XY coordinates
- [ ] 12.2 Move corresponding marker to new XY position on map
- [ ] 12.3 Update elevation display for new position
- [ ] 12.4 When marker is dragged, convert XY to grid reference
- [ ] 12.5 Update dropdown selections to match marker position
- [ ] 12.6 Handle edge cases (marker on grid boundary, keypad rounding)
- [ ] 12.7 Debounce rapid marker movements to avoid excessive updates

## 13. Application State Management (app.js)

- [ ] 13.1 Create state object holding current mortar and target positions
- [ ] 13.2 Create state object holding loaded heightmap and metadata
- [ ] 13.3 Implement state update functions (setMortarPosition, setTargetPosition)
- [ ] 13.4 Implement state getter functions
- [ ] 13.5 Add state change listeners to trigger UI updates
- [ ] 13.6 Persist state to localStorage on changes (optional)
- [ ] 13.7 Restore state from localStorage on page load (optional)

## 14. Event Handler Implementation (ui.js)

- [ ] 14.1 Implement onMapSelectionChange() - Load map and heightmap
- [ ] 14.2 Implement onDropdownChange() - Update marker position
- [ ] 14.3 Implement onMarkerDrag() - Update dropdown selections
- [ ] 14.4 Implement onMapClick() - Place or move marker
- [ ] 14.5 Implement onCalculateClick() - Run calculation pipeline
- [ ] 14.6 Implement onMapLoad() - Initialize grid and markers
- [ ] 14.7 Add error event handlers for all async operations
- [ ] 14.8 Test all event handlers with various user interactions

## 15. CSS Styling (style.css)

- [ ] 15.1 Implement three-column layout using Flexbox or Grid
- [ ] 15.2 Style input panel (left column, 300px width)
- [ ] 15.3 Style map visualization (center column, flexible width)
- [ ] 15.4 Style results panel (right column, 300px width)
- [ ] 15.5 Apply BEM naming convention consistently
- [ ] 15.6 Implement color scheme (blue, red, green, yellow, cyan as per spec)
- [ ] 15.7 Style dropdowns and buttons (consistent theme)
- [ ] 15.8 Style elevation displays and labels
- [ ] 15.9 Style results with appropriate font sizes and weights
- [ ] 15.10 Add hover states for interactive elements
- [ ] 15.11 Ensure sufficient color contrast for accessibility

## 16. Responsive Design (Mobile Adaptation)

- [ ] 16.1 Implement media query for screens < 768px (tablet)
- [ ] 16.2 Switch to two-column layout (inputs+results stacked, map full-width)
- [ ] 16.3 Implement media query for screens < 480px (mobile)
- [ ] 16.4 Switch to single-column layout (all panels stacked)
- [ ] 16.5 Make dropdowns and buttons touch-friendly (larger tap targets)
- [ ] 16.6 Test on various screen sizes (desktop, tablet, phone)
- [ ] 16.7 Note: Full mobile support deferred to V2, V1 basic fallback only

## 17. Error Handling and User Feedback

- [ ] 17.1 Display loading spinner during heightmap fetch
- [ ] 17.2 Display error message if map fails to load
- [ ] 17.3 Display error message if heightmap is missing or corrupted
- [ ] 17.4 Disable Calculate button if positions are invalid
- [ ] 17.5 Show tooltip explaining why button is disabled
- [ ] 17.6 Display calculation errors in results panel (replace results)
- [ ] 17.7 Log all errors to browser console for debugging
- [ ] 17.8 Test error scenarios: missing map, invalid coordinates, network failures

## 18. Performance Optimization

- [ ] 18.1 Debounce marker drag events (update every 100ms, not every pixel)
- [ ] 18.2 Throttle elevation sampling during rapid movements
- [ ] 18.3 Lazy load map tiles or images (if using tile-based approach)
- [ ] 18.4 Minimize DOM manipulations (batch updates)
- [ ] 18.5 Profile with Chrome DevTools Performance tab
- [ ] 18.6 Test with largest maps (4km, 2049×2049 heightmaps)
- [ ] 18.7 Ensure UI remains responsive during all operations (<100ms updates)

## 19. Integration Testing

- [ ] 19.1 Test full workflow: Select map → Place mortar → Place target → Calculate
- [ ] 19.2 Test dropdown-to-marker sync in both directions
- [ ] 19.3 Test with Korengal Valley (extreme elevation)
- [ ] 19.4 Test with Vadso City (long range)
- [ ] 19.5 Test with Burning Sands (flat terrain)
- [ ] 19.6 Test edge cases: max range, map boundaries, zero distance
- [ ] 19.7 Test error handling: missing maps, invalid inputs, out of range
- [ ] 19.8 Compare calculator results with in-game measurements

## 20. In-Game Validation

- [ ] 20.1 Launch PR:BF2 local server with test map (Korengal Valley)
- [ ] 20.2 Place mortar and target at known grid coordinates
- [ ] 20.3 Input same coordinates in calculator
- [ ] 20.4 Use calculated firing solution in-game
- [ ] 20.5 Measure impact distance from target (must be <50m)
- [ ] 20.6 Record test data (coords, calculated values, observed impact)
- [ ] 20.7 Repeat for Vadso City and Burning Sands
- [ ] 20.8 Adjust calculations if systematic error detected

## 21. Documentation and Comments

- [ ] 21.1 Add JSDoc comments to all UI functions
- [ ] 21.2 Add inline comments explaining complex UI logic
- [ ] 21.3 Document event flow and state management
- [ ] 21.4 Create user guide section in README.md
- [ ] 21.5 Add screenshots of calculator interface
- [ ] 21.6 Document keyboard shortcuts (if any)
- [ ] 21.7 Add troubleshooting section for common UI issues

## 22. Accessibility Considerations

- [ ] 22.1 Add ARIA labels to all interactive elements
- [ ] 22.2 Ensure tab navigation works logically
- [ ] 22.3 Add keyboard shortcuts for Calculate (Enter key)
- [ ] 22.4 Ensure sufficient color contrast (WCAG AA minimum)
- [ ] 22.5 Test with screen reader (basic compatibility)
- [ ] 22.6 Add focus indicators for keyboard navigation
- [ ] 22.7 Note: Full accessibility deferred to V2, V1 basic compliance only

## 23. Browser Compatibility Testing

- [ ] 23.1 Test on Chrome 90+ (primary browser)
- [ ] 23.2 Test on Firefox 88+ (secondary browser)
- [ ] 23.3 Test on Edge 90+ (secondary browser)
- [ ] 23.4 Verify ES6 features work (arrow functions, const/let, modules)
- [ ] 23.5 Verify Leaflet.js works on all browsers
- [ ] 23.6 Test offline operation on all browsers
- [ ] 23.7 Fix any browser-specific issues
