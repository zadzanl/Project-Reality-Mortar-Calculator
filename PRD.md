# PROJECT REALITY MORTAR CALCULATOR

## User Stories \& Product Requirements Document


***

# DELIVERABLE 1: USER STORIES

## User Story 1: Map Selection and Visualization

**As a Squad Leader**, I want to select a PR map from a dropdown list and see a visual representation of the terrain with grid overlays, so that I can confirm I am operating on the correct map and understand the battlefield layout before placing mortars.

**Persona Context:** Squad Leader in live Project Reality operations. Wrong map yields incorrect firing solutions, wasted ammo, and lost time.

**Acceptance Criteria:**

- Map selector displays all available PR maps detected from game installation
- 2D map visualization loads within 500ms
- Grid overlay shows standard PR grid notation (A1-M13 with keypad subgrids 1-9)
- Zoom and pan controls function smoothly
- Map displays actual terrain representation (not placeholder)
- System remembers and pre-loads the last-selected map on startup

***

## User Story 2: Mortar Position Input with Height Detection

**As a Mortar Crew member**, I want to place my mortar position by clicking on the map OR entering grid coordinates (e.g., "D6-2"), and have the calculator automatically detect my elevation from the heightmap, so that I don't have to manually estimate my height above sea level.

**Persona Context:** Mortar Crew translating observer calls into firing data. Manual elevation estimates are error-prone and cause 30-40 meter misses at range.

**Acceptance Criteria:**

- Mortar marker is draggable on the 2D map
- Grid input field accepts PR notation (e.g., "D6-kpad7" or "Delta 6-2")
- Z-height is automatically extracted from heightmap and displayed
- Marker shows visual confirmation of placement
- Height value updates in real-time as marker is dragged
- Input validates format and map bounds, shows errors for invalid coordinates

***

## User Story 3: Target Position Input with Automatic Elevation

**As a Squad Leader**, I want to place target markers by clicking the map or entering coordinates, with automatic elevation detection, so that I can quickly designate fire missions without complex manual calculations.

**Persona Context:** Squad Leader coordinating fire and movement. Needs to quickly iterate firing solutions when adjusting for observed impacts.

**Acceptance Criteria:**

- Target marker placement works identically to mortar placement
- Multiple targets can be placed simultaneously
- Each target displays its grid reference and elevation
- Distance and azimuth to target are calculated automatically
- Target markers are visually distinct from mortar markers (red for target, blue for mortar)
- Line-of-sight indicator shows direct path between mortar and target

***

## User Story 4: High-Angle Firing Solution with Mils

**As a Mortar Crew member**, I want the calculator to display the High Angle firing solution in both Mils and Degrees, accounting for the height difference between my mortar and the target, so that I can accurately engage targets behind obstacles that would block low-angle fire.

**Acceptance Criteria:**

- Elevation displayed in Mils (primary) and Degrees (secondary)
- Calculation accounts for X, Y (horizontal distance), and Z (height difference)
- Formula uses correct PR physics constants (gravity 14.86 m/s², velocity 148.64 m/s)
- High angle solution prioritized (mortar fire arc)
- Visual warning if target is out of maximum range (1500m)

***

## User Story 5: Fast Communication During Combat

**As a Squad Leader under fire**, I want to see firing solutions update in real-time as I adjust markers, with clear azimuth and elevation displays, so that I can call for fire quickly without switching between multiple tools or performing mental calculations.

**Acceptance Criteria:**

- Calculation updates occur within 100ms of marker movement
- Azimuth displayed prominently in compass degrees
- Elevation displayed in Mils with Degree conversion
- Distance to target shown in meters
- Time-of-flight displayed (optional enhancement)

***

## User Story 6: Grid Coordinate Conversion

**As a Mortar Crew member**, I want to convert between PR grid notation (e.g., "B4-kpad7") and raw XY coordinates seamlessly, so that I can communicate effectively with teammates using standard callouts while the calculator handles the technical conversion.

**Acceptance Criteria:**

- Grid notation follows PR standard (A-M columns, 1-13 rows, keypad 1-9 subgrids)
- Conversion is bidirectional (grid ↔ XY coordinates)
- Grid reference validates input format
- Keypad orientation matches PR standard (7-8-9 top, 1-2-3 bottom)
- Invalid coordinates show clear error messages

***

## User Story 7: Offline Operation and Quick Launch

**As a Mortar Crew member**, I want to launch the calculator with a single click without requiring internet connectivity, so that I can use it during gameplay without alt-tabbing delays or external dependencies.

**Acceptance Criteria:**

- Single `run.bat` file launches server and opens browser automatically
- All map data and heightmaps stored locally
- Calculator works completely offline (no API calls)
- Startup time under 3 seconds
- Browser opens to correct localhost URL automatically

***

# DELIVERABLE 2: PRODUCT REQUIREMENTS DOCUMENT (PRD)


***

## A. PRODUCT OVERVIEW

### Goal

Create a **localhost web-based mortar calculator** for Project Reality: BF2 that provides ballistically accurate firing solutions accounting for X, Y, and Z (elevation) differences between mortar and target positions. The tool must operate completely offline and integrate seamlessly with gameplay.

### Success Metrics

- **Map Load Time:** <500ms per map
- **Calculation Accuracy:** ±1 Mil deviation from in-game behavior
- **Startup Time:** <3 seconds from double-clicking `run.bat`
- **User Adoption:** Tool becomes standard for mortar squad coordination


### Target Users

- **Primary:** Mortar crew operators (2-4 players per squad)
- **Secondary:** Squad Leaders coordinating fire missions
- **Tertiary:** Forward Observers spotting targets

