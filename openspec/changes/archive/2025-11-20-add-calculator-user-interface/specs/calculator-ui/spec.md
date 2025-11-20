# Calculator UI Specification

## ADDED Requirements

### Requirement: Three-Column Desktop Layout

The system SHALL provide three-column layout (Input Panel | Map Visualization | Results Panel) optimized for desktop use (screens >1200px).

#### Scenario: Standard desktop display
- **WHEN** calculator loads on 1920×1080 monitor
- **THEN** layout displays three columns side-by-side
- **AND** input panel is 300px wide (left)
- **AND** map visualization is flexible width (center, fills remaining space)
- **AND** results panel is 300px wide (right)
- **AND** all three columns are same height (100% viewport height minus header)

#### Scenario: Tablet display adaptation
- **WHEN** calculator loads on screen 768-1200px width
- **THEN** layout switches to two columns
- **AND** input and results panels stack vertically (left)
- **AND** map visualization takes right half

#### Scenario: Mobile display adaptation
- **WHEN** calculator loads on screen <768px width
- **THEN** layout switches to single column
- **AND** panels stack: input → map → results (vertical scrolling)

### Requirement: Map Selection Dropdown

The system SHALL provide dropdown menu populated with all available maps from `/processed_maps/` directory, sorted alphabetically.

#### Scenario: Dropdown population
- **WHEN** page loads and /processed_maps/ contains 45 maps
- **THEN** dropdown shows "Select a map..." placeholder
- **AND** dropdown contains 45 options sorted alphabetically (A-Z)
- **AND** map names display with underscores replaced by spaces

#### Scenario: Map selection
- **WHEN** user selects "Muttrah City 2" from dropdown
- **THEN** heightmap and metadata are fetched
- **AND** Leaflet map displays map area
- **AND** grid overlay is drawn
- **AND** loading indicator appears during fetch (disappears when complete)

#### Scenario: Remember last selection
- **WHEN** user selects map and reloads page
- **THEN** last selected map is pre-selected in dropdown (from localStorage)
- **AND** map loads automatically

### Requirement: Coordinate Input with Three Dropdowns

The system SHALL provide three dropdowns per position (Column A-M, Row 1-13, Keypad 1-9) for both mortar and target positions.

#### Scenario: Mortar position dropdowns
- **WHEN** user views input panel
- **THEN** mortar section displays three dropdowns labeled "Column", "Row", "Keypad"
- **AND** Column dropdown contains A through M (13 options)
- **AND** Row dropdown contains 1 through 13 (13 options)
- **AND** Keypad dropdown contains 1 through 9 (9 options)

#### Scenario: Target position dropdowns
- **WHEN** user views input panel
- **THEN** target section displays identical three dropdowns
- **AND** dropdowns are visually distinct from mortar dropdowns (different section, label)

#### Scenario: Default selections
- **WHEN** map is first loaded
- **THEN** mortar dropdowns default to D-6-5
- **AND** target dropdowns default to E-7-5

### Requirement: Interactive Leaflet Map with PR Grid Overlay

The system SHALL display interactive Leaflet map with PR standard 13×13 grid overlay, column labels (A-M), and row labels (1-13).

#### Scenario: Map initialization
- **WHEN** map is selected
- **THEN** Leaflet map initializes centered on map
- **AND** zoom level is set to show entire map
- **AND** pan and zoom controls are enabled

#### Scenario: Grid overlay display
- **WHEN** map loads
- **THEN** 13 vertical lines are drawn (columns A-M)
- **AND** 13 horizontal lines are drawn (rows 1-13)
- **AND** grid lines are thin, semi-transparent gray
- **AND** column labels A-M appear at top of map
- **AND** row labels 1-13 appear on left side of map
- **AND** labels have white text with black outline for visibility

#### Scenario: Grid persists across zoom
- **WHEN** user zooms in or out
- **THEN** grid lines scale proportionally
- **AND** labels remain visible and properly positioned

### Requirement: Draggable Mortar and Target Markers

The system SHALL provide blue mortar marker and red target marker that can be placed by clicking and repositioned by dragging.

#### Scenario: Initial marker placement
- **WHEN** map loads with default coordinates
- **THEN** blue marker appears at mortar position (D-6-5)
- **AND** red marker appears at target position (E-7-5)

#### Scenario: Click-to-place marker
- **WHEN** user clicks map location
- **THEN** nearest marker (mortar or target) moves to clicked position
- **AND** marker snaps to valid map bounds if clicked outside

#### Scenario: Drag marker
- **WHEN** user drags mortar marker to new position
- **THEN** marker follows cursor smoothly
- **AND** on drag end, mortar elevation updates
- **AND** mortar dropdowns update to match new grid reference
- **AND** range circle updates to new mortar position

