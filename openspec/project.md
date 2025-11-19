# Project Context

## Purpose

**What this tool does:**
This is a calculator for Project Reality: BF2 video game. It helps mortar crews aim their mortars accurately.

**Why it exists:**
In the game, mortars need to account for:
- Distance to target (how far away)
- Direction to target (which way to point)
- Height difference (target higher or lower than mortar)

This calculator does the math so players can hit their targets.

**Key Goals:**
- Calculate accurate firing angles (within 1 Mil of game behavior)
- Work without internet connection
- Start in less than 3 seconds when user clicks run.bat
- Support all Project Reality maps

## Tech Stack

**What is a "tech stack"?** The programming languages and tools used to build this project.

### Backend (Python 3.8 or newer)

**What is "backend"?** The server that sends files to your web browser.

- **Flask version 2.3 or newer** - A simple Python web server
  - Purpose: Send HTML, CSS, JavaScript, and JSON files to browser
  - Does NOT do calculations (browser does all the math)
  
- **NumPy** - A Python library for working with arrays of numbers
  - Purpose: Read and process heightmap data (elevation maps)
  
- **Standard Python Libraries:**
  - `zipfile` - Open compressed .zip files
  - `struct` - Read binary files (files with raw numbers)
  - `json` - Read and write JSON files (text files with structured data)

### Frontend (JavaScript in your web browser)

**What is "frontend"?** The code that runs in your web browser.

- **Leaflet.js version 1.9 or newer** - A map display library
  - Shows the game map on your screen
  - Must be downloaded and saved in project folder (do NOT use internet links)
  
- **HTML5** - Creates the structure of the web page
  - No frameworks (just plain HTML)
  
- **CSS3** - Makes the web page look nice
  - Uses Flexbox and Grid for layout (modern CSS features)
  - Uses BEM naming (a way to organize CSS class names)
  
- **Vanilla JavaScript** - Plain JavaScript without any frameworks
  - ES6 or newer (modern JavaScript features like arrow functions)

### Data Format

**What format is the map data?**

- **Input:** 16-bit RAW heightmaps (binary files from game)
- **Output:** JSON files (text files that store numbers in arrays)
- **Why JSON?** Keeps all precision (0 to 65535 range) without losing data

## Code Style Rules

**Why do we have code style rules?** So all code looks similar and is easy to read.

### Python Code Style

**Indentation:** Use 4 spaces (not tabs)

**Naming:**
- Functions and variables: `snake_case` (words separated by underscores)
  - Example: `get_elevation`, `height_scale`, `map_size`
- Classes: `PascalCase` (capitalize first letter of each word)
  - Example: `HeightmapProcessor`, `MapMetadata`

**Type Hints:** Tell Python what type of data a function expects
```python
def get_elevation(x: float, y: float) -> float:
    # This function takes two decimal numbers and returns a decimal number
    return elevation
```

**Comments (Docstrings):** Describe what functions do
```python
def calculate_distance(x1, y1, x2, y2):
    """Calculate distance between two points.
    
    Args:
        x1, y1: First point coordinates in meters
        x2, y2: Second point coordinates in meters
    
    Returns:
        Distance in meters as a decimal number
    """
```

### JavaScript Code Style

**Indentation:** Use 2 spaces (not tabs)

**Naming:**
- Functions and variables: `camelCase` (first word lowercase, rest capitalized)
  - Example: `calculateDistance`, `heightScale`, `mapSize`
- Classes: `PascalCase`
  - Example: `FiringSolution`, `CoordinateConverter`

**Variable Declaration:**
- Use `const` by default (value cannot change)
- Use `let` only when value needs to change
- NEVER use `var` (old JavaScript style)

**Functions:**
- Arrow functions for short callbacks: `array.map(x => x * 2)`
- Named functions for main logic: `function calculateElevation() { ... }`

**Comments (JSDoc):** Describe what functions do
```javascript
/**
 * Calculate firing solution for given positions
 * @param {Object} mortar - Mortar position with x, y, z properties
 * @param {Object} target - Target position with x, y, z properties
 * @returns {Object} Solution with azimuth, elevation, distance
 */
function calculateFiringSolution(mortar, target) {
  // Function code here
}
```

### CSS Code Style

**Naming (BEM - Block Element Modifier):**