***

## B. FUNCTIONAL REQUIREMENTS

### 1. Map Processing (Python Backend - Part A: The Processor)

**Requirement 1.1:** Automatic Game Installation Detection

- **Must** search standard PR installation paths:
    - `C:\Program Files (x86)\Project Reality\Project Reality BF2`
    - `D:\Games\Project Reality\Project Reality BF2`
    - User-specified custom path via configuration file
- **Must** detect `/levels/` directory containing map folders
- **Must** continue processing other maps if one fails
- **Must** generate processing report (maps found, maps processed, errors)

**Requirement 1.2:** Heightmap Extraction from server.zip

- **Must** locate `server.zip` within each map folder (e.g., `/levels/muttrah_city_2/server.zip`)
- **Must** extract `HeightmapPrimary.raw` (16-bit grayscale heightmap)
- **Must** parse file as **16-bit unsigned integer** array with little-endian byte order
- **Must** support standard PR heightmap resolutions: 1025×1025, 2049×2049, or 513×513 pixels
- **Must** handle the "+1" pixel border used for terrain stitching

**Requirement 1.3:** Heightmap Metadata Export

- **Must** extract from BF2 map config files:
    - **Map Size in Meters:** From `init.con` (e.g., 2048m × 2048m for 2km maps, 4096m × 4096m for 4km maps)
    - **Height Scale:** From `terrain.con` - maximum terrain height (typically 100-500m, range: 100-1000m)
    - **Grid Configuration:** 13×13 grid with 75m, 150m, or 300m per grid square (derived from map size)
- **Must** calculate conversion ratio: `meters_per_pixel = map_size_meters / (heightmap_resolution - 1)`
  - Note: Subtract 1 to account for the +1 pixel border used for terrain stitching
- **Must** export as JSON metadata file: `map_name_metadata.json`
- **Must** log warnings for missing maps or corrupted files
- **Must** use default height_scale of 300m if `terrain.con` is missing or corrupted

**Requirement 1.4:** Heightmap Conversion to JSON

- **Must** convert 16-bit RAW to JSON for lossless web compatibility
- **Must** maintain full 16-bit precision (0-65535 per pixel)
- **Must** use the following JSON structure:

```json
{
  "resolution": 1025,
  "width": 1025,
  "height": 1025,
  "format": "uint16",
  "data": [0, 1234, 5678, ...],  // Flat array, row-major order
  "compression": "none"  // Future: gzip base64 for smaller size
}
```

- **Must** preserve original resolution including +1 border (1025×1025 or 2049×2049)
  - Rationale: Maintains consistency with engine format, simplifies debugging
- **Should** optionally compress data array using gzip + base64 encoding if file size >5MB
- **Must** store processed data in `/processed_maps/` directory structure:

```
/processed_maps/
  /muttrah_city_2/
    heightmap.json       # 16-bit height data
    metadata.json        # Map configuration
    minimap.png          # Optional: Visual preview
```


***

### 2. The User Interface (HTML/CSS/JavaScript Frontend - Part B: The Calculator)

**Requirement 2.1:** Map Selection Interface

- **Dropdown menu** listing all processed maps alphabetically
- **Map preview** showing minimap thumbnail on selection
- **Load button** to confirm selection and load full map data
- Display map metadata (size, grid scale) in UI corner

**Requirement 2.2:** Coordinate Input System

**Two input modes:**

**Mode A: Dropdown Input (Primary)**
- **Mortar Position Fields (3 dropdowns):**
    - **Column:** Dropdown A-M (13 options)
    - **Row:** Dropdown 1-13 (13 options)
    - **Keypad:** Dropdown with visual numpad layout (9 options: 7,8,9 / 4,5,6 / 1,2,3)
- **Target Position Fields:**
    - Same 3-dropdown structure as mortar position
- **Conversion Logic:**
    - Letter = Column (A=0, B=1, ..., M=12)
    - Number = Row (1-13, maps to 0-12 internally)
    - Keypad = Subgrid position (7=top-left, 9=top-right, 1=bottom-left, 3=bottom-right, 5=center)
- **Display Format:**
    - Show selected coordinates as "Column Row-Keypad" (e.g., "D 6-7")
    - Update in real-time as dropdowns change

**Mode B: Interactive Map Clicking (Secondary)**
- **Click-to-place markers** directly on map visualization
- **Draggable markers** for refinement
- **Dropdowns auto-update** when markers placed or dragged

**Requirement 2.3:** Map Visualization Panel

- **2D top-down map view** using Leaflet.js or HTML5 Canvas
- **Pan controls:** Click-drag to pan
- **Zoom controls:** Mouse wheel or +/- buttons (6-8 zoom levels)
- **Grid overlay:** PR standard grid lines with letter/number labels
- **Markers:**
    - **Blue marker:** Mortar position (with elevation badge)
    - **Red marker:** Target position (with elevation badge)
    - **Cyan line:** Direct path between mortar and target
    - **Range circle:** Semi-transparent circle showing max range (1500m) from mortar
- **Performance:** 60 FPS during pan/zoom on mid-range hardware

**Requirement 2.4:** Results Display Panel

