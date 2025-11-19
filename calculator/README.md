# Project Reality Mortar Calculator - Frontend

This directory contains the web-based calculator interface and JavaScript modules for ballistics calculations.

## Directory Structure

```
calculator/
├── static/
│   └── js/
│       ├── ballistics.js    # Core ballistics calculations
│       ├── coordinates.js   # Grid reference ↔ XY conversion
│       └── heightmap.js     # Terrain height sampling
├── index.html               # Main UI (to be implemented)
└── server.py                # Flask static file server (to be implemented)
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