- Block: Main component
  - Example: `.calculator-panel`
  
- Element: Part of a block (use double underscore)
  - Example: `.calculator-panel__input`
  
- Modifier: Variation of block or element (use double dash)
  - Example: `.calculator-panel__input--disabled`

**Why BEM?** Makes it clear which CSS rules apply to which HTML elements.

**Mobile First:** Write CSS for phones first, then add rules for bigger screens
```css
/* Base styles for small screens */
.calculator-panel {
  width: 100%;
}

/* Larger screens */
@media (min-width: 768px) {
  .calculator-panel {
    width: 50%;
  }
}
```

### Architecture Patterns

**Modular JavaScript (No Bundler for V1):**
- Pure functions in `ballistics.js` (no side effects, testable)
- Coordinate conversion in `coordinates.js` (grid ↔ world)
- Height sampling in `heightmap.js` (bilinear interpolation)
- UI logic in `ui.js` (DOM manipulation only)
- Main orchestration in `app.js`

**Separation of Concerns:**
- **Data Layer:** JSON files (heightmaps, metadata)
- **Logic Layer:** JavaScript modules (calculations, conversions)
- **Presentation Layer:** HTML/CSS (no inline styles, no JS in HTML except module loading)

**Array-Ready Design (V1 uses single items, V2+ expands to arrays):**
```javascript
// V1: Function accepts single objects
calculateFiringSolution(mortar, target) { ... }

// V2+: Trivial to map over arrays
mortars.map(m => targets.map(t => calculateFiringSolution(m, t)))
```

### Testing Strategy

**V1 - Manual In-Game Validation:**
- **Korengal Valley** - Extreme elevation differences (300-500m)
- **Vadso City** - Long range + elevation (1200m+)
- **Burning Sands** - Flat terrain control test

**Validation Protocol:**
1. Place mortar/target in-game at known grid coordinates
2. Input same coordinates in calculator
3. Use calculated solution in-game
4. Measure impact distance from target
5. **Acceptance:** Impact within 50m (2× mortar spread radius)

**V2+ - Automated Unit Tests:**
- Grid coordinate parser edge cases
- Bilinear interpolation accuracy
- Ballistic formula against known solutions (test vectors)
- Boundary condition handling

### Git Workflow

**Branching Strategy:**
- `main` - Stable releases only
- `dev` - Integration branch for features
- `feature/[name]` - Individual features (e.g., `feature/add-tof-display`)
- `fix/[issue]` - Bug fixes

**Commit Conventions (Conventional Commits):**
- `feat: Add time-of-flight calculation`
- `fix: Correct heightmap border handling`
- `docs: Update PRD with testing strategy`
- `refactor: Modularize coordinate conversion`
- `test: Add Korengal validation test data`

**OpenSpec Change Workflow:**
1. Create change proposal in `openspec/changes/[change-id]/`
2. Implement changes per `tasks.md`
3. Validate with `openspec validate --strict`
4. After deployment, archive with `openspec archive [change-id]`

## Understanding Project Reality Game Mechanics

**What is Project Reality?** A military simulation game where physics works differently than real life.

### Important Physics Numbers (DO NOT CHANGE THESE)

**Gravity: 14.86 meters per second squared**
- In real life, Earth gravity is 9.8
- In Project Reality game, gravity is 14.86
- Use 14.86, NOT 9.8

**Mortar Shell Speed: 148.64 meters per second**
- This is how fast the shell leaves the mortar
- Do NOT change this number

**Maximum Range: 1500 meters**
- Mortar cannot shoot farther than this
- This is a game balance limit

**Mortar Accuracy: About 30 meters**
- Even with perfect calculations, shells land within 30 meter circle
- This is normal game behavior

### Coordinate System (How to measure positions)

**Where is the origin (0, 0)?**
- Top-left corner of the map (Northwest corner)
- NOT the center of the map
- NOT the bottom-left corner

**Which direction do the axes point?**
- X-axis: Left to right (West to East)
  - X increases as you go right
  - X = 0 is the left edge
  
- Y-axis: Top to bottom (North to South)
  - Y increases as you go down
  - Y = 0 is the top edge
  
- Z-axis: Up and down (elevation)
  - Z increases as you go up
  - Z = 0 is sea level