**Three-Column Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Header: "PR Mortar Calculator" [Map Dropdown ▼]       │
├────────────┬─────────────────────────┬──────────────────┤
│            │                         │                  │
│  Inputs    │   Map Visualization     │   Results        │
│  Panel     │   (Leaflet.js)          │   Panel          │
│            │                         │                  │
│  - Mortar  │   [Interactive Map]     │   Distance: 1234m│
│    Grid    │   [Blue/Red Markers]    │   Azimuth: 045°  │
│    B4-7    │   [Range Circle]        │   Δ Elev: +45m   │
│            │                         │                  │
│  - Target  │                         │   ELEVATION:     │
│    Grid    │                         │   ┏━━━━━━━━━━┓   │
│    C2-3    │                         │   ┃ 1247 mils┃   │
│            │                         │   ┗━━━━━━━━━━┛   │
│  [Calc]    │                         │   70.2°          │
│            │                         │                  │
│  Elevations│                         │   TOF: 8.3s      │
│  Mortar: 12m                         │                  │
│  Target: 57m                         │   [Status: OK]   │
│            │                         │                  │
└────────────┴─────────────────────────┴──────────────────┘
```

**Color Coding:**
- **Blue:** Mortar position, friendly elements
- **Red:** Target position, danger/out-of-range warnings
- **Green:** Valid inputs, in-range status
- **Yellow:** Warnings (extended range, high elevation)
- **Cyan:** Line-of-sight, range indicators
- **Gray:** Disabled elements, grid lines

**Must Display:**
- **Horizontal Distance:** `1234 m` (Euclidean distance in X-Y plane)
- **Azimuth:** `045°` (bearing from mortar to target, 0-360°)
- **Elevation Delta:** `+45 m` or `-23 m` (Target Z - Mortar Z)
- **Mortar Elevation (High Angle):**
    - `1247 mils` (primary display - PR standard)
    - `70.2°` (secondary display for reference)
- **Time of Flight:** `8.3 seconds` (calculated from trajectory)
- **Range Status:**
    - Green: In optimal range (<1200m)
    - Yellow: Extended range (1200-1500m, reduced accuracy)
    - Red: Out of range (>1500m, impossible shot)

**Requirement 2.5:** Visual Warnings

- **Out of Range Warning:** Large red banner if distance >1500m
- **Extreme Elevation Warning:** Yellow alert if elevation difference >100m (accuracy may suffer)
- **Invalid Coordinate Warning:** Real-time validation errors in input fields

**Requirement 2.6:** Responsive Behavior

- **Desktop (>1200px):** Three-column layout as shown
- **Tablet (768-1200px):** Two-column (inputs+results stacked, map full-width)
- **Mobile (<768px):** Single column, collapsible panels

***

### 3. The Calculator (Ballistics Math Engine - JavaScript)

**Requirement 3.1:** Input Processing and Data Model

**Data Structure (V1 - Single Mortar, Expandable to Arrays):**
```javascript
const firingSolution = {
  mortar: {
    id: 1,
    gridRef: { column: 'D', row: 6, keypad: 7 },
    worldPos: { x: 1234.5, y: 2345.6, z: 45.2 }
  },
  target: {
    id: 1,
    gridRef: { column: 'C', row: 2, keypad: 3 },
    worldPos: { x: 987.3, y: 1876.4, z: 89.7 }
  },
  solution: {
    distance: 1234.5,  // meters
    azimuth: 45.2,      // degrees (0-360)
    elevation: 1247,    // mils
    elevationDeg: 70.2, // degrees (secondary)
    heightDelta: 44.5,  // meters (target - mortar)
    timeOfFlight: 8.3,  // seconds
    inRange: true,      // boolean
    status: 'OK'        // 'OK' | 'OUT_OF_RANGE' | 'UNREACHABLE'
  }
};
```

**V2+ Expansion Structure (Placeholder):**
```javascript
// Future: Array of mortars, each with multiple targets
const firingSolutions = [
  {
    mortarId: 1,
    mortar: { ... },
    targets: [{ targetId: 1, worldPos: {...}, solution: {...} }, ...]
  },
  { mortarId: 2, ... }
];
```

- **Inputs:**
    - Mortar Position: `(x1, y1, z1)` in meters
    - Target Position: `(x2, y2, z2)` in meters
- **Derived Values:**
    - Horizontal Distance: `D = sqrt((x2-x1)² + (y2-y1)²)`
    - Height Difference: `ΔZ = z2 - z1` (positive if target higher)
    - Azimuth: `θ = atan2(y2-y1, x2-x1)` converted to compass bearing (0-360°)

**Requirement 3.2:** Ballistic Calculation (High Angle Solution)

**Physics Constants (CRITICAL - DO NOT DEVIATE):**

| Constant | Symbol | Value | Unit | Source |
| :-- | :-- | :-- | :-- | :-- |
| Gravity (PR Engine) | g | **14.86** | m/s² | Project Reality engine (NOT Earth standard 9.8) |
| Projectile Initial Velocity | v₀ | **148.64** | m/s | PR mortar specification |
| Maximum Effective Range | R_max | **1500** | m | PR gameplay balance |
| Angular Unit (Primary) | - | **Mils** | NATO mils | 6400 mils = 360° |
| Angular Unit (Secondary) | - | **Degrees** | degrees | 360° = full circle |

**Coordinate System (Player-Facing UI):**
- **Origin:** Northwest corner of map (0, 0) - matches in-game PR map display
- **X-axis:** East (increases right)
- **Y-axis:** South (increases down)
- **Z-axis:** Elevation (increases upward from sea level = 0)
- **Azimuth Reference:** 0° = North, 90° = East, 180° = South, 270° = West

**CRITICAL NOTE:** This differs from PR engine's internal coordinate system (center origin). All calculator math and UI use the player-facing NW-origin system for consistency with in-game map displays. When extracting data from game files, coordinate transformation may be needed.

**Simplified Ballistic Formula (High Angle):**

```
For high-angle mortar fire (θ > 45°):

Elevation Angle (φ) = arctan(
  (v² + sqrt(v⁴ - g*(g*D² + 2*v²*ΔZ))) / (g*D)
)