#### Scenario: Marker tooltips
- **WHEN** user hovers over marker
- **THEN** tooltip displays grid reference (e.g., "D6-7")
- **AND** tooltip displays elevation (e.g., "45m")

### Requirement: Range Circle Overlay (1500m Maximum)

The system SHALL display semi-transparent cyan circle around mortar marker with 1500m radius indicating maximum firing range.

#### Scenario: Range circle display
- **WHEN** mortar marker is placed
- **THEN** cyan circle is drawn centered on mortar
- **AND** circle radius is 1500 meters in map units
- **AND** circle has 30% opacity fill and 2px stroke

#### Scenario: Range circle updates
- **WHEN** mortar marker is dragged
- **THEN** range circle moves with marker in real-time

#### Scenario: Out-of-range visual indicator
- **WHEN** target marker is outside range circle
- **THEN** target marker turns darker red or adds warning icon
- **AND** distance display shows red color

### Requirement: Real-Time Elevation Display

The system SHALL display mortar and target elevations in input panel, updating automatically when positions change.

#### Scenario: Elevation display
- **WHEN** markers are placed at positions
- **THEN** input panel shows "Mortar: 45.0m" below mortar dropdowns
- **AND** input panel shows "Target: 120.5m" below target dropdowns
- **AND** elevations are formatted to 1 decimal place

#### Scenario: Elevation updates on drag
- **WHEN** user drags target marker
- **THEN** target elevation updates in real-time during drag
- **AND** bilinear interpolation samples heightmap at new position

#### Scenario: Elevation updates on dropdown change
- **WHEN** user changes target Row dropdown from 6 to 7
- **THEN** target marker moves on map
- **AND** target elevation updates to new position's height

### Requirement: Calculate Button and Pipeline Execution

The system SHALL provide prominent Calculate button that triggers full calculation pipeline and displays firing solution.

#### Scenario: Calculate button appearance
- **WHEN** user views input panel
- **THEN** Calculate button is large, bright color (e.g., orange or green)
- **AND** button is positioned below input fields

#### Scenario: Button enabled state
- **WHEN** both mortar and target positions are valid
- **THEN** Calculate button is enabled (normal color, clickable)

#### Scenario: Button disabled state
- **WHEN** coordinates are invalid (out of bounds, no map selected)
- **THEN** Calculate button is disabled (grayed out, no pointer cursor)
- **AND** tooltip explains why disabled (e.g., "Select a map first")

#### Scenario: Calculate execution
- **WHEN** user clicks Calculate button
- **THEN** loading indicator appears briefly
- **AND** ballistics engine calculates firing solution
- **AND** results panel updates with new values
- **AND** loading indicator disappears

### Requirement: Results Panel with Mils Primary Display

The system SHALL display firing solution results with elevation in Mils (large, primary) and Degrees (smaller, secondary).

#### Scenario: Results display format
- **WHEN** calculation completes successfully
- **THEN** results panel shows:
  - Distance: "1234 m"
  - Azimuth: "045°"
  - Elevation Delta: "+45 m" (or "-23 m" if target lower)
  - **ELEVATION (PRIMARY):** "1247 mils" (large, bold text, ~24px font)
  - **Elevation (secondary):** "70.2°" (smaller text, ~16px font)
  - Time of Flight: "8.3 s"
  - Range Status: Green "IN RANGE" or Yellow "EXTENDED RANGE" or Red "OUT OF RANGE"

#### Scenario: Range status color coding
- **WHEN** distance is 900m (<1200m)
- **THEN** range status shows green "IN RANGE"

#### Scenario: Extended range warning
- **WHEN** distance is 1350m (1200-1500m)
- **THEN** range status shows yellow "EXTENDED RANGE"

#### Scenario: Out of range error
- **WHEN** distance is 1600m (>1500m)
- **THEN** range status shows red "OUT OF RANGE"

### Requirement: Visual Warning System for Errors

The system SHALL display prominent visual warnings for invalid inputs, out-of-range targets, and extreme elevation differences.

#### Scenario: Out-of-range banner
- **WHEN** calculated distance exceeds 1500m
- **THEN** large red banner appears above results panel
- **AND** banner displays "OUT OF RANGE - Maximum range 1500m"
- **AND** Calculate button remains enabled (allow user to adjust and retry)

#### Scenario: Extreme elevation warning
- **WHEN** elevation difference |ΔZ| exceeds 100m
- **THEN** yellow alert appears in results panel
- **AND** alert displays "⚠ Extreme elevation difference - accuracy may suffer"
- **AND** calculation still completes normally