**Azimuth (direction):**
- 0 degrees = North (up)
- 90 degrees = East (right)
- 180 degrees = South (down)
- 270 degrees = West (left)

**Important Note:** The game engine uses center origin internally, but players see maps with top-left origin. This calculator uses top-left origin to match what players see.

### Grid System (How to describe positions)

**What is the grid system?** A way to describe map locations using letters and numbers (like a chess board).

**Grid Structure:**
- 13 columns (vertical lines) labeled A through M
- 13 rows (horizontal lines) labeled 1 through 13
- This creates 169 squares (13 × 13 = 169)

**Subgrid (Keypad):**
- Each square is divided into 9 smaller squares
- Numbered like a phone keypad:
  ```
  7  8  9    (top row)
  4  5  6    (middle row)
  1  2  3    (bottom row)
  ```
- 5 is always the center
- 7 is top-left corner
- 3 is bottom-right corner

**Example Grid Reference:**
- "D6-7" means:
  - Column D (4th column from left)
  - Row 6 (6th row from top)
  - Keypad 7 (top-left of that square)

**Grid Square Size (depends on map):**
- 1 kilometer maps: Each square is 75 meters
- 2 kilometer maps: Each square is 150 meters
- 4 kilometer maps: Each square is 300 meters

### Heightmap Data (Elevation Information)

**What is a heightmap?** An image file that stores elevation (height) data. Dark pixels = low ground, bright pixels = high ground.

**Technical Details:**

**File Format:**
- Type: 16-bit grayscale RAW file
- Values: Each pixel stores a number from 0 to 65535
- Storage: Inside `server.zip` file, named `HeightmapPrimary.raw`
- Byte Order: Little-endian (Intel PC format)

**Image Size:**
- 2 kilometer maps: 1025 × 1025 pixels
- 4 kilometer maps: 2049 × 2049 pixels
- Includes extra 1 pixel border (game uses this for terrain smoothing)

**How to Calculate Elevation:**

```
elevation_in_meters = (pixel_value / 65535.0) * height_scale
```

**What each variable means:**
- `pixel_value` = The number from the heightmap (0 to 65535)
- `65535` = Maximum value for 16-bit number (do NOT change)
- `height_scale` = Maximum height of map in meters (from terrain.con file)
- `elevation_in_meters` = Final height above sea level

**Example:**
- Pixel value: 32768 (middle gray)
- Height scale: 300 meters (from terrain.con)
- Calculation: 32768 / 65535 = 0.5
- Result: 0.5 × 300 = 150 meters elevation

**Color Meanings:**
- Black pixel (value 0) = Sea level (0 meters)
- White pixel (value 65535) = Maximum height (height_scale value)
- Gray pixel (value 32768) = Half of maximum height

**Height Scale Values (from terrain.con file):**
- Typical: 100 to 500 meters
- Maximum ever used: 1000 meters
- Flat maps (deserts): 100-200 meters
- Mountain maps: 400-1000 meters

**Precision:**
- 65536 different height levels (because 16-bit = 2^16 = 65536)
- With 300m height scale: 300 ÷ 65536 = 0.0046 meters = 4.6 millimeters per level
- With bilinear interpolation: About 5 centimeters effective precision
- Mortar spread is 30 meters, so this precision is more than enough

### Ballistic Calculations (Mortar Physics)

**What is a ballistic calculation?** Math to figure out what angle to aim the mortar.

**High-Angle Firing (Most Common):**

Mortars usually fire at steep angles (more than 45 degrees up). This formula calculates the angle:

```
φ = arctan((v² + sqrt(v⁴ - g*(g*D² + 2*v²*ΔZ))) / (g*D))
```

**What each variable means:**
- `φ` (phi) = Elevation angle we need to find (in radians)
- `v` = 148.64 (mortar shell speed in meters per second)
- `g` = 14.86 (game gravity in meters per second squared)
- `D` = Horizontal distance to target (in meters)
  - Calculate: `D = sqrt((x2-x1)² + (y2-y1)²)`
- `ΔZ` (delta Z) = Height difference (in meters)
  - Calculate: `ΔZ = target_height - mortar_height`
  - Positive number = target is higher
  - Negative number = target is lower

