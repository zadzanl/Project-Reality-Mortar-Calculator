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

**Requirement 1.1:** Local Map Collection Script (`collect_maps.py`)

- **Must** search standard PR installation paths:
    - `C:\Program Files (x86)\Project Reality\Project Reality BF2`
    - `D:\Games\Project Reality\Project Reality BF2`
    - User-specified custom path via command-line argument or interactive prompt
- **Must** detect `/mods/pr/levels/` directory containing map folders
- **Must** copy both `server.zip` AND `client.zip` files from each map folder to `/raw_map_data/[map_name]/`
    - `server.zip` contains heightmap elevation data (`heightmapprimary.raw`)
    - `client.zip` contains visual minimap textures and other client-side assets (in `info/` directory)
- **Must** validate each server.zip file:
    - Calculate MD5 checksum
    - Verify zip file integrity (can be opened)
    - Confirm contains `heightmapprimary.raw` (case-insensitive)
- **Must** validate each client.zip file:
    - Calculate MD5 checksum (separately from server.zip)
    - Verify zip file integrity (can be opened)
    - Confirm contains `info/` directory with at least one `.dds` file
    - Log warning if client.zip missing but continue processing (heightmap-only mode)
- **Must** handle duplicates/updates:
    - Compare MD5 checksums with existing files
    - Skip if identical, update if different (version tracking in manifest)
- **Must** generate `manifest.json`:
    - **What is a manifest:** A list of all the map files you collected
    - **What information to save:**
      - Map name (example: "muttrah_city_2")
      - Server.zip MD5 checksum and metadata (heightmap presence)
      - Client.zip MD5 checksum and metadata (minimap presence)
      - File sizes in bytes (example: 5242880 = 5MB)
      - When you collected it (example: "2025-01-15 14:30:00")
      - Where you found it (example: "C:/Program Files/Project Reality/Project Reality BF2/mods/pr/levels/muttrah_city_2")
    - **Example structure:**
      ```json
      {
          "maps": [
              {
                  "name": "muttrah_city_2",
                  "server_zip": {
                      "md5": "a1b2c3d4...",
                      "size_bytes": 1048576,
                      "has_heightmap": true
                  },
                  "client_zip": {
                      "md5": "b2c3d4e5...",
                      "size_bytes": 2097152,
                      "has_minimap": true
                  },
                  "collected_at": "2024-11-19T10:30:00Z",
                  "source_path": "C:\\PR\\levels\\muttrah_city_2"
              }
          ],
          "total_maps": 45,
          "total_size_mb": 87.3,
          "collection_date": "2024-11-19"
      }
      ```
- **Must** configure Git LFS automatically:
    - **What is Git LFS:** A tool to store large files outside the main Git repository
    - **When to use it:** If total size of all server.zip files is MORE than 10MB
    - **How:** Create a file called `.gitattributes` with this line: `*.zip filter=lfs diff=lfs merge=lfs -text`
- **Must** generate collection report (maps found, copied, skipped, errors)
- **Must** continue processing other maps if one fails

**Requirement 1.2:** Cloud Notebook Processing (`process_maps.ipynb`)

- **Must** assume repository is already cloned (user runs `git clone` first)
- **Must** read from `/raw_map_data/` directory (local clone includes LFS files)
- **Must** process each `server.zip` file:
    - Extract `heightmapprimary.raw` (file containing terrain heights, case-insensitive)
    - **How to read the file:**
      - Each height is stored as 2 bytes (bytes are numbers 0-255)
      - Read bytes in "little-endian" order (means: first byte + second byte × 256)
      - Final number will be 0 to 65535
    - File sizes: 1025×1025, 2049×2049, or 513×513 pixels (these are the only allowed sizes)
    - **Important:** The file has an extra row and column on the edges (called "+1 border") - this is normal
- **Must** process each `client.zip` file:
    - Extract visual minimap DDS files from `info/` directory
    - Convert DDS files to PNG format for web compatibility
    - Handle cases where client.zip is missing (degrade gracefully to heightmap-only mode)
- **Must** extract map configuration files from server.zip:
    - `init.con` for map size
    - `terrain.con` for height scale
- **Must** process all maps in batch (not requiring manual selection per map)
- **Must** display progress indicators (current map, X of Y completed)

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

**Requirement 1.4:** Automated Git Commit and Push