Where:
- φ = Firing elevation angle (radians)
- v = 148.64 m/s
- g = 14.86 m/s²
- D = Horizontal distance (meters)
- ΔZ = Height difference (meters, + if target higher)
```

**Conversion to Mils:**

```
Mils = φ (in radians) × (6400 / (2π))
Degrees = φ (in radians) × (180 / π)
```

**Time of Flight Calculation:**

```
Time of Flight (t) = D / (v₀ * cos(φ)) + (v₀ * sin(φ) + sqrt((v₀ * sin(φ))² + 2 * g * ΔZ)) / g

Simplified approximation for high-angle fire:
t ≈ (2 * v₀ * sin(φ)) / g

Where:
- t = Time of flight (seconds)
- D = Horizontal distance (meters)
- v₀ = 148.64 m/s (initial velocity)
- φ = Elevation angle (radians)
- g = 14.86 m/s² (PR gravity)
- ΔZ = Height difference (meters)
```

**Requirement 3.3:** Edge Cases & Validation

**Case 1: Target Out of Physical Range**
- If discriminant `(v⁴ - g*(g*D² + 2*v²*ΔZ)) < 0` → Physically impossible shot
- Display: "TARGET UNREACHABLE - Reduce distance or elevation difference"

**Case 2: Target Beyond Gameplay Range**
- If `D > 1500m` → Out of effective range
- Display: "OUT OF RANGE - Maximum range 1500m"

**Case 3: Zero Distance**
- If `D < 1m` → Invalid firing solution
- Display: "ERROR - Mortar and target positions too close"

**Case 4: Extreme Elevation Difference**
- If `|ΔZ| > 200m` → Warn about accuracy degradation
- Display: "WARNING - Extreme elevation difference may reduce accuracy"

**Case 5: Coordinates Outside Map Bounds**
- If `x < 0 || x > map_size || y < 0 || y > map_size` → Invalid position
- Display: "ERROR - Position outside map boundaries"
- Validation occurs when:
  - User clicks outside map area
  - Dropdown selection results in invalid coordinate
  - Marker dragged beyond map edge (snap to boundary)

**Requirement 3.4:** Height Sampling with Bilinear Interpolation

- **Must** use bilinear interpolation when sampling elevation from heightmap
- **Algorithm:**
  1. Convert world XY coordinates to heightmap pixel coordinates
  2. Calculate fractional pixel position (e.g., x=123.7, y=456.3)
  3. Sample 4 surrounding pixels (floor and ceil of x and y)
  4. Interpolate linearly in X direction (top pair, bottom pair)
  5. Interpolate linearly in Y direction (final result)
- **Purpose:** Smooth elevation values between discrete pixels, reduces 15cm precision to ~5cm effective precision
- **Rationale:** Mortar has ~30m spread, but smoother UX and more accurate for close-range shots

**Requirement 3.5:** Real-Time Updates

- Recalculate on "Calculate" button press only (not real-time during drag)
- Display loading indicator if calculation exceeds 50ms (should never happen)
- Calculations run on main thread (simple enough, no Web Workers needed for V1)

***

## C. TECHNICAL SPECIFICATIONS

### Tech Stack (MANDATORY)

- **Backend (Processor):** Python 3.8+
    - Required Libraries: `numpy` (array operations), `zipfile` (extract server.zip), `struct` (binary RAW parsing), `json`
    - Optional: `PIL/Pillow` (only for minimap PNG generation)
- **Frontend (Calculator):**
    - HTML5 + Vanilla JavaScript (ES6+)
    - CSS3 for styling (Flexbox/Grid for layout)
    - **Leaflet.js 1.9+** for map rendering (bundled locally, no CDN)
      - Rationale: Battle-tested, 40KB gzipped, excellent custom projection support
- **Server:** Flask 2.3+ (Python microframework)
    - **Purpose:** Serve static files only (HTML, CSS, JS, JSON)
    - **No API endpoints** - all calculations happen in browser JavaScript
    - Single-file server script: `calculator/server.py`
    - Advantages over `http.server`: Better error handling, MIME type support, easier routing for future expansion


### Deployment Architecture

```
/ProjectRealityMortarCalc/
  /processor/              # Part A: Map Processing
    process_maps.py        # Main heightmap processor
    utils.py               # Helper functions
  /calculator/             # Part B: Web Calculator
    /static/
      /js/
        app.js             # Main application logic
        ballistics.js      # Physics calculations (pure functions)
        coordinates.js     # Grid/world coordinate conversion
        heightmap.js       # Height sampling with bilinear interpolation
        ui.js              # UI state management
      /css/
        styles.css
      /lib/
        leaflet/           # Leaflet.js (bundled, no CDN)
      /maps/               # Symlink to processed_maps/
    index.html             # Main UI
    server.py              # Flask static file server
  /processed_maps/         # Generated by processor (bundled in repo)
    /muttrah_city_2/
    /fallujah_west/
    ...
  /tests/                  # Unit tests (V2+)
    test_ballistics.py
    test_coordinates.py
  run.bat                  # Windows launcher
  run.sh                   # Linux/Mac launcher
  README.md
  requirements.txt         # Python dependencies
  .gitignore
```

### Modularity Requirements (V1 Foundation for V2+ Expansion)

**Code Organization Principles:**

1. **Separation of Concerns:**
   - `ballistics.js` - Pure math functions, no DOM access
   - `coordinates.js` - Grid↔World conversion, no UI logic
   - `heightmap.js` - Height sampling, no calculation logic
   - `ui.js` - DOM manipulation only, delegates calculations

2. **Function Signatures (Array-Ready):**
```javascript
// V1: Single item, but accepts arrays internally
function calculateFiringSolution(mortar, target) { ... }

