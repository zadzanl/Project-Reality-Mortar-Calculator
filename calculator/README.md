# Project Reality Mortar Calculator - Frontend

This directory contains the web-based calculator interface and JavaScript modules for ballistics calculations.

## Quick Start

**From the project root directory, run:**

Windows:
```bash
run.bat
```

Linux/Mac:
```bash
./run.sh
```

The calculator will open automatically in your browser at `http://localhost:8080`

## Directory Structure

```
calculator/
├── static/
│   ├── js/
│   │   ├── app.js           # Main application orchestrator
│   │   ├── ballistics.js    # Core ballistics calculations
│   │   ├── coordinates.js   # Grid reference ↔ XY conversion
│   │   └── heightmap.js     # Terrain height sampling
│   ├── css/
│   │   └── styles.css       # Application styles (BEM naming)
│   └── lib/
│       ├── leaflet.js       # Leaflet 1.9.4 (bundled)
│       ├── leaflet.css      # Leaflet styles
│       └── images/          # Leaflet marker assets
├── templates/
│   └── index.html           # Main UI template
└── server.py                # Flask static file server
```

## Flask Server

The Flask server (`server.py`) serves static files only. All calculations happen in the browser.

**Features:**
- Auto-detects available port (8080-8089)
- Opens browser automatically
- Serves HTML, CSS, JavaScript, and JSON map data
- Graceful shutdown with Ctrl+C
- No external dependencies required

**Routes:**
- `/` - Main calculator page
- `/static/<path>` - Static assets (CSS, JS, images)
- `/maps/<map_name>/<file>` - Map data (heightmap.json, metadata.json)
- `/maps/list` - JSON list of available maps

**Starting Manually:**
```bash
python calculator/server.py
```

## JavaScript Modules

### ballistics.js

Core ballistics engine for calculating mortar firing solutions.

**Key Functions:**
- `calculateFiringSolution(mortar, target)` - Complete firing solution
- `calculateDistance(x1, y1, x2, y2)` - Horizontal distance
- `calculateAzimuth(x1, y1, x2, y2)` - Compass bearing
- `calculateElevationAngle(distance, heightDiff)` - High-angle solution
- `radiansToMils(radians)` - Convert to military units
- `validateFiringSolution(distance, heightDiff)` - Check validity

**Critical Constants (DO NOT MODIFY):**
- `PR_PHYSICS.GRAVITY = 14.86` m/s² (Project Reality engine)
- `PR_PHYSICS.PROJECTILE_VELOCITY = 148.64` m/s
- `PR_PHYSICS.MAX_RANGE = 1500` meters

### coordinates.js

Grid reference parsing and coordinate conversion.

**Key Functions:**
- `parseGridReference(gridRef)` - Parse "D6-7" format
- `gridToXY(column, row, keypad, gridScale)` - Convert to meters
- `xyToGrid(x, y, gridScale)` - Reverse conversion
- `validateGridReference(gridRef)` - Format validation
- `calculateGridScale(mapSize)` - Determine grid square size

**Grid System:**
- Columns: A-M (13 columns)
- Rows: 1-13 (13 rows)
- Keypad: 1-9 (phone layout: 7-8-9 / 4-5-6 / 1-2-3)

### heightmap.js

Terrain height sampling with bilinear interpolation.

**Key Functions:**
- `loadMapData(mapName)` - Load heightmap + metadata
- `getElevation(x, y, ...)` - Sample height at position
- `bilinearInterpolation(...)` - Smooth interpolation
- `worldToPixel(x, y, mapSize, resolution)` - Coordinate conversion

**Features:**
- Caches loaded heightmaps
- Bilinear interpolation for smooth results
- Handles +1 pixel border in heightmaps
- Error handling for missing/corrupted data

## Usage Example

```javascript
import { loadMapData } from './static/js/heightmap.js';
import { gridRefToXY } from './static/js/coordinates.js';
import { calculateFiringSolution } from './static/js/ballistics.js';

// Load map data
const mapData = await loadMapData('muttrah_city_2');
const gridScale = mapData.metadata.grid_scale;

// Convert grid references to XY coordinates
const mortarXY = gridRefToXY('D6-7', gridScale);
const targetXY = gridRefToXY('C2-3', gridScale);

// Get elevations
const mortarZ = mapData.getElevationAt(mortarXY.x, mortarXY.y);
const targetZ = mapData.getElevationAt(targetXY.x, targetXY.y);

// Calculate firing solution
const solution = calculateFiringSolution(
  { x: mortarXY.x, y: mortarXY.y, z: mortarZ },
  { x: targetXY.x, y: targetXY.y, z: targetZ }
);

console.log(`Distance: ${solution.distance.toFixed(1)}m`);
console.log(`Azimuth: ${solution.azimuth.toFixed(1)}°`);
console.log(`Elevation: ${solution.elevationMils.toFixed(0)} mils`);
console.log(`Time of Flight: ${solution.timeOfFlight.toFixed(1)}s`);
```

## Testing

All modules are structured as pure functions with no DOM dependencies, making them testable:

```javascript
// Unit test example
import { calculateDistance } from './ballistics.js';

const dist = calculateDistance(0, 0, 300, 400);
console.assert(Math.abs(dist - 500) < 0.01, 'Distance should be 500m');
```

## Coordinate System

- **Origin (0,0):** Top-left corner (Northwest)
- **X-axis:** Left to right (West → East)
- **Y-axis:** Top to bottom (North → South)
- **Z-axis:** Elevation above sea level
- **Azimuth:** 0° = North, 90° = East, 180° = South, 270° = West

## Next Steps

1. Implement `index.html` - User interface
2. Implement `server.py` - Flask static file server
3. Create `run.bat` - Windows launcher
4. Add unit tests in `/tests` directory
5. Integration testing with real map data

## References

- Physics formulas: `PRD.md` (Ballistic Calculation section)
- Grid system: `PRD.md` (Grid Coordinate Parsing section)
- Heightmap format: `PRD.md` (Heightmap Coordinate Conversion section)

## Map Interactions

- Click on the map to place the target marker.
- Shift+Click on the map to place the mortar marker.
- Drag markers to adjust positions; markers update grid and elevation displays on drag end.
- Use the dropdowns to enter grid coordinates (Column A-M, Row 1-13, Keypad 1-9).