#### Scenario: Invalid coordinates error
- **WHEN** marker is dragged outside map bounds
- **THEN** red error text appears: "ERROR - Invalid coordinates"
- **AND** Calculate button is disabled

#### Scenario: Impossible shot error
- **WHEN** target is physically unreachable (discriminant < 0)
- **THEN** red banner displays "TARGET UNREACHABLE - Reduce distance or elevation difference"
- **AND** no elevation values are shown in results

### Requirement: Dropdown-to-Marker Bidirectional Sync

The system SHALL synchronize dropdown selections with marker positions bidirectionally in real-time.

#### Scenario: Dropdown change updates marker
- **WHEN** user changes mortar Column dropdown from D to E
- **THEN** mortar marker moves on map to column E
- **AND** marker position updates within 100ms
- **AND** elevation display updates for new position

#### Scenario: Marker drag updates dropdowns
- **WHEN** user drags target marker from E-7-5 to F-8-3
- **THEN** target Column dropdown changes to F
- **AND** target Row dropdown changes to 8
- **AND** target Keypad dropdown changes to 3
- **AND** dropdowns update within 100ms of drag end

#### Scenario: Keypad rounding on drag
- **WHEN** marker is dragged to position between keypad zones
- **THEN** closest keypad number is selected (1-9)
- **AND** marker snaps to center of keypad zone

### Requirement: Application State Management

The system SHALL maintain application state (current map, mortar position, target position, loaded heightmaps) and persist critical state to localStorage.

#### Scenario: State initialization
- **WHEN** page loads
- **THEN** state object is created with default values
- **AND** localStorage is checked for saved map selection
- **AND** saved map is loaded if found

#### Scenario: State updates
- **WHEN** user changes mortar position
- **THEN** state.mortarPosition is updated with {x, y, z, gridRef}
- **AND** state change triggers UI updates (elevation display, range circle)

#### Scenario: State persistence
- **WHEN** user selects map
- **THEN** map name is saved to localStorage
- **AND** on page reload, map is auto-selected

### Requirement: Offline Operation Compliance

The system SHALL function completely offline with no external network requests (except to localhost Flask server).

#### Scenario: Network disconnected operation
- **WHEN** user disconnects from internet
- **THEN** all calculator functionality works identically
- **AND** Leaflet.js loads from local `/calculator/static/lib/` directory
- **AND** no console errors about failed network requests

#### Scenario: No CDN dependencies
- **WHEN** browser Network tab is inspected during calculator use
- **THEN** all requests are to localhost (http://localhost:8080)
- **AND** no requests to external domains (cdn.jsdelivr.net, unpkg.com, etc.)

### Requirement: Performance Target Compliance

The system SHALL respond to user interactions within 100ms and complete calculations within 50ms for responsive gameplay integration.

#### Scenario: Marker drag responsiveness
- **WHEN** user drags marker rapidly
- **THEN** marker follows cursor smoothly (60fps)
- **AND** elevation updates within 100ms of drag end

#### Scenario: Calculation speed
- **WHEN** user clicks Calculate button
- **THEN** results appear within 50ms
- **AND** no visible lag or delay

#### Scenario: Map load time
- **WHEN** user selects new map
- **THEN** map loads and displays within 500ms
- **AND** heightmap JSON parses without blocking UI

### Requirement: Accessibility and Usability

The system SHALL provide keyboard navigation, ARIA labels, and sufficient color contrast for basic accessibility (WCAG AA level).

#### Scenario: Keyboard navigation
- **WHEN** user presses Tab key
- **THEN** focus moves logically through inputs: map dropdown → mortar dropdowns → target dropdowns → Calculate button

#### Scenario: Enter key shortcut
- **WHEN** user presses Enter key while focused on input
- **THEN** Calculate button is triggered (same as clicking button)

#### Scenario: Color contrast
- **WHEN** results are displayed
- **THEN** all text has minimum 4.5:1 contrast ratio against background
- **AND** color-blind users can distinguish markers by shape/label (not color alone)

### Requirement: Browser Compatibility

The system SHALL function on modern browsers (Chrome 90+, Firefox 88+, Edge 90+) without polyfills.

#### Scenario: ES6 module support
- **WHEN** calculator loads in Chrome 90+
- **THEN** ES6 modules (import/export) work correctly
- **AND** arrow functions, const/let, template literals work

#### Scenario: Leaflet.js compatibility
- **WHEN** calculator loads in Firefox 88+
- **THEN** Leaflet map renders correctly
- **AND** markers, overlays, and interactions work identically to Chrome

#### Scenario: Cross-browser testing
- **WHEN** calculator is tested on Edge 90+
- **THEN** all functionality works without browser-specific code
- **AND** no console errors related to unsupported features
