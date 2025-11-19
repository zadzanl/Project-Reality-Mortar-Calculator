# Project Context

## Purpose

**What this tool does:**
This calculator helps players aim mortars in Project Reality: BF2 video game.

**Why it exists:**
Players need to calculate three things to hit targets with mortars:
- Distance to target (how far away)
- Direction to target (which way to point)
- Height difference (target higher or lower than mortar)

This tool does the math automatically.

**Key Goals:**
- Calculate firing angles that match game behavior (within 1 Mil)
- Work without internet connection
- Start in less than 3 seconds when user runs run.bat
- Support all Project Reality maps

## Tech Stack

**Tech stack** means: Which programming languages and tools we use.

### Backend (Python 3.8 or newer)

**Backend** means: The program that serves files to your web browser.

**Map Processing has two parts:**

**Phase 1 - Local Collection Script** (`collect_maps.py`):
- **Purpose:** Extract server.zip files from PR:BF2 installation
- **Libraries:** Standard library only (`os`, `shutil`, `zipfile`, `json`, `hashlib`)
- **Features:**
  - Auto-detect game installation
  - Validate files with MD5 checksums
  - Handle duplicates and versioning
  - Configure Git LFS automatically
  - Generate manifest.json

**Phase 2 - Cloud Processing Notebook** (`process_maps.ipynb`):
- **Format:** `.ipynb` notebook for cloud or local execution
- **Environments:** Google Colab (primary), local Jupyter (secondary)
- **Required Libraries:**
  - `numpy` - Array operations for heightmap processing
  - `zipfile` - Extract from server.zip
  - `struct` - Parse binary RAW heightmaps
  - `json` - Output JSON files
  - `subprocess` - Git operations (commit, push)
  - `PIL/Pillow` - Optional minimap generation

**Web Server (Python Script):**
- **Flask 2.3+** - Static file server
  - Purpose: Send HTML, CSS, JavaScript, and JSON files to browser
  - Does NOT do calculations (browser does all the math)

### Frontend (JavaScript in browser)

**Frontend** means the code that runs in your web browser.

**Required Libraries:**
- **Leaflet.js 1.9+** - Map display library
  - Shows game map on screen
  - Download and save in project folder (do NOT use internet links)
  
- **HTML5** - Creates web page structure
  - Use plain HTML (no frameworks)
  
- **CSS3** - Makes web page look nice
  - Use Flexbox and Grid for layout
  - Use BEM naming convention for CSS class names
  
- **Vanilla JavaScript** - Plain JavaScript (no frameworks)
  - Use ES6 or newer (modern JavaScript features)

### Data Format

**Map data storage:**
- **Input:** 16-bit RAW heightmaps (binary files from game)
- **Output:** JSON files (text files that store numbers)
- **Why JSON:** Keeps all precision (values from 0 to 65535) without losing data

## Code Style Rules

These rules make code look the same everywhere. This makes code easier to read.

### Python Code Style

**Indentation:** Press space bar 4 times (NOT tab key)

**Naming rules:**
- Functions and variables: `snake_case`
  - Words separated by underscores
  - Example: `get_elevation`, `height_scale`, `map_size`
  - All lowercase
  
- Classes: `PascalCase`
  - First letter of each word is capital
  - Example: `HeightmapProcessor`, `MapMetadata`
  - No underscores

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

**Indentation:** Press space bar 2 times (NOT tab key)

**Naming rules:**
- Functions and variables: `camelCase`
  - First word lowercase, other words start with capital
  - Example: `calculateDistance`, `heightScale`, `mapSize`
  
- Classes: `PascalCase`
  - First letter of each word is capital
  - Example: `FiringSolution`, `CoordinateConverter`

**Variable rules:**
- Use `const` for values that don't change
  - Example: `const PI = 3.14159`
  
- Use `let` for values that change
  - Example: `let counter = 0`
  
