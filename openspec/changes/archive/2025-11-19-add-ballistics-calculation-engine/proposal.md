# Proposal: Ballistics Calculation Engine

## Why

The mortar calculator must do math to figure out:
1. Direction to aim (azimuth)
2. Angle to aim up/down (elevation)
3. How long the shell takes to reach target (time-of-flight)

The math must account for:
- Distance to target
- Height difference (target higher or lower)
- Project Reality game physics (gravity 14.86, shell speed 148.64)

The calculation code must be:
- Pure functions (same input always gives same output)
- Testable (we can check if math is correct)
- Separate from UI (no mixing of math and buttons/display)

Right now, we have no calculation code.

## What Changes

- **Core Ballistics Module** (`calculator/static/js/ballistics.js`):
  - Calculate high-angle firing solution using PR game physics
  - Convert between angle units (radians ↔ mils ↔ degrees)
  - Calculate how long shell is in the air
  - Calculate distance and direction from X/Y positions
  - Check for errors (too far, impossible shot, very steep angle)
  - Pure functions (same inputs always give same outputs, no side effects)

- **Coordinate Conversion Module** (`calculator/static/js/coordinates.js`):
  - Convert grid references to XY positions ("D6-7" → meters)
  - Convert XY positions back to grid references (reverse)
  - Calculate keypad position (1-9 within each grid square)
  - Calculate grid square size based on map size (PR uses 13×13 grid)
  - Check if coordinates are valid and inside map

- **Heightmap Sampling Module** (`calculator/static/js/heightmap.js`):
  - Load height data from `/processed_maps/[map]/heightmap.json`
  - Use bilinear interpolation to get smooth heights between pixels
  - Convert world positions (meters) to image pixel positions
  - Calculate elevation using height_scale formula
  - Load map settings (map_size, height_scale, grid_scale)

- **Physics Constants Configuration**:
  - **CRITICAL VALUES** (DO NOT CHANGE):
    - Gravity: 14.86 m/s² (Project Reality engine value)
    - Projectile velocity: 148.64 m/s (mortar shell speed)
    - Maximum range: 1500 meters (gameplay limit)
  - Mils per circle: 6400 (NATO standard)
  - Degrees per circle: 360

## Impact

- **Affected Specs**: Creates new capability `ballistics-engine`
- **Affected Code**:
  - New files: `calculator/static/js/ballistics.js`, `calculator/static/js/coordinates.js`, `calculator/static/js/heightmap.js`
- **Dependencies**: None (pure JavaScript ES6+, no external libraries)
- **Testing**: Pure functions enable unit testing without browser
- **Accuracy**: Calculations must match in-game behavior within ±1 Mil, ±10m distance
- **Performance**: All calculations must complete within 50ms