**How to Calculate Distance (D):**
```
D = sqrt((x2 - x1)² + (y2 - y1)²)
```
- `x1, y1` = Mortar position
- `x2, y2` = Target position
- `sqrt` = Square root

**Angular Units (Ways to Measure Angles):**

**Mils (Primary unit):**
- Military standard for artillery
- One full circle = 6400 mils
- Convert from radians: `mils = radians × (6400 / (2 × π))`
- Convert from radians: `mils = radians × 1018.59`

**Degrees (Secondary unit):**
- Normal angle measurement
- One full circle = 360 degrees
- Convert from radians: `degrees = radians × (180 / π)`
- Convert from radians: `degrees = radians × 57.2958`

**Example Conversion:**
- If φ = 1.22 radians
- Mils: 1.22 × 1018.59 = 1243 mils
- Degrees: 1.22 × 57.2958 = 69.9 degrees

## Important Constraints

### Offline Operation (MANDATORY)
- Zero external API calls (no CDN, no telemetry)
- All dependencies bundled locally
- Entire tool folder is portable (USB-friendly)
- No internet connection required

### Performance Targets
- Map load time: <500ms per map
- Calculation time: <50ms per solution
- Startup time: <3 seconds from `run.bat` double-click

### Compatibility
- Windows 10+ (primary), Linux/Mac (secondary via `run.sh`)
- Python 3.8+ (widely available)
- Modern browsers (Chrome 90+, Firefox 88+, Edge 90+)
- No mobile support required for V1

### Data Constraints
- Heightmap JSON files: 2-10MB each (uncompressed), 20-50 maps → ~500MB total
- Processed maps bundled in repository (users can extend via processor)
- Git LFS not required (JSON is text, compresses well)

## External Dependencies

### Zero External Services
- No APIs, no authentication, no cloud storage
- Tool is 100% self-contained

### Local Game Installation (Optional)
- **PR:BF2 Installation Path** (for processor only, not calculator):
  - Windows: `C:\Program Files (x86)\Project Reality\Project Reality BF2`
  - Custom paths supported via config
- **Required Files:**
  - `/levels/[map_name]/server.zip` (contains HeightmapPrimary.raw)
  - `/levels/[map_name]/init.con` (map size)
  - `/levels/[map_name]/terrain.con` (height scale)

### Python Dependencies (requirements.txt)
```
Flask==2.3.3
numpy==1.24.3
Werkzeug==2.3.7
```

### JavaScript Dependencies (Bundled)
- Leaflet.js 1.9.4 (no external plugins)
- No npm, no webpack, no build process for V1

## Map Processing Notes

**One-Time Setup (Typically done by maintainer):**
1. Processor scans PR:BF2 installation
2. Extracts heightmaps from `server.zip` for all maps
3. Converts RAW → JSON (lossless)
4. Generates metadata.json (map_size, height_scale, grid_scale)
5. Outputs to `/processed_maps/[map_name]/`

**Users receive:**
- Pre-processed maps in repository
- Can run processor themselves for custom maps
- No need to own PR:BF2 to use calculator (maps bundled)

## Quick Reference

**Key Files:**
- `PRD.md` - Product Requirements Document (this is the bible)
- `openspec/AGENTS.md` - AI assistant instructions for OpenSpec workflow
- `openspec/project.md` - This file (project context)
- `processor/process_maps.py` - Heightmap extraction script
- `calculator/server.py` - Flask static file server
- `calculator/static/js/ballistics.js` - Core physics calculations

**Key Commands:**
```bash
# Run calculator
python calculator/server.py          # Manual start
./run.bat                             # Windows one-click
./run.sh                              # Linux/Mac one-click

# Process maps (one-time or when maps update)
python processor/process_maps.py

# OpenSpec workflow
openspec list                         # View active changes
openspec validate --strict            # Validate before implementation
openspec archive [change-id] --yes    # Archive after deployment
```

**Critical Physics Values (DO NOT CHANGE):**
```javascript
const PR_PHYSICS = {
  GRAVITY: 14.86,              // m/s² (PR engine value)
  PROJECTILE_VELOCITY: 148.64, // m/s (mortar shell)
  MAX_RANGE: 1500,             // meters
  MILS_PER_CIRCLE: 6400,
  DEGREES_PER_CIRCLE: 360
};
```