- NEVER use `var` (old JavaScript, don't use it)

**Functions:**
- Arrow functions for short operations: `array.map(x => x * 2)`
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

BEM makes it clear which CSS rules apply to which HTML elements.

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

**Two-Phase Map Processing:**

**Phase 1 - Collection Script Structure:**
- Function: `find_pr_installation()` - Auto-detect game path
- Function: `calculate_md5(file_path)` - Checksum validation
- Function: `copy_server_zip(src, dest)` - Copy with structure preservation
- Function: `generate_manifest(maps_data)` - Create inventory JSON
- Function: `configure_git_lfs(total_size)` - Auto-setup LFS if needed
- Single-file script, no external dependencies beyond stdlib

**Phase 2 - Notebook Structure:**
- Cell 1: Markdown instructions (workflow overview)
- Cell 2: Imports and environment detection
- Cell 3: Configuration (Git credentials)
- Cell 4: Map discovery (read manifest)
- Cell 5: Processing loop (extract, convert, save)
- Cell 6: Git automation (commit and push)
- Cell 7: Summary and results
- Progress indicators for user feedback

**Modular JavaScript (Calculator):**
- Pure functions in `ballistics.js` (no side effects, testable)
- Coordinate conversion in `coordinates.js` (grid to world coordinates)
- Height sampling in `heightmap.js` (bilinear interpolation)
- UI logic in `ui.js` (DOM manipulation only)
- Main orchestration in `app.js`

**Separation of Concerns:**
- **Data Layer:** JSON files (heightmaps, metadata)
- **Logic Layer:** JavaScript modules (calculations, conversions)
- **Presentation Layer:** HTML and CSS (no inline styles, no JavaScript in HTML except module loading)

**Array-Ready Design (V1 uses single items, V2 expands to arrays):**
```javascript
// V1: Function accepts single objects
calculateFiringSolution(mortar, target) { ... }

// V2: Easy to expand to arrays later
mortars.map(m => targets.map(t => calculateFiringSolution(m, t)))
```

### Testing Strategy

**V1 - Manual In-Game Validation:**

Test on these maps:
- **Korengal Valley** - Extreme elevation differences (300-500m)
- **Vadso City** - Long range with elevation (1200m and more)
- **Burning Sands** - Flat terrain control test

**Validation Protocol:**
1. Place mortar and target in game at known grid coordinates
2. Input same coordinates in calculator
3. Use calculated solution in game
4. Measure impact distance from target
5. **Acceptance:** Impact within 50m (2 times mortar spread radius)

**V2 - Automated Unit Tests:**
- Grid coordinate parser edge cases
- Bilinear interpolation accuracy
- Ballistic formula against known solutions (test vectors)
- Boundary condition handling

### Git Workflow

**Branching Strategy:**
- `main` - Stable releases only
- `dev` - Integration branch for features
- `feature/[name]` - Individual features (example: `feature/add-tof-display`)
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

**Project Reality** is a military simulation game where physics works differently than real life.

### Important Physics Numbers (DO NOT CHANGE THESE)

**Gravity: 14.86 meters per second squared**
- In real life, Earth gravity is 9.8
- In Project Reality game, gravity is 14.86
- Always use 14.86, NOT 9.8

**Mortar Shell Speed: 148.64 meters per second**
- This is how fast the shell leaves the mortar
- Do NOT change this number

**Maximum Range: 1500 meters**
- Mortar cannot shoot farther than this
- This is a game balance limit

**Mortar Accuracy: About 30 meters**
- Even with perfect calculations, shells land within 30 meter circle
- This is normal game behavior

### Coordinate System (How to measure positions on the map)

**Origin point (0, 0) is in the top-left corner:**
- Like reading a book: start at top-left
- NOT in the center
- NOT in the bottom-left

**Three axes (directions):**

1. **X-axis:** Left to right (West to East)
   - X = 0 at left edge
   - X increases going right
   - Think: reading left to right

2. **Y-axis:** Top to bottom (North to South)
   - Y = 0 at top edge
   - Y increases going down
   - Think: reading top to bottom

3. **Z-axis:** Up and down (elevation/height)
   - Z = 0 at sea level
   - Z increases going up
   - Think: climbing a mountain

**Direction (Azimuth):**
- 0 degrees = North (straight up)
- 90 degrees = East (right)
- 180 degrees = South (straight down)
- 270 degrees = West (left)

**Important:** The game uses a different system internally, but we use this simpler system to match what players see on their maps.

### Grid System (How to describe positions)

**Grid system** is a way to describe map locations using letters and numbers (like a chess board).

**Grid Structure:**
- 13 columns (vertical lines) labeled A through M
- 13 rows (horizontal lines) labeled 1 through 13
- This creates 169 squares (13 times 13 = 169)

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

**Heightmap** is an image file that stores elevation (height) data. Dark pixels = low ground, bright pixels = high ground.

**Technical Details:**

**File Format:**
- Type: 16-bit grayscale RAW file
- Values: Each pixel stores a number from 0 to 65535
- Storage: Inside `server.zip` file, named `HeightmapPrimary.raw`
- Byte Order: Little-endian (Intel PC format)

**Image Size:**
- 2 kilometer maps: 1025 by 1025 pixels
- 4 kilometer maps: 2049 by 2049 pixels
- Includes extra 1 pixel border (game uses this for terrain smoothing)

**How to Calculate Elevation:**

```
elevation_in_meters = (pixel_value / 65535.0) * height_scale
```

**Variable meanings:**
- `pixel_value` = The number from the heightmap (0 to 65535)
- `65535` = Maximum value for 16-bit number (do NOT change)
- `height_scale` = Maximum height of map in meters (from terrain.con file)
- `elevation_in_meters` = Final height above sea level

**Example:**
- Pixel value: 32768 (middle gray)
- Height scale: 300 meters (from terrain.con)
- Calculation: 32768 / 65535 = 0.5
- Result: 0.5 times 300 = 150 meters elevation

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
- 65536 different height levels (because 16-bit = 2 to the power of 16 = 65536)
- With 300m height scale: 300 divided by 65536 = 0.0046 meters = 4.6 millimeters per level
- With bilinear interpolation: About 5 centimeters effective precision
- Mortar spread is 30 meters, so this precision is more than enough

### Ballistic Calculations (Mortar Physics)

**Ballistic calculation** means math to figure out what angle to aim the mortar.

**High-Angle Firing (Most Common):**

Mortars usually fire at steep angles (more than 45 degrees up). This formula calculates the angle:

```
φ = arctan((v² + sqrt(v⁴ - g*(g*D² + 2*v²*ΔZ))) / (g*D))
```

**Variable meanings:**
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
- Mils: 1.22 times 1018.59 = 1243 mils
- Degrees: 1.22 times 57.2958 = 69.9 degrees

## Important Constraints

### Offline Operation (MANDATORY)
- Zero external API calls (no CDN, no telemetry)
- All dependencies bundled locally
- Entire tool folder is portable (can copy to USB drive)
- No internet connection required

### Performance Targets
- Map load time: less than 500ms per map
- Calculation time: less than 50ms per solution
- Startup time: less than 3 seconds from `run.bat` double-click

### Compatibility
- Windows 10 and newer (primary), Linux and Mac (secondary via `run.sh`)
- Python 3.8 and newer (widely available)
- Modern browsers (Chrome 90 and newer, Firefox 88 and newer, Edge 90 and newer)
- No mobile support required for V1

### Data Constraints
- Heightmap JSON files: 2-10MB each (uncompressed), 20-50 maps means about 500MB total
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

**Phase 1: Local Collection (Maintainer only, one-time per map update)**
1. Run `python processor/collect_maps.py` on machine with PR:BF2 installed
2. Script auto-detects installation at standard paths
3. Script copies server.zip files to `/raw_map_data/[map_name]/`
4. Script validates each file (MD5 checksum, integrity check)
5. Script handles duplicates (skip if identical, update if changed)
6. Script generates `manifest.json` with map inventory
7. Script configures Git LFS if total size > 10MB threshold
8. Maintainer commits: `git add raw_map_data/ && git commit && git push`

**Phase 2: Cloud Processing (Maintainer, runs anywhere with Git)**
1. Clone repository: `git clone https://github.com/user/repo.git`
   - Git LFS automatically downloads tracked files
2. Open `processor/process_maps.ipynb` in Google Colab or local Jupyter
3. Provide Git credentials (name, email, GitHub Personal Access Token)
4. Run all cells sequentially
5. Notebook processes all maps from `/raw_map_data/`:
   - Extracts HeightmapPrimary.raw from each server.zip
   - Parses 16-bit RAW data, extracts config files
   - Converts to JSON format (lossless)
   - Generates metadata.json for each map
   - Outputs to `/processed_maps/[map_name]/`
6. Notebook automatically commits and pushes results to GitHub
7. Processing time: ~5-10 minutes for 45 maps (depending on hardware)

**End Users:**
- Clone repository (includes pre-processed maps in `/processed_maps/`)
- No processing needed, just run calculator with `run.bat` or `run.sh`
- For custom maps: Contact maintainer to add server.zip to `/raw_map_data/`

## Quick Reference

**Key Files:**
- `PRD.md` - Product Requirements Document (this is the bible)
- `openspec/AGENTS.md` - AI assistant instructions for OpenSpec workflow
- `openspec/project.md` - This file (project context)
- `processor/collect_maps.py` - Local extraction script (Phase 1)
- `processor/process_maps.ipynb` - Cloud processing notebook (Phase 2)
- `calculator/server.py` - Flask static file server
- `calculator/static/js/ballistics.js` - Core physics calculations

**Key Commands:**
```bash
# Run calculator
python calculator/server.py          # Manual start
./run.bat                             # Windows one-click
./run.sh                              # Linux and Mac one-click

# Phase 1: Collect maps (local, maintainer only)
python processor/collect_maps.py     # Auto-detect PR:BF2
python processor/collect_maps.py --path "D:\Games\PR"  # Custom path

# Phase 2: Process maps (cloud or local, maintainer only)
jupyter notebook processor/process_maps.ipynb  # Local execution
# Or: Open in Google Colab and run all cells

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