// V2+: Trivial expansion to multiple mortars
function calculateMultipleFiringSolutions(mortars, targets) {
  return mortars.map(m => 
    targets.map(t => calculateFiringSolution(m, t))
  );
}
```

3. **UI Placeholders (V2+ Features):**
   - "Add Mortar" button (disabled, tooltip: "Coming in V2")
   - "Add Target" button (disabled)
   - "Save Fire Plan" menu item (grayed out)
   - Data model uses IDs (mortarId, targetId) for future uniqueness

4. **Configuration Externalization:**
```javascript
// config.js (V1)
const CONFIG = {
  MAX_MORTARS: 1,    // V2+: Increase to 4
  MAX_TARGETS: 1,    // V2+: Increase to 10
  ENABLE_SAVE: false // V2+: localStorage persistence
};
```

5. **Extension Points:**
   - CSS uses BEM naming for easy theming
   - Event handlers use delegation for dynamic elements
   - Map layers structured for trajectory overlays (V2+)


### Execution Flow

1. **First-Time Setup:**
    - User runs `run.bat`
    - Batch file checks if `/processed_maps/` exists
    - If not: Runs `python processor/process_maps.py` (one-time processing)
    - Prompts user for PR installation path if not auto-detected
2. **Normal Operation:**
    - `run.bat` executes: `python calculator/server.py`
    - Server starts on `http://localhost:8080`
    - Batch file auto-opens default browser to `http://localhost:8080`
3. **User Interaction:**
    - User selects map → Loads heightmap + metadata from `/processed_maps/`
    - User places mortar + target markers
    - JavaScript calculates firing solution using local data
    - No server-side calculation needed (all frontend)

### Offline Policy (CRITICAL)

- **Zero External Dependencies:** No CDN links (bundle Leaflet.js locally)
- **No API Calls:** All data must be local files
- **No Telemetry:** No analytics, tracking, or phone-home
- **Portable:** Entire `/ProjectRealityMortarCalc/` folder can be copied to USB drive

***

## D. PHYSICS MODEL DEFINITION (MANDATORY CONSTANTS)

### PR Engine Physics

**IMPORTANT: These are Project Reality game values, NOT real-world physics.**

```javascript
const PR_PHYSICS = {
  // Gravity in the game (NOT Earth's 9.8)
  GRAVITY: 14.86,              // meters per second squared
  
  // How fast mortar shell leaves the tube
  PROJECTILE_VELOCITY: 148.64, // meters per second
  
  // Maximum distance mortar can shoot
  MAX_RANGE: 1500,             // meters (game balance limit)
  
  // Angular conversions (how to measure angles)
  MILS_PER_CIRCLE: 6400,       // Military uses mils (not degrees)
  DEGREES_PER_CIRCLE: 360,     // Normal degrees
  RADIANS_PER_CIRCLE: 2 * Math.PI, // Math uses radians
  
  // Heightmap specs (elevation data format)
  HEIGHTMAP_BIT_DEPTH: 16,     // 16-bit = numbers 0 to 65535
  HEIGHTMAP_RESOLUTIONS: [1025, 2049], // Image sizes used in game
  
  // Grid system (map coordinates)
  GRID_COLUMNS: ['A','B','C','D','E','F','G','H','I','J','K','L','M'], // 13 columns
  GRID_ROWS: [1,2,3,4,5,6,7,8,9,10,11,12,13], // 13 rows
  KEYPAD_LAYOUT: [7,8,9,4,5,6,1,2,3], // Phone keypad orientation
  
  // Map scales (how big each grid square is)
  GRID_SCALES: {
    '1km': 75,   // 75 meters per square on 1km maps
    '2km': 150,  // 150 meters per square on 2km maps
    '4km': 300   // 300 meters per square on 4km maps
  }
};
```


### Heightmap Coordinate Conversion

**Step 1: Convert pixel coordinates to world meters**

```python
# Python (Processor)
def pixel_to_world(pixel_x, pixel_y, heightmap_res, map_size_meters):
    """
    Convert heightmap pixel coordinates to world XY meters.
    
    Example:
    - Pixel (512, 512) on a 1025x1025 heightmap
    - Map size is 2048 meters
    - Result: (1024m, 1024m) - the center of the map
    """
    # Calculate how many meters each pixel represents
    meters_per_pixel = map_size_meters / heightmap_res
    
    # Multiply pixel position by meters per pixel
    world_x = pixel_x * meters_per_pixel
    world_y = pixel_y * meters_per_pixel
    
    return world_x, world_y

**Step 2: Get elevation (Z height) from pixel value**

```python
def get_elevation(pixel_x, pixel_y, heightmap_array, height_scale):
    """Extract Z-height from 16-bit heightmap using PR:BF2 formula
    
    Example:
    - Pixel value: 32768 (middle gray)
    - Height scale: 300 meters
    - Calculation: 32768 / 65535 = 0.5 (50%)
    - Result: 0.5 * 300 = 150 meters elevation
    """
    # Get the raw 16-bit value from heightmap (0 to 65535)
    raw_value = heightmap_array[pixel_y, pixel_x]
    
    # Convert to 0.0 to 1.0 scale (percentage)
    normalized = raw_value / 65535.0
    
    # Multiply by max height to get actual meters
    elevation_meters = normalized * height_scale
    
    return elevation_meters
    
    # Where height_scale comes from terrain.con file:
    # - Black pixel (0) = 0m (sea level)
    # - White pixel (65535) = height_scale meters (max terrain height)
    # - Typical values: 100-500m, max observed: 1000m