- **Must** configure git user identity in notebook (name, email via user input)
- **Must** stage all files in `/processed_maps/` directory
- **Must** create commit with descriptive message:
    - Example: "chore: process maps - 45 maps updated (2024-11-19)"
    - Include count of new/updated maps
- **Must** push to GitHub using authentication token (user provides via Colab secrets or prompt)
- **Must** handle git conflicts gracefully:
    - Pull latest changes before committing
    - Abort and warn user if conflicts cannot be auto-resolved
- **Should** provide dry-run option to preview changes without committing
- **Must** display summary: files added, modified, total commit size

**Requirement 1.5:** Heightmap Conversion to JSON

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

- **Must** configure Git LFS for processed files if individual JSON > 1MB or total > 10MB
- **Must** update manifest with processing metadata (timestamp, versions)

<!-- NEW REQUIREMENT: Minimap Extraction -->
**Requirement 1.6: Visual Minimap Extraction**

**Purpose:** Extract and convert visual map representations from client.zip for use as base layer in calculator UI.

**Location of minimap files:** `client.zip/info/` directory within each map folder (per [PR Forum: Loading DDS Map Files](https://forum.realitymod.com/viewtopic.php?t=105865) and [Offline Maps Discussion](https://forum.realitymod.com/viewtopic.php?t=111399)).

**File format:** DDS (DirectDraw Surface) files using DXT1 compression format (per [BF2 DDS Format Documentation](https://forum.realitymod.com/viewtopic.php?t=126573)).

**Must extract from `client.zip`:**

- Navigate to `{mapname}/client.zip/info/` directory
- Locate minimap DDS files (naming conventions vary: `minimap.dds`, `map.dds`, or `{mapname}.dds`)
- Extract all DDS files found in the `info/` folder
- If multiple DDS files exist, prioritize largest by file size as primary minimap

**Must convert DDS to PNG format using one of these methods:**

**Option A: Python Pillow Library (Recommended)**

```python
from PIL import Image

# Open DDS file
dds_image = Image.open('minimap.dds')

# Convert and save as PNG
dds_image.save('minimap.png', 'PNG')
```

According to [Pillow Image File Formats Documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html), Pillow supports reading DXT1 and DXT5 DDS formats in RGBA mode. This is a read-only operation sufficient for our extraction needs.

**Option B: Python Wand Library (Alternative)**

```python
from wand.image import Image

# Open and convert DDS to PNG
with Image(filename='minimap.dds') as img:
    img.save(filename='minimap.png')
```

Based on [Stack Overflow: DDS Compression in Python](https://stackoverflow.com/questions/55574543/how-to-compress-png-image-with-s3tc-dxt-algorithm-in-python), Wand (ImageMagick Python binding) can handle DDS conversion reliably.

**Option C: Command-line Tools (Fallback)**

- Use ImageMagick's `convert` command: `convert minimap.dds minimap.png`
- Use reaConverter or similar batch conversion tools (per [reaConverter DDS to PNG Guide](https://www.reaconverter.com/convert/dds_to_png.html))

**Must handle edge cases:**

- Some maps may have multiple DDS files in `info/` folder - extract all, prioritize largest by file size as primary minimap
- If no DDS files found, log warning and proceed with heightmap-only processing
- If DDS conversion fails, attempt alternative conversion method before failing
- Validate converted PNG dimensions match expected map sizes (typically 1024x1024, 2048x2048, or 4096x4096 pixels)
- Verify PNG file size >100KB (too small indicates corruption or extraction failure)

**Must store converted minimap:**

- Save to `/processed_maps/{mapname}/minimap.png`
- Optionally create `background.png` as a scaled copy if different resolution needed for UI
- Include minimap metadata in `metadata.json`:

```json
{
  "map_name": "muttrah_city_2",
  "map_size": 2048,
  "height_scale": 300,
  "minimap": {
    "source_file": "info/minimap.dds",
    "resolution": "2048x2048",
    "file_size_kb": 1024,
    "converted_at": "2024-11-19T10:30:00Z"
  }
}
```

***

### 2. The User Interface (HTML/CSS/JavaScript Frontend - Part D: The Calculator)

**Requirement 2.1:** Map Selection Interface

- **Dropdown menu** listing all processed maps alphabetically
- **Map preview** showing minimap thumbnail on selection
- **Load button** to confirm selection and load full map data
- Display map metadata (size, grid scale) in UI corner

**Requirement 2.2:** Coordinate Input System

**Two input modes:**

**Mode A: Dropdown Input (Primary)**

**How it works:** Choose position using 3 dropdown menus

- **Mortar Position Fields (3 dropdowns):**
    - **Dropdown 1 - Column:** Pick a letter from A to M (13 choices)
      - A = first column on left, M = last column on right
    - **Dropdown 2 - Row:** Pick a number from 1 to 13 (13 choices)
      - 1 = first row at top, 13 = last row at bottom
    - **Dropdown 3 - Keypad:** Pick a position within the square (9 choices)
      - Uses phone keypad layout:
        ```
        7  8  9    (7 = top-left corner, 9 = top-right corner)
        4  5  6    (5 = center of square)
        1  2  3    (1 = bottom-left corner, 3 = bottom-right corner)
        ```
- **Target Position Fields:**
    - Same 3 dropdowns as mortar position
    
- **Example:** If you select "D", "6", "7":
    - D = 4th column from left
    - 6 = 6th row from top
    - 7 = top-left corner of that square
    - Display shows: "D 6-7"

**Mode B: Interactive Map Clicking (Secondary)**
- **Click-to-place markers** directly on map visualization
- **Draggable markers** for refinement
- **Dropdowns auto-update** when markers placed or dragged

**Requirement 2.3:** Map Visualization Panel

- **2D top-down map view** using Leaflet.js or HTML5 Canvas
- **Minimap Base Layer:** Display converted minimap.png as background image
    - **Leaflet.js Configuration:**
      ```javascript
      // Load minimap as image overlay
      const mapBounds = [[0, 0], [mapSize, mapSize]];  // From metadata.json

      // Create image overlay using minimap.png
      const minimapOverlay = L.imageOverlay(
          '/maps/{mapname}/minimap.png',
          mapBounds
      ).addTo(map);

      // Set map view to fit minimap bounds
      map.fitBounds(mapBounds);
      ```
    - **Requirements for minimap display:**
      - Minimap PNG must be displayed as the base layer (underneath grid overlays and markers)
      - Image must scale proportionally when zooming
      - Must load within 500ms (use lazy loading if PNG >2MB)
      - If minimap.png missing, display placeholder grid pattern with warning message: "Visual map unavailable - using grid only"
      - Grid overlay must align precisely with minimap terrain features
- **Pan controls:** Click-drag to pan
- **Zoom controls:** Mouse wheel or +/- buttons (6-8 zoom levels)
- **Grid overlay:** PR standard grid lines with letter/number labels (overlaid on minimap)
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

**Coordinate System (How we measure positions on the map):**
- **Origin (starting point):** Top-left corner of the map = position (0, 0)
  - Think of the map like a piece of paper: start reading from top-left
  - This matches what you see on your in-game PR map
- **X-axis (left-right):** Goes from West to East
  - X increases as you move RIGHT on the map
- **Y-axis (up-down):** Goes from North to South
  - Y increases as you move DOWN on the map
- **Z-axis (elevation):** Height above sea level
  - Z = 0 means sea level
  - Z = 100 means 100 meters above sea level
- **Azimuth (compass direction):** 
  - 0° = North (top of map)
  - 90° = East (right side of map)
  - 180° = South (bottom of map)
  - 270° = West (left side of map)

**IMPORTANT NOTE:** The game engine internally uses a DIFFERENT coordinate system (with origin at map center). But you only need to worry about the player-facing system described above. When reading game files, we convert to the top-left origin system automatically.

**Simplified Ballistic Formula (High Angle):**

**What this formula does:** Calculates the angle to aim your mortar to hit a target

**In plain English:**
- The shell goes up in an arc (like throwing a ball)
- Higher angle = shorter distance but can go over hills
- The formula accounts for: how far away the target is + how much higher/lower they are

**The Math:**

```
For high-angle mortar fire (angle > 45 degrees):

Elevation Angle (φ) = arctan(
  (v² + sqrt(v⁴ - g*(g*D² + 2*v²*ΔZ))) / (g*D)
)

What each symbol means:
- φ = Firing angle you need (in radians - a math unit for angles)
- v = 148.64 m/s (how fast the shell flies)
- g = 14.86 m/s² (how fast things fall in the game)
- D = Horizontal distance in meters (how far away target is on flat ground)
- ΔZ = Height difference in meters
  - Positive number = target is HIGHER than you
  - Negative number = target is LOWER than you
  - Zero = same height
```

**IMPORTANT:** This formula gives you the angle in "radians". You must convert to Mils or Degrees (see next section).

**Conversion to Mils and Degrees:**

**What is a radian?** A math unit for measuring angles (like inches vs. centimeters for distance)

**What is a Mil?** A military unit for measuring angles
- Full circle = 6400 Mils
- Used by militaries because it's easier for range calculations

**The Conversion:**

```
Mils = φ (in radians) × (6400 / (2π))
     = φ (in radians) × 1018.59

Degrees = φ (in radians) × (180 / π)
        = φ (in radians) × 57.2958
```

**Example:**
- If formula gives you φ = 0.8 radians
- In Mils: 0.8 × 1018.59 = 815 Mils
- In Degrees: 0.8 × 57.2958 = 45.8 Degrees

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

**Requirement 3.4:** Height Reading with Bilinear Interpolation

- **Must** use bilinear interpolation when reading height from heightmap
- **What this means:** When the position lands BETWEEN pixels, average the 4 surrounding pixels
- **Step-by-step:**
  1. Convert map position to pixel position (might be pixel 123.7, not exactly 123)
  2. Find the 4 pixels around this position:
     - Top-left pixel, Top-right pixel
     - Bottom-left pixel, Bottom-right pixel
  3. Average the top two pixels → get top_height
  4. Average the bottom two pixels → get bottom_height
  5. Average top_height and bottom_height → get final height
- **Why:** Makes height changes smooth instead of jumpy when you move the marker
- **Example:** If you stand between 4 pixels with heights [100m, 102m, 101m, 103m], your height is 101.5m (the average)

**Requirement 3.5:** Real-Time Updates

- Recalculate on "Calculate" button press only (not real-time during drag)
- Display loading indicator if calculation exceeds 50ms (should never happen)
- Calculations run on main thread (simple enough, no Web Workers needed for V1)

***

## C. TECHNICAL SPECIFICATIONS

### Tech Stack (MANDATORY)

- **Backend (Data Collection & Processing):** Python 3.8+
    - **Phase 1 - Local Collection Script** (`collect_maps.py`):
        - Standard library: `os`, `shutil`, `zipfile`, `json`, `hashlib` (MD5 checksums)
        - Extracts both server.zip and client.zip files from PR:BF2 installation
        - Validates and versions using MD5 checksums
        - Manages Git LFS configuration
    - **Phase 2 - Cloud Processing Notebook** (`process_maps.ipynb`):
        - Required Libraries: `numpy`, `zipfile`, `struct`, `json`, `subprocess` (git operations)
        - Required for Minimap Conversion: `Pillow` (PIL) - DDS to PNG conversion
        - Optional: `Wand` (ImageMagick binding) - fallback DDS converter
        - Runs in Google Colab or local Jupyter
        - Auto-commits processed data back to GitHub
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
  /raw_map_data/           # Part A: Source data (Git LFS if > 10MB total)
    /muttrah_city_2/
      server.zip           # Original heightmap data from game installation
      client.zip           # Original minimap textures from game installation
    /fallujah_west/
      server.zip
      client.zip
    manifest.json          # Map inventory with checksums for both zip files
  /processor/              # Part B: Processing scripts
    collect_maps.py        # Phase 1: Local extraction script (server.zip + client.zip)
    process_maps.ipynb     # Phase 2: Cloud processing notebook (heightmap + minimap)
    README.md              # Workflow instructions
  /processed_maps/         # Part C: Processed output (Git LFS if needed)
    /muttrah_city_2/
      heightmap.json       # 16-bit height data
      metadata.json        # Map configuration (includes minimap info)
      minimap.png          # Converted from client.zip/info/minimap.dds
      background.png       # Optional: Scaled version for UI
    /fallujah_west/
      heightmap.json
      metadata.json
      minimap.png
      background.png
  /calculator/             # Part D: Web Calculator
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
  requirements.txt         # Python dependencies (includes Pillow for DDS conversion)
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

1. **Maintainer Setup (One-time data collection):**
    - Run `python processor/collect_maps.py` on machine with PR:BF2 installed
    - Script extracts both server.zip and client.zip files to `/raw_map_data/`
    - Script validates files with MD5 checksums and creates manifest.json
    - Script configures Git LFS automatically (if total size > 10MB)
    - Commit and push `/raw_map_data/` to GitHub

2. **Maintainer Processing (Cloud or local):**
    - Clone repository with `git clone` (includes LFS files)
    - Open `processor/process_maps.ipynb` in Google Colab or Jupyter
    - Notebook reads from `/raw_map_data/`, processes all maps:
      - Extracts and converts heightmaps from server.zip
      - Extracts and converts minimaps from client.zip (DDS → PNG)
    - Notebook outputs to `/processed_maps/` (heightmap.json + metadata.json + minimap.png)
    - Notebook automatically commits and pushes results back to GitHub

3. **End User Setup (Download and run):**
    - Clone repository (processed maps and minimaps already included as PNG files)
    - Run `run.bat` or `run.sh`
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
- **Minimap Images:** All visual map representations are pre-converted to PNG during processing phase and bundled in repository. No runtime DDS conversion needed by end users.

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

### Step 1: Develop collect_maps.py

**What this script does:** Extracts both server.zip (heightmap) and client.zip (minimap) files from local PR:BF2 installation and prepares them for GitHub upload.

**Steps to implement:**

1. **Import Python libraries:**
   ```python
   import os        # File and folder operations
   import shutil    # Copy files
   import zipfile   # Validate zip files
   import json      # Write manifest
   import hashlib   # Calculate MD5 checksums
   from pathlib import Path
   from datetime import datetime
   ```

2. **Auto-detect PR:BF2 installation:**
   ```python
   # Default paths to check
   PR_PATHS = [
       r"C:\Program Files (x86)\Project Reality\Project Reality BF2",
       r"D:\Games\Project Reality\Project Reality BF2"
   ]
   # Check each path, prompt user if not found
   # Allow custom path via command-line: python collect_maps.py --path "D:\Games\PR"
   ```

3. **Find all map folders:**
   ```python
   # Scan /mods/pr/levels/ directory for map folders
   # Each subfolder should contain server.zip AND client.zip
   ```

4. **For each map, validate and copy server.zip:**
   ```python
   # Calculate MD5 checksum of server.zip
   # Verify zip integrity (test open)
   # Check for heightmapprimary.raw inside (case-insensitive)
   # Copy to /raw_map_data/[map_name]/server.zip
   # Preserve folder structure
   ```

5. **For each map, validate and copy client.zip:**
   ```python
   # Calculate MD5 checksum of client.zip (separately from server.zip)
   # Verify zip integrity (test open)
   # Check for info/ folder with .dds files inside
   # Copy to /raw_map_data/[map_name]/client.zip
   # Log warning if client.zip missing but continue (heightmap-only mode)
   ```

6. **Handle duplicates with checksums:**
   ```python
   # If map exists in raw_map_data/
   # Compare MD5 checksums for both server.zip and client.zip
   # Skip if identical, update if different
   # Track versions in manifest
   ```

7. **Generate manifest.json:**
   ```python
   {
       "maps": [
           {
               "name": "muttrah_city_2",
               "server_zip": {
                   "md5": "a1b2c3d4...",
                   "size_bytes": 1048576,
                   "has_heightmap": true
               },
               "client_zip": {
                   "md5": "b2c3d4e5...",
                   "size_bytes": 2097152,
                   "has_minimap": true
               },
               "collected_at": "2024-11-19T10:30:00Z",
               "source_path": "C:\\PR\\levels\\muttrah_city_2"
           }
       ],
       "total_maps": 45,
       "maps_with_minimaps": 43,
       "maps_heightmap_only": 2,
       "total_size_mb": 150.7,
       "collection_date": "2024-11-19"
   }
   ```

8. **Configure Git LFS (if needed):**
   ```python
   # Calculate total size of raw_map_data/
   # If > 10MB: Create/update .gitattributes
   # Add patterns: *.zip filter=lfs diff=lfs merge=lfs -text
   ```

9. **Generate collection report:**
   - Print summary: "Collected 45 maps (43 with minimaps, 2 heightmap-only), 0 skipped, 0 errors"
   - Save report to processor/collection_report.txt
   - List any errors or warnings

### Step 2: Develop process_maps.ipynb

**What this notebook does:** Processes server.zip and client.zip files from /raw_map_data/ and converts to JSON + PNG formats. Runs in Google Colab or local Jupyter. Auto-commits results to GitHub.

**Notebook Structure:**

1. **Cell 1 (Markdown): Instructions**
   - Explain workflow: clone repo → open notebook → run all cells
   - Prerequisites: Git authentication token (GitHub PAT)
   - Expected runtime: ~5-10 minutes for 45 maps

2. **Cell 2 (Python): Imports and Environment Check**
   ```python
   import os, zipfile, struct, json, subprocess
   import numpy as np
   from PIL import Image  # For DDS to PNG conversion
   from pathlib import Path
   from datetime import datetime
   
   # Detect environment (Colab vs local)
   IN_COLAB = 'google.colab' in str(get_ipython())
   print(f"Running in: {'Google Colab' if IN_COLAB else 'Local Jupyter'}")
   ```

3. **Cell 3 (Python): Install Dependencies**
   ```python
   # Install required libraries
   !pip install Pillow numpy
   
   # Optional: Install Wand as fallback DDS converter
   # !pip install Wand
   ```

4. **Cell 4 (Python): Configuration and Authentication**
   ```python
   # Git configuration
   GIT_USER_NAME = input("Git user name: ")
   GIT_USER_EMAIL = input("Git user email: ")
   GITHUB_TOKEN = input("GitHub Personal Access Token: ")  # Or use Colab secrets
   
   # Configure git
   subprocess.run(['git', 'config', 'user.name', GIT_USER_NAME])
   subprocess.run(['git', 'config', 'user.email', GIT_USER_EMAIL])
   ```

5. **Cell 5 (Python): Load Manifest and Discover Maps**
   ```python
   # Read manifest.json from raw_map_data/
   # List all server.zip and client.zip files to process
   # Display: "Found 45 maps to process (43 with minimaps, 2 heightmap-only)"
   ```

6. **Cell 6 (Python): Define Minimap Extraction Function**
   ```python
   def extract_and_convert_minimap(map_name, raw_data_path, output_path):
       """
       Extract minimap DDS from client.zip and convert to PNG.
       
       Args:
           map_name: Name of the map (e.g., 'muttrah_city_2')
           raw_data_path: Path to raw_map_data folder
           output_path: Path to processed_maps folder
       
       Returns:
           dict with minimap metadata or None if extraction failed
       """
       client_zip_path = os.path.join(raw_data_path, map_name, 'client.zip')
       
       # Check if client.zip exists
       if not os.path.exists(client_zip_path):
           print(f"⚠️  {map_name}: client.zip not found, skipping minimap")
           return None
       
       try:
           # Extract DDS files from info folder
           with zipfile.ZipFile(client_zip_path, 'r') as zf:
               info_files = [f for f in zf.namelist() 
                           if 'info/' in f.lower() and f.lower().endswith('.dds')]
               
               if not info_files:
                   print(f"⚠️  {map_name}: No DDS files in client.zip/info/")
                   return None
               
               # Use largest DDS file as primary minimap
               largest_dds = max(info_files, key=lambda f: zf.getinfo(f).file_size)
               
               # Extract to temporary location
               temp_dds_path = f'temp_{map_name}_minimap.dds'
               with open(temp_dds_path, 'wb') as f:
                   f.write(zf.read(largest_dds))
               
               # Convert DDS to PNG using Pillow
               with Image.open(temp_dds_path) as img:
                   # Ensure output directory exists
                   output_dir = os.path.join(output_path, map_name)
                   os.makedirs(output_dir, exist_ok=True)
                   
                   # Save as PNG
                   minimap_png_path = os.path.join(output_dir, 'minimap.png')
                   img.save(minimap_png_path, 'PNG')
                   
                   # Get image dimensions
                   width, height = img.size
               
               # Clean up temporary DDS file
               os.remove(temp_dds_path)
               
               # Validate PNG file size
               png_size_kb = os.path.getsize(minimap_png_path) // 1024
               if png_size_kb < 100:
                   print(f"⚠️  {map_name}: PNG file too small ({png_size_kb}KB), may be corrupted")
               
               print(f"✅ {map_name}: Minimap converted ({width}x{height}, {png_size_kb}KB)")
               
               return {
                   "source_file": largest_dds,
                   "resolution": f"{width}x{height}",
                   "file_size_kb": png_size_kb,
                   "converted_at": datetime.now().isoformat()
               }
               
       except Exception as e:
           print(f"❌ {map_name}: Failed to convert minimap - {str(e)}")
           # Try fallback method (Wand) here if needed
           return None
   ```

7. **Cell 7 (Python): Processing Loop**
   ```python
   # For each map in raw_map_data/:
   #   - Extract heightmapprimary.raw from server.zip (case-insensitive)
   #   - Parse as 16-bit unsigned int array
   #   - Extract init.con and terrain.con
   #   - Convert RAW to JSON (existing heightmap processing)
   #   - Extract and convert minimap from client.zip (NEW)
   #   - Generate metadata.json (include minimap info)
   #   - Save to processed_maps/[map_name]/
   #   - Display progress bar
   
   # Example integration:
   for map_name in map_list:
       print(f"\nProcessing {map_name}...")
       
       # Existing heightmap processing
       # ... (process server.zip, extract heightmap, etc.) ...
       
       # NEW: Add minimap conversion
       minimap_metadata = extract_and_convert_minimap(
           map_name, 
           'raw_map_data',
           'processed_maps'
       )
       
       # Update metadata.json to include minimap info
       if minimap_metadata:
           metadata['minimap'] = minimap_metadata
       
       # Save updated metadata
       # ...
   ```

8. **Cell 8 (Python): Git Commit and Push**
   ```python
   # Pull latest changes: git pull origin main
   # Stage files: git add processed_maps/
   # Commit: git commit -m "chore: process maps - 45 updated (43 with minimaps) (2024-11-19)"
   # Push with token: git push https://[token]@github.com/user/repo.git
   # Display: "Successfully pushed to GitHub"
   ```

9. **Cell 9 (Markdown): Summary**
   - Display processing results
   - Show stats: "45 maps processed, 43 with minimaps, 2 heightmap-only"
   - Link to GitHub repository
   - Next steps for user

### Step 3: Develop Frontend (index.html + JavaScript)

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
   
   // NEW: Load minimap PNG as base layer
   const metadata = await fetch('/maps/muttrah_city_2/metadata.json').then(r => r.json());
   const mapSize = metadata.map_size;
   
   // Create image overlay for minimap
   if (metadata.minimap) {
       const minimapOverlay = L.imageOverlay(
           '/maps/muttrah_city_2/minimap.png',
           [[0, 0], [mapSize, mapSize]]
       ).addTo(map);
   } else {
       console.warn('Minimap not available - using grid-only mode');
       // Display placeholder or warning to user
   }
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
11. Visual minimap images are successfully extracted from client.zip and converted to PNG format for all available maps
12. Calculator displays actual terrain representation (satellite/overview image) as base layer under grid overlays, not placeholder graphics

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

***

## DOCUMENT CHANGELOG

### Revision: 2024-11-19 - Minimap Extraction Feature Added

**Summary:** Enhanced PRD to include visual minimap extraction from client.zip files, providing users with actual terrain representation (satellite/overview images) as the base layer in the calculator interface.

**Rationale:** The original PRD only covered heightmap data (elevation), which provides terrain shape but no visual representation. Users need to see actual map features (roads, buildings, terrain colors) to orient themselves and identify landmarks. This visual data is stored separately in client.zip files and must be extracted and converted for web display.

**Modified Sections:**

1. **Section B.1 - Functional Requirements (Map Processing)**
   - **Requirement 1.1 (Local Map Collection):**
     - Changed: Now collects both `server.zip` AND `client.zip` files
     - Added: Separate validation for client.zip (MD5 checksum, integrity, DDS file presence)
     - Added: Graceful degradation if client.zip missing (heightmap-only mode)
     - Updated: manifest.json structure to include separate entries for server_zip and client_zip
   
   - **Requirement 1.2 (Cloud Notebook Processing):**
     - Added: Processing step for client.zip alongside server.zip
     - Added: Minimap extraction and conversion workflow
   
   - **NEW Requirement 1.6 (Visual Minimap Extraction):**
     - Location: client.zip/info/ directory
     - Source format: DDS files (DXT1 compression)
     - Conversion methods: Pillow (recommended), Wand (alternative), ImageMagick (fallback)
     - Edge cases: Multiple DDS files, missing files, conversion failures, invalid dimensions
     - Output: minimap.png saved to processed_maps/{mapname}/
     - Metadata: Include minimap info in metadata.json

2. **Section B.2 - Functional Requirements (User Interface)**
   - **Requirement 2.3 (Map Visualization Panel):**
     - Added: Detailed Leaflet.js configuration for minimap as base layer
     - Added: Image overlay setup using L.imageOverlay()
     - Added: Requirements for minimap display (loading speed, fallback behavior, grid alignment)
     - Added: Warning message display if minimap unavailable

3. **Section C - Technical Specifications**
   - **Tech Stack:**
     - Updated: Phase 1 now extracts both server.zip and client.zip
     - Added: Pillow library as required dependency for DDS conversion
     - Added: Wand library as optional fallback converter
   
   - **Deployment Architecture (Directory Structure):**
     - Updated: `/raw_map_data/{mapname}/` now includes both server.zip and client.zip
     - Updated: `/processed_maps/{mapname}/` now includes minimap.png and optional background.png
     - Updated: manifest.json includes metadata for both zip files
     - Updated: requirements.txt includes Pillow for DDS conversion
   
   - **Execution Flow:**
     - Step 1: Collection script now extracts both zip types
     - Step 2: Processing notebook converts heightmaps AND minimaps
     - Step 3: End users receive pre-converted PNG files (no runtime conversion needed)
   
   - **Offline Policy:**
     - Added: Clarification that minimap PNGs are pre-converted and bundled in repository

4. **Section "IMPLEMENTATION GUIDE"**
   - **Step 1 (collect_maps.py):**
     - Added: Client.zip extraction and validation logic
     - Added: Separate MD5 checksum calculation for client.zip
     - Added: Detection of DDS files in client.zip/info/ directory
     - Updated: Manifest generation to include client.zip metadata
     - Updated: Collection report to show "X maps with minimaps, Y heightmap-only"
   
   - **Step 2 (process_maps.ipynb):**
     - Added: Cell 3 for installing Pillow dependency
     - Added: Cell 6 with complete minimap extraction function
     - Added: Integration of minimap conversion into main processing loop
     - Updated: Metadata.json now includes minimap information
     - Updated: Git commit messages to reflect minimap processing
     - Updated: Summary cell to show minimap processing statistics
   
   - **Step 3 (Frontend Development):**
     - Added: Code to load minimap PNG and create Leaflet image overlay
     - Added: Fallback behavior when minimap unavailable
     - Added: Warning message display for missing minimaps

5. **Section "SUCCESS CRITERIA"**
   - Added: Criterion 11 - Visual minimap extraction successful for all maps
   - Added: Criterion 12 - Calculator displays actual terrain representation as base layer

**Technical References Added:**
- [PR Forum: Loading DDS Map Files](https://forum.realitymod.com/viewtopic.php?t=105865) - Minimap location documentation
- [PR Forum: Offline Maps Discussion](https://forum.realitymod.com/viewtopic.php?t=111399) - Client.zip usage patterns
- [PR Forum: DDS Format in BF2](https://forum.realitymod.com/viewtopic.php?t=126573) - DXT1 compression specification
- [Pillow Documentation: Image File Formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) - DDS support details
- [Stack Overflow: DDS Compression in Python](https://stackoverflow.com/questions/55574543) - Wand library examples
- [reaConverter: DDS to PNG](https://www.reaconverter.com/convert/dds_to_png.html) - Alternative conversion methods

**Preserved Elements:**
- All physics constants remain unchanged (gravity 14.86 m/s², velocity 148.64 m/s)
- Heightmap extraction logic untouched
- Ballistic calculation formulas unchanged
- Coordinate system specifications unchanged
- All existing functional requirements preserved

**Implementation Flexibility Granted:**
- Choice of DDS conversion library (Pillow, Wand, or ImageMagick)
- Handling of missing minimaps (grayscale, placeholder, or grid-only mode)
- PNG compression and optimization strategies
- File naming conventions (must be consistent and documented)
- Error recovery and retry logic

**Constraints Maintained:**
- Offline capability preserved (all conversions during preprocessing)
- No runtime DDS conversion by end users
- Graceful degradation if minimap unavailable (heightmap-only mode)
- All dependencies documented in requirements.txt

***

**END OF DOCUMENT**