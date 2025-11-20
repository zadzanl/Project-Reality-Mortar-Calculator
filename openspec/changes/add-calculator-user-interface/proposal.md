# Proposal: Calculator User Interface

## Why

The mortar calculator needs a web page where users can:
1. Select maps
2. Place mortar and target positions (click map or use dropdowns)
3. See the map with grid lines and range circles
4. View calculated firing solutions

The interface must:
- Connect to the ballistics engine (the math code)
- Use the height data (heightmaps)
- Show updates immediately when you move markers

Right now, we have no user interface.

## What Changes

- **Main HTML Template** (`calculator/templates/index.html`):
  - Three-column layout: Inputs | Map | Results
  - Map selector dropdown (shows all available maps)
  - Coordinate inputs: 3 dropdowns per position (Column A-M, Row 1-13, Keypad 1-9)
  - Calculate button (click to run calculations)
  - Works on phones (switches to single column)

- **Map Visualization Component** (`ui.js` + Leaflet.js):
  - Interactive map showing selected PR map with minimap base layer
  - Minimap PNG displayed as background (satellite/overview imagery)
  - PR grid overlay (13×13 grid with labels: A-M columns, 1-13 rows) overlaid on minimap
  - Draggable markers: Blue (mortar), Red (target)
  - Click map to place markers
  - Range circle showing 1500m maximum distance
  - Zoom and pan controls
  - Shows elevation (height) as you move markers
  - Graceful fallback if minimap.png unavailable (grid-only mode with warning)

- **Input Panel** (`calculator/templates/index.html` + `ui.js`):
  - Map selection dropdown with map names
  - Mortar position inputs:
    - Dropdown 1: Column (A through M)
    - Dropdown 2: Row (1 through 13)
    - Dropdown 3: Keypad (1-9)
  - Target position inputs (identical 3-dropdown structure)
  - Auto-sync between dropdown inputs and map marker positions
  - Elevation displays (auto-populated from heightmap)
  - Calculate button (prominent, calls ballistics engine)

- **Results Display Panel** (`calculator/templates/index.html` + `ui.js`):
  - Distance to target (meters)
  - Azimuth (compass degrees, 0-360°)
  - Elevation delta (height difference in meters, +/- prefix)
  - **PRIMARY DISPLAY:** Elevation in Mils (large, bold text)
  - **SECONDARY DISPLAY:** Elevation in Degrees (smaller text)
  - Time of flight (seconds, 1 decimal place)
  - Range status indicator (green/yellow/red)
  - Visual warnings for out-of-range or invalid inputs

- **Visual Warning System**:
  - Red banner: "OUT OF RANGE - Maximum range 1500m" (distance > 1500m)
  - Yellow alert: "Extreme elevation difference - accuracy may suffer" (|ΔZ| > 100m)
  - Red text: "ERROR - Invalid coordinates" (out of bounds, validation failure)

- **Application Orchestration** (`app.js`):
  - Load calculation modules (ballistics.js, coordinates.js, heightmap.js)
  - Handle user actions (dropdown changes, map clicks, marker drags)
  - Track current mortar and target positions
  - Run calculations in correct order
  - Handle errors and show messages to user

- **Styling** (`calculator/static/css/style.css`):
  - BEM naming (organized CSS class names)
  - Colors: Blue (mortar), Red (target), Green (good), Yellow (warning), Cyan (guides)
  - Flexbox layout for three columns on desktop
  - Grid layout for single column on mobile
  - Custom styling for map markers and overlays

## Impact

- **Affected Specs**: Creates new capability `calculator-ui`
- **Affected Code**:
  - New files: `calculator/templates/index.html`, `calculator/static/js/app.js`, `calculator/static/js/ui.js`, `calculator/static/css/style.css`
- **Dependencies**: 
  - Leaflet.js 1.9.4 (bundled locally)
  - Ballistics engine (proposal 3)
  - Heightmap data (proposal 1 - JSON format)
  - Minimap images (proposal 1 - PNG format)
  - Flask server (proposal 2)
- **User Impact**: End users interact exclusively with this UI for all calculator functionality
- **Testing**: Integration with in-game testing on Korengal Valley, Vadso City, Burning Sands