```


### Grid Coordinate Parsing

**What this function does:** Converts grid references like "D6-7" into XY coordinates in meters.

```javascript
// JavaScript (Frontend)
function parseGridReference(gridRef) {
  // Examples of valid inputs:
  // - "D6-2" (short form)
  // - "Delta 6 kpad 2" (long form with words)
  // - "d6-kpad2" (lowercase also works)
  
  // Look for pattern: Letter, Number, Keypad number
  const regex = /([A-Ma-m])(\d{1,2})[-\s]*(kpad\s*)?(\d)/i;
  const match = gridRef.match(regex);
  
  // If pattern doesn't match, input is invalid
  if (!match) return null;
  
  // Extract the parts
  const column = match[1].toUpperCase();  // "D"
  const row = parseInt(match[2]);          // 6
  const keypad = parseInt(match[4]);       // 2
  
  // Convert to XY coordinates in meters
  // (calculation depends on grid square size for this map)
  const x = calculateX(column, keypad);  // Calculate X position
  const y = calculateY(row, keypad);     // Calculate Y position
  
  return { column, row, keypad, x, y };
}
```

**How grid-to-XY conversion works:**

1. **Column letter → X position**
   - A=0, B=1, C=2, ... M=12
   - Multiply by grid square size (75m, 150m, or 300m)
   - Add offset for keypad position within square

2. **Row number → Y position**
   - Row 1=0, Row 2=1, ... Row 13=12
   - Multiply by grid square size
   - Add offset for keypad position within square

3. **Keypad number → Offset within square**
   - Keypad 7 (top-left) = (0m, 0m)
   - Keypad 5 (center) = (half square, half square)
   - Keypad 3 (bottom-right) = (full square, full square)


***

## E. FUTURE ENHANCEMENTS (OUT OF SCOPE FOR V1)

### Phase 2 Features (Not Required for MVP)

- **Multi-Mortar Coordination:**
    - Battery of 2+ mortars firing synchronized salvos
    - Staggered fire sequences
- **Firing Tables:**
    - Pre-calculated range cards for common distances
    - Export to CSV for printing
- **Trajectory Visualization:**
    - 3D arc showing projectile path
    - Obstacle detection (terrain blocking line of fire)
- **Save/Load Fire Plans:**
    - Store mortar + target positions as JSON
    - Quick-load for repeated gameplay on same map
- **Wind Correction:**
    - Lateral drift calculation (if PR implements wind)
- **Admin Features:**
    - Multi-user network mode (squad coordination over LAN)
    - Voice callout generation (text-to-speech firing commands)

***

## TESTING STRATEGY

### Manual In-Game Validation

**Test Maps (Priority Order):**

1. **Korengal Valley** - Extreme vertical terrain
   - Test Case: Mortar in valley floor, target on mountain peak
   - Expected: Solution accounts for 300-500m elevation difference
   - Validates: Height scale accuracy, extreme ΔZ handling

2. **Vadso City** - Large distance + large elevation
   - Test Case: Mortar at sea level, target on hilltop 1200m+ away
   - Expected: High-angle solution hits target
   - Validates: Long-range ballistics, combined distance+elevation

3. **Burning Sands** - Flat terrain control
   - Test Case: Mortar and target both at ~same elevation
   - Expected: Azimuth and range match in-game compass
   - Validates: Horizontal distance calculation, grid system accuracy

**Validation Protocol:**

1. **Setup Phase:**
   - Load map in PR:BF2 local server
   - Place mortar at known grid coordinate
   - Place target at second known coordinate
   - Note in-game compass bearing and range

2. **Calculator Phase:**
   - Input same coordinates in calculator
   - Record calculated azimuth, elevation, distance

3. **Fire Mission Phase:**
   - Use calculated firing solution in-game
   - Observe impact point relative to target
   - Measure miss distance (use map editor overlay if needed)

4. **Acceptance Criteria:**
   - Azimuth within ±2° of in-game compass
   - Elevation results in impact within 50m of target (2× mortar spread)
   - Distance calculation within ±10m of in-game range

**Test Data Collection:**
```
Map: Korengal Valley
Mortar: D6-5 (x=1234.5, y=2345.6, z=45.2m)
Target: C2-3 (x=987.3, y=1876.4, z=389.7m)
Calculated: Az=045°, El=1247mils, Dist=1234m, TOF=8.3s
In-Game Result: Impact 23m from target (PASS)
```

### Automated Unit Tests (Future V2+)
- Grid coordinate parser edge cases
- Height sampling interpolation accuracy
- Ballistic formula against known solutions
- Out-of-bounds handling

## QUALITY CHECKLIST

### Before Implementation, Verify:

- [x] Gravity constant is **14.86 m/s²** (not 9.8)
- [x] Projectile velocity is **148.64 m/s**
- [x] Architecture is **Localhost Web App** (not desktop GUI)
- [x] Heightmap format is **16-bit RAW** grayscale
- [x] Grid system uses **PR standard notation** (A-M, 1-13, keypad 1-9)
- [x] Calculator accounts for **Height Difference (Z-axis)**
- [x] No external API dependencies (completely offline)
- [x] Single `run.bat` launches entire system

***

## IMPLEMENTATION GUIDE

**READ THIS FIRST:** This section gives step-by-step instructions. Follow them in order.

### Step 1: Develop map_processor.py

**What this script does:** Reads map files from Project Reality game and converts them to JSON format.

**Steps to implement:**

1. **Import Python libraries:**
   ```python
   import os        # File and folder operations
   import struct    # Read binary files
   import json      # Write JSON files
   import zipfile   # Open .zip files
   from PIL import Image  # Optional: create preview images
   ```

2. **Set up path to Project Reality installation:**
   ```python
   # Default paths to check (try these first)
   PR_PATHS = [
       r"C:\Program Files (x86)\Project Reality\Project Reality BF2",
       r"D:\Games\Project Reality\Project Reality BF2"
   ]
   # User can also specify custom path in config file
   ```

3. **Find all map folders:**
   ```python
   # Look for /levels/ directory
   # Each subfolder is a map (example: /levels/muttrah_city_2/)
   ```

4. **For each map, extract heightmap:**
   ```python
   # Open server.zip file
   # Find HeightmapPrimary.raw inside
   # Read as 16-bit unsigned integers (little-endian)
   # WARNING: Use '<H' format in struct.unpack (< means little-endian, H means unsigned short)
   ```

5. **Read map configuration files:**
   ```python
   # From init.con: Get map size (2048m or 4096m)
   # From terrain.con: Get height scale (100-1000m)
   # WARNING: If terrain.con is missing, use default 300m
   ```

6. **Convert heightmap to JSON:**
   ```python
   # Create JSON structure:
   {
       "resolution": 1025,
       "width": 1025,
       "height": 1025,
       "format": "uint16",
       "data": [0, 1234, 5678, ...]  # All pixel values in order
   }
   # Keep all 16-bit precision (do NOT convert to 8-bit)
   ```

7. **Create metadata.json:**
   ```python
   {
       "map_name": "muttrah_city_2",
       "map_size": 2048,        # meters
       "height_scale": 300,     # meters
       "grid_scale": 150,       # meters per grid square
       "heightmap_resolution": 1025  # pixels
   }
   ```

8. **Handle errors gracefully:**
   - If a map file is corrupted, skip it and continue with next map
   - Write error messages to log file
   - At end, print report: "Processed 45 maps, 2 errors"

### Step 2: Develop Frontend (index.html + JavaScript)

**What this does:** Creates the web page where users interact with the calculator.

**Steps to implement:**

1. **Create HTML structure (index.html):**
   ```html
   <!-- Three-column layout -->
   <div class="calculator">
     <div class="calculator__inputs"><!-- Dropdowns go here --></div>
     <div class="calculator__map"><!-- Leaflet map goes here --></div>
     <div class="calculator__results"><!-- Results display here --></div>
   </div>
   ```

2. **Add map dropdown and load button:**
   ```html
   <select id="map-selector">
     <option value="muttrah_city_2">Muttrah City</option>
     <!-- Add all available maps -->
   </select>
   <button id="load-map">Load Map</button>
   ```

3. **Add coordinate input dropdowns:**
   ```html
   <!-- Mortar position -->
   <label>Mortar Column:</label>
   <select id="mortar-column">
     <option value="A">A</option>
     <option value="B">B</option>
     <!-- A through M -->
   </select>
   
   <label>Mortar Row:</label>
   <select id="mortar-row">
     <option value="1">1</option>
     <!-- 1 through 13 -->
   </select>
   
   <label>Mortar Keypad:</label>
   <select id="mortar-keypad">
     <option value="7">7 (Top-Left)</option>
     <option value="8">8 (Top)</option>
     <option value="9">9 (Top-Right)</option>
     <!-- Show keypad layout visually -->
   </select>
   
   <!-- Repeat for target position -->
   ```

4. **Initialize Leaflet map:**
   ```javascript
   // Create map (don't use geographic coordinates)
   const map = L.map('map', {
     crs: L.CRS.Simple,  // IMPORTANT: Use Simple coordinate system (not GPS)
     minZoom: -2,
     maxZoom: 2
   });
   ```

5. **Load heightmap JSON:**
   ```javascript
   // Fetch heightmap data
   const response = await fetch('/maps/muttrah_city_2/heightmap.json');
   const heightmapData = await response.json();
   
   // Store in variable for later height lookups
   window.currentHeightmap = heightmapData;
   ```

6. **Implement height sampling function:**
   ```javascript
   function getElevation(x, y) {
     // IMPORTANT: Use bilinear interpolation (average 4 surrounding pixels)
     // Step 1: Convert world XY to pixel coordinates
     // Step 2: Get 4 surrounding pixel values
     // Step 3: Interpolate between them
     // Step 4: Apply height scale formula
     return elevation;
   }
   ```

7. **Implement ballistic solver:**
   ```javascript
   function calculateFiringSolution(mortar, target) {
     // Use EXACT formulas from "Ballistic Calculation" section
     // Do NOT modify gravity or velocity constants
     const g = 14.86;   // NOT 9.8
     const v = 148.64;  // Do not change
     
     // Calculate horizontal distance
     const D = Math.sqrt((target.x - mortar.x)**2 + (target.y - mortar.y)**2);
     
     // Calculate height difference
     const deltaZ = target.z - mortar.z;
     
     // Apply high-angle formula (see PRD for complete formula)
     // ...
     
     return { azimuth, elevation, distance, tof };
   }
   ```

8. **Update UI when Calculate button clicked:**
   ```javascript
   document.getElementById('calculate-btn').addEventListener('click', () => {
     // Get mortar and target positions
     // Call calculateFiringSolution()
     // Display results
     // Only calculate on button press (not real-time)
   });
   ```

### Step 3: Validation Protocols

**How to test if your calculator works correctly:**

**Protocol A: The "Korengal" Test**
- Load Korengal Valley map (has mountains)
- Place mortar in valley floor (low elevation)
- Place target on mountain peak about 600 meters away (high elevation)
- Calculate firing solution
- Go into game and fire mortar with that solution
-  **PASS:** Shell hits within 50 meters of target
-  **FAIL:** Shell hits mountainside (elevation calculation wrong)

**Protocol B: The "Al Basrah" Scale Test**
- Load Al Basrah map
- Find two grid references that are exactly 1 kilometer apart
- Input them as mortar and target
- Check calculated distance
-  **PASS:** Shows exactly 1000 meters
-  **FAIL:** Shows different distance (map size parsing wrong)

## SUCCESS CRITERIA

### V1.0 is Complete When:

1. Processor successfully extracts heightmaps from PR installation
2. Calculator displays interactive map with grid overlay
3. User can place mortar + target via click OR grid input
4. Elevation values auto-populate from heightmap
5. Firing solution displays accurate Azimuth + Elevation (Mils)
6. Calculation matches in-game behavior within ±1 Mil
7. Tool runs completely offline on localhost
8. `run.bat` launches tool in <3 seconds
9. Documentation includes example screenshots and usage guide
10. Code is open-source on GitHub with clear README

***

## APPENDIX: REFERENCE MATERIALS

### Data Sources Consulted

- **Forum:** [https://forum.realitymod.com/showthread.php?t=130362](https://forum.realitymod.com/showthread.php?t=130362)
- **Manual:** [https://www.realitymod.com/manual/pr_manual.pdf](https://www.realitymod.com/manual/pr_manual.pdf) (Mortar section)
- **Community Tools:**
    - SkyJumpy's MortarCalc (precedent for feature set)
    - SquadCalc (similar architecture for Squad game)


### Technical References

- **16-bit RAW Format:** IBM PC byte order, single channel, 1025×1025 or 2049×2049
- **BF2 Coordinate System:** Origin (0,0) at northwest corner, +X east, +Y south
- **Mil/Degree Conversion:** 1 circle = 6400 mils = 360° = 2π radians

***

**END OF DOCUMENT**

***

**Note to Implementation Agent:** This PRD is your blueprint. Every constant, formula, and architectural decision has been researched and validated against Project Reality's actual behavior. Do NOT deviate from the physics constants or assume "standard" values. When in doubt, refer back to this document. Good luck, and may your mortars fly true! 🎯
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^3][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.youtube.com/watch?v=hWWz21krKbA

[^2]: https://forum.realitymod.com/viewtopic.php?t=91183

[^3]: https://forum.realitymod.com/viewtopic.php?t=73115

[^4]: https://www.youtube.com/watch?v=RTWPkzNRtV4

[^5]: https://www.cheetah3d.com/forum/index.php?threads%2F3237%2F

[^6]: https://forum.realitymod.com/viewtopic.php?t=86390

[^7]: https://www.realitymod.com/manual/en/the_basics.html

[^8]: https://forums.unrealengine.com/t/raw-heightmap-formats-accepted-for-level-import/145934

[^9]: https://forum.realitymod.com/viewtopic.php?t=101803

[^10]: https://forum.realitymod.com/viewtopic.php?t=143038

[^11]: https://forum.realitymod.com/viewtopic.php?t=43017

[^12]: https://ufdcimages.uflib.ufl.edu/AA/00/06/85/31/00345/05-28-2020_pdf.txt

[^13]: https://www.reddit.com/r/joinsquad/comments/5cfvlw/we_are_the_developers_of_squad_ask_us_anything/

[^14]: https://forum.realitymod.com/viewtopic.php?t=113026

[^15]: https://forum.realitymod.com/viewtopic.php?t=131650

[^16]: https://forum.realitymod.com/viewtopic.php?t=1171

[^17]: https://www.realitymod.com/forum/f138-infantry-tactics/104645-pr-guide-tips-tricks.html

[^18]: https://forum.realitymod.com/viewtopic.php?t=119735

[^19]: https://github.com/matthiaszeller/python-calc

[^20]: https://www.reddit.com/r/Stormworks/comments/1m70w8j/complete_guide_for_ballistic_calculation_revised/

[^21]: https://forums.unrealengine.com/t/ascii-grid-to-heightmap-for-ue4/134773

[^22]: https://github.com/iamAbhishekkumar/Scientific-calculator

[^23]: https://dspace.mist.ac.bd/xmlui/bitstream/handle/123456789/979/Saraf - 4 copy.pdf?sequence=1\&isAllowed=y

[^24]: https://forums.unrealengine.com/t/heightmap-vertice-values-to-world-height/112388

[^25]: https://github.com/deepankarvarma/Basic-Calculator-Using-Python

[^26]: https://forum.realitymod.com/viewtopic.php?t=90278

[^27]: https://www.youtube.com/watch?v=QzXbGJ5BsUw

[^28]: https://github.com/juliotrigo/pycalculator

[^29]: https://github.com/tdjsnelling/babel

[^30]: https://github.com/grimwm/libballistics

[^31]: https://gist.github.com/10se1ucgo/9a5e84ee8c0cce51e04aca31d057c372?permalink_comment_id=3719160

[^32]: https://github.com/dbookstaber/py_ballistics

[^33]: https://github.com/SquadFM/Squad-Field-Manual

[^34]: https://github.com/o-murphy/js-ballistics

[^35]: https://github.com/Shemich/Shemich

[^36]: https://github.com/sh4rkman/SquadCalc

[^37]: https://forum.realitymod.com/viewtopic.php?t=134649

[^38]: https://github.com/sirdoombox/PostScriptumMortarCalculator

[^39]: https://forum.realitymod.com/viewtopic.php?t=150088

[^40]: https://github.com/Whiplash141/squad-mortar-calculator

[^41]: https://forum.realitymod.com/viewtopic.php?t=69889\&start=120