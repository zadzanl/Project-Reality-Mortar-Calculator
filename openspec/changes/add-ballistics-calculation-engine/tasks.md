# Implementation Tasks: Ballistics Calculation Engine

## 1. Ballistics Module (ballistics.js)

- [ ] 1.1 Create `calculator/static/js/ballistics.js` module structure
- [ ] 1.2 Define PR_PHYSICS constant object (gravity, velocity, max_range, mils, degrees)
- [ ] 1.3 Implement `calculateDistance(x1, y1, x2, y2)` - Euclidean distance in X-Y plane
- [ ] 1.4 Implement `calculateAzimuth(x1, y1, x2, y2)` - Compass bearing 0-360°
- [ ] 1.5 Implement `calculateElevationAngle(distance, heightDiff)` - High-angle solution in radians
- [ ] 1.6 Implement `radiansToMils(radians)` - Convert to military angular unit
- [ ] 1.7 Implement `radiansToDegrees(radians)` - Convert to degrees
- [ ] 1.8 Implement `milsToDegrees(mils)` - Direct conversion
- [ ] 1.9 Implement `calculateTimeOfFlight(distance, elevationAngle, heightDiff)` - TOF in seconds
- [ ] 1.10 Implement `validateFiringSolution(distance, heightDiff)` - Check physical possibility
- [ ] 1.11 Export all functions as ES6 module
- [ ] 1.12 Add JSDoc comments for all functions

## 2. Coordinate Conversion Module (coordinates.js)

- [ ] 2.1 Create `calculator/static/js/coordinates.js` module structure
- [ ] 2.2 Define column mapping (A-M → 0-12)
- [ ] 2.3 Define keypad position offsets (1-9 within square)
- [ ] 2.4 Implement `parseGridReference(gridRef)` - Parse "D6-7" format with regex
- [ ] 2.5 Implement `gridToXY(column, row, keypad, gridScale)` - Convert to meters
- [ ] 2.6 Implement `xyToGrid(x, y, gridScale)` - Reverse conversion to grid notation
- [ ] 2.7 Implement `validateGridReference(gridRef)` - Format and bounds validation
- [ ] 2.8 Implement `getKeypadOffset(keypadNum, gridScale)` - Calculate offset within square
- [ ] 2.9 Handle edge cases (invalid columns, out-of-bounds rows, invalid keypad numbers)
- [ ] 2.10 Export all functions as ES6 module
- [ ] 2.11 Add JSDoc comments with examples

## 3. Heightmap Sampling Module (heightmap.js)

- [ ] 3.1 Create `calculator/static/js/heightmap.js` module structure
- [ ] 3.2 Implement `loadHeightmap(mapName)` - Fetch JSON from `/processed_maps/[map]/heightmap.json`
- [ ] 3.3 Implement `loadMetadata(mapName)` - Fetch metadata.json
- [ ] 3.4 Implement `worldToPixel(x, y, mapSize, resolution)` - Convert world coords to pixel coords
- [ ] 3.5 Implement `bilinearInterpolation(heightmapData, pixelX, pixelY)` - Sample height between pixels
- [ ] 3.6 Implement `getElevation(x, y, heightmapData, heightScale, mapSize, resolution)` - Full pipeline
- [ ] 3.7 Handle boundary cases (coordinates exactly on border, +1 pixel border handling)
- [ ] 3.8 Implement caching for loaded heightmaps (avoid redundant fetches)
- [ ] 3.9 Add error handling for missing files, corrupted JSON
- [ ] 3.10 Export all functions as ES6 module
- [ ] 3.11 Add JSDoc comments and usage examples

## 4. Physics Constants Validation

- [ ] 4.1 Verify PR_PHYSICS.GRAVITY = 14.86 (NOT 9.8)
- [ ] 4.2 Verify PR_PHYSICS.PROJECTILE_VELOCITY = 148.64
- [ ] 4.3 Verify PR_PHYSICS.MAX_RANGE = 1500
- [ ] 4.4 Verify PR_PHYSICS.MILS_PER_CIRCLE = 6400
- [ ] 4.5 Add code comments warning against modification
- [ ] 4.6 Document source of constants in PRD.md reference

## 5. Ballistic Formula Implementation

- [ ] 5.1 Implement discriminant check: `v⁴ - g*(g*D² + 2*v²*ΔZ)`
- [ ] 5.2 Return error if discriminant < 0 (physically impossible shot)
- [ ] 5.3 Calculate high-angle solution: `arctan((v² + sqrt(discriminant)) / (g*D))`
- [ ] 5.4 Handle zero distance edge case (D < 1m)
- [ ] 5.5 Handle extreme elevation warning (|ΔZ| > 200m)
- [ ] 5.6 Validate result is within 0 to π/2 radians (0-90°)
- [ ] 5.7 Test against known solutions from PRD.md examples

## 6. Coordinate System Implementation

- [ ] 6.1 Implement origin at top-left corner (0, 0) = Northwest
- [ ] 6.2 X-axis: left to right (West to East), X increases rightward
- [ ] 6.3 Y-axis: top to bottom (North to South), Y increases downward
- [ ] 6.4 Azimuth: 0° = North, 90° = East, 180° = South, 270° = West
- [ ] 6.5 Convert atan2 result to compass bearing (handle negative angles)
- [ ] 6.6 Test coordinate conversions with known grid references

## 7. Bilinear Interpolation Algorithm

- [ ] 7.1 Convert world XY to pixel coordinates (may be fractional, e.g., 123.7)
- [ ] 7.2 Find 4 surrounding pixels (floor and ceil of X and Y)
- [ ] 7.3 Read height values from heightmap data array
- [ ] 7.4 Calculate interpolation weights based on fractional parts
- [ ] 7.5 Interpolate horizontally (top row, bottom row)
- [ ] 7.6 Interpolate vertically (combine top and bottom results)
- [ ] 7.7 Handle edge cases (pixel coordinates exactly on integer boundary)
- [ ] 7.8 Test with known heightmap samples (verify smoothness)

## 8. Grid Reference Parser

- [ ] 8.1 Accept formats: "D6-7", "D6-kpad7", "Delta 6-7", "d6-7" (case-insensitive)
- [ ] 8.2 Use regex: `/^([A-M])(\d{1,2})-(?:kpad)?(\d)$/i`
- [ ] 8.3 Extract column letter, row number, keypad number
- [ ] 8.4 Validate column is A-M (reject N, O, P, etc.)
- [ ] 8.5 Validate row is 1-13 (reject 0, 14+)
- [ ] 8.6 Validate keypad is 1-9 (reject 0, 10+)
- [ ] 8.7 Return structured object: `{column: 'D', row: 6, keypad: 7, x: 450.5, y: 675.25}`
- [ ] 8.8 Return null or throw error for invalid input

## 9. Error Handling and Validation

- [ ] 9.1 Validate distance is within 1m to 1500m
- [ ] 9.2 Validate coordinates are within map bounds (0 to map_size)
- [ ] 9.3 Validate heightmap resolution matches expected (1025 or 2049)
- [ ] 9.4 Handle missing heightmap data (return error, not crash)
- [ ] 9.5 Handle JSON parse errors gracefully
- [ ] 9.6 Return descriptive error messages for UI display
- [ ] 9.7 Log errors to console for debugging

## 10. Performance Optimization

- [ ] 10.1 Measure calculation time (target < 50ms per solution)
- [ ] 10.2 Cache heightmap data after first load (avoid re-parsing JSON)
- [ ] 10.3 Use TypedArray for heightmap data if beneficial
- [ ] 10.4 Optimize bilinear interpolation (minimize array lookups)
- [ ] 10.5 Profile with browser DevTools Performance tab
- [ ] 10.6 Test with largest maps (4km, 2049×2049 resolution)

## 11. Unit Testing Preparation

- [ ] 11.1 Structure functions as pure (input → output, no side effects)
- [ ] 11.2 Avoid DOM dependencies (no document, window, etc.)
- [ ] 11.3 Create test vectors from PRD.md examples
- [ ] 11.4 Document expected inputs and outputs for each function
- [ ] 11.5 Add assertion helpers for floating-point comparison (±0.01 tolerance)

## 12. Integration Testing

- [ ] 12.1 Test full pipeline: grid ref → XY → elevation → firing solution
- [ ] 12.2 Test with Korengal Valley (extreme elevation differences)
- [ ] 12.3 Test with Vadso City (long range + elevation)
- [ ] 12.4 Test with Burning Sands (flat terrain control)
- [ ] 12.5 Compare calculator results with in-game measurements
- [ ] 12.6 Verify accuracy: azimuth ±2°, elevation ±1 mil, distance ±10m
- [ ] 12.7 Test edge cases: max range, zero distance, extreme ΔZ

## 13. Documentation

- [ ] 13.1 Add JSDoc comments to all exported functions
- [ ] 13.2 Include parameter types and return types
- [ ] 13.3 Add usage examples in comments
- [ ] 13.4 Document physics constants and their sources
- [ ] 13.5 Create developer guide for extending calculations
- [ ] 13.6 Add inline comments explaining complex formulas
- [ ] 13.7 Reference PRD.md sections for formula derivations
