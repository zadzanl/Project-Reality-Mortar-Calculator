# Ballistics Engine Developer Guide

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Testing Strategy](#testing-strategy)
4. [Performance Optimization](#performance-optimization)
5. [Integration Test Recipes](#integration-test-recipes)
6. [Memory Profiling](#memory-profiling)
7. [Adding New Features](#adding-new-features)
8. [Troubleshooting](#troubleshooting)

## Overview

The Ballistics Calculation Engine provides pure functions for calculating mortar firing solutions using Project Reality game physics. The engine consists of three main modules:

- **ballistics.js** - Core physics calculations (distance, azimuth, elevation, TOF)
- **coordinates.js** - Grid reference parsing and coordinate conversion
- **heightmap.js** - Elevation sampling with bilinear interpolation

### Critical Constants

**DO NOT MODIFY THESE VALUES** - They are derived from the Project Reality game engine:

```javascript
GRAVITY = 14.86 m/s²           // PR engine gravity (NOT Earth's 9.8)
PROJECTILE_VELOCITY = 148.64 m/s  // Mortar shell speed
MAX_RANGE = 1500 meters        // Gameplay limit
MILS_PER_CIRCLE = 6400         // NATO military angular unit
```

## Architecture

### Module Dependencies

```
User Input (Grid Ref)
    ↓
coordinates.js (parseGridReference, gridRefToXY)
    ↓
heightmap.js (loadHeightmap, getElevation)
    ↓
ballistics.js (calculateFiringSolution)
    ↓
Firing Solution Output
```

### Data Flow

1. **Input**: Grid reference (e.g., "D6-7") or XY coordinates
2. **Coordinate Conversion**: Grid → XY world coordinates
3. **Elevation Sampling**: XY → Z elevation via heightmap interpolation
4. **Ballistics Calculation**: (X₁,Y₁,Z₁), (X₂,Y₂,Z₂) → Firing solution

### Pure Functions

All calculation functions are **pure** (deterministic, no side effects):
- Same inputs always produce same outputs
- No global state mutation
- No DOM dependencies
- Testable in isolation

## Testing Strategy

### Test Hierarchy

```
Unit Tests (test_*.js)
    ↓ Components in isolation
Integration Tests (test_integration.js)
    ↓ Full pipeline with real data
Map-Specific Tests (test_map_specific.js)
    ↓ Diverse terrain scenarios
Performance Benchmarks (bench.js)
    ↓ Timing and profiling
```

### Running Tests

```bash
# All tests
npm test

# Individual test suites
node calculator/tests/test_ballistics.js
node calculator/tests/test_coordinates.js
node calculator/tests/test_heightmap.js
node calculator/tests/test_integration.js

# Map-specific tests
node calculator/tests/test_map_specific.js

# Performance benchmark (1000 iterations)
node calculator/tests/bench.js 1000
```

### Unit Test Guidelines

**When to write unit tests:**
- New calculation function added
- Edge case discovered
- Bug fixed (regression test)
- Performance-critical code path

**Example unit test:**

```javascript
import assert from 'node:assert';
import { calculateDistance } from '../static/js/ballistics.js';

// Test known distance (3-4-5 right triangle)
const dist = calculateDistance(0, 0, 300, 400);
assert.strictEqual(dist, 500, 'Should calculate Pythagorean distance');

// Test zero distance
const zeroDist = calculateDistance(100, 100, 100, 100);
assert.strictEqual(zeroDist, 0, 'Same point should have zero distance');
```

### Integration Test Guidelines

**When to write integration tests:**
- New map added
- Coordinate system changed
- Heightmap format updated
- End-to-end workflow modified

**Example integration test:**

```javascript
// Load map data
const mapData = await loadMapData('test_bootcamp');
const gridScale = calculateGridScale(mapData.metadata.map_size);

// Parse grid reference
const mortarXY = gridRefToXY('D6-5', gridScale);
const targetXY = gridRefToXY('F8-5', gridScale);

// Get elevations
const mortarZ = mapData.getElevationAt(mortarXY.x, mortarXY.y);
const targetZ = mapData.getElevationAt(targetXY.x, targetXY.y);

// Calculate solution
const solution = calculateFiringSolution(
  { x: mortarXY.x, y: mortarXY.y, z: mortarZ },
  { x: targetXY.x, y: targetXY.y, z: targetZ }
);

// Validate
assert(solution.valid, 'Solution should be valid');
assert(solution.distance > 0, 'Distance should be positive');
```

## Performance Optimization

### Current Performance (as of 2025-11-19)

Benchmark results on test_bootcamp map (1000 iterations):

| Operation | Mean | P95 | P99 | Status |
|-----------|------|-----|-----|--------|
| Grid Parsing | 0.001ms | 0.002ms | 0.009ms |  OK  Excellent |
| Grid to XY | 0.001ms | 0.003ms | 0.008ms |  OK  Excellent |
| Elevation Sampling | 0.001ms | 0.002ms | 0.004ms |  OK  Excellent |
| Firing Solution | 0.005ms | 0.008ms | 0.032ms |  OK  Excellent |
| **Full Pipeline** | **0.004ms** | **0.007ms** | **0.014ms** | ** OK  Excellent** |

**Target**: <50ms per full pipeline calculation  OK  **ACHIEVED** (49.996ms margin)

### Optimization Techniques Applied

#### 1. Uint16Array for Heightmaps

**Benefit**: 50% memory reduction, faster access

```javascript
// Before: Regular array (uses 64-bit floats internally)
heightmapData.data = [0, 1234, 5678, ...]; // ~512MB for 2049×2049

// After: Uint16Array (uses 16-bit integers)
heightmapData.data = new Uint16Array([0, 1234, 5678, ...]); // ~256MB
```

**Implementation** (`heightmap.js:loadHeightmap`):
```javascript
const typedData = new Uint16Array(heightmapData.data);
const optimizedData = { ...heightmapData, data: typedData };
```

#### 2. Heightmap Caching

**Benefit**: Avoid redundant network requests and JSON parsing

```javascript
// Cache loaded heightmaps
const heightmapCache = new Map();

if (heightmapCache.has(mapName)) {
  return heightmapCache.get(mapName); // Instant return
}

// First load: fetch + parse + cache
const data = await fetch(...).then(r => r.json());
heightmapCache.set(mapName, data);
```

#### 3. Bilinear Interpolation Optimization

**Benefit**: Minimize array lookups (4 reads per interpolation)

```javascript
// Optimized: Single index calculation
function getPixelValue(data, x, y, width) {
  return data[y * width + x] || 0; // Row-major order
}

// Used 4 times per interpolation (top-left, top-right, bottom-left, bottom-right)
```

### Profiling in Browser

#### Chrome DevTools Performance Tab

1. Open DevTools → Performance tab
2. Click Record
3. Perform 100+ calculations
4. Stop recording
5. Analyze flame graph

**What to look for:**
- Functions taking >10ms
- Repeated calls to same function (caching opportunity)
- GC (garbage collection) pauses

#### Memory Profiling

1. Open DevTools → Memory tab
2. Take heap snapshot before loading map
3. Load heightmap
4. Take second snapshot
5. Compare snapshots

**Expected memory usage:**
- 513×513 heightmap: ~0.5 MB (Uint16Array)
- 1025×1025 heightmap: ~2 MB
- 2049×2049 heightmap: ~8 MB

**Red flags:**
- Memory increasing without bound (leak)
- Multiple copies of same heightmap (cache miss)
- Retained detached DOM nodes

### Performance Recommendations for Large Maps

#### 4096m Maps (2049×2049 resolution)

**Challenges:**
- 8MB+ heightmap data
- 4+ million elevation samples
- Potential browser memory limits

**Solutions:**

1. **Lazy Loading**
   ```javascript
   // Load heightmap on-demand, not at startup
   async function getElevationLazy(x, y, mapName) {
     if (!heightmapCache.has(mapName)) {
       await loadHeightmap(mapName); // First access loads
     }
     return getElevation(...);
   }
   ```

2. **Spatial Indexing** (future optimization)
   ```javascript
   // Divide map into tiles (e.g., 256×256)
   // Load only tiles containing mortar/target positions
   const tileX = Math.floor(x / 256);
   const tileY = Math.floor(y / 256);
   const tile = await loadTile(mapName, tileX, tileY);
   ```

3. **Web Workers** (for UI responsiveness)
   ```javascript
   // Offload calculations to background thread
   const worker = new Worker('ballistics-worker.js');
   worker.postMessage({ mortar, target, heightmap });
   worker.onmessage = (e) => displaySolution(e.data);
   ```

## Integration Test Recipes

### Recipe 1: Adding a New Map Test

```javascript
// 1. Check map is in processed_maps/
// 2. Load map metadata
const metadata = await loadMetadataFromFile('new_map');
console.log(metadata); // Check map_size, height_scale, resolution

// 3. Create test case
async function testNewMap() {
  const mapData = await loadMapData('new_map');
  const gridScale = calculateGridScale(mapData.metadata.map_size);
  
  // Choose representative grid positions
  testFiringSolution('new_map', 'D6-5', 'G8-5', mapData, {
    minDistance: 100,  // Expected range
    maxDistance: 1000
  });
}
```

### Recipe 2: Testing Extreme Elevation

```javascript
// Find highest and lowest points in map
const stats = getHeightmapStats(heightmap.data);
console.log(`Height range: ${stats.min} to ${stats.max}`);

// Convert to elevation
const minElev = (stats.min / 65535) * heightScale;
const maxElev = (stats.max / 65535) * heightScale;

// Create test from low to high
const solution = calculateFiringSolution(
  { x: lowPoint.x, y: lowPoint.y, z: minElev },
  { x: highPoint.x, y: highPoint.y, z: maxElev }
);

// Should warn about extreme elevation or be unreachable
assert(solution.status === 'EXTREME_ELEVATION' || !solution.valid);
```

### Recipe 3: Reciprocal Firing Test

```javascript
// Verify distance is same in both directions
const ab = calculateFiringSolution(posA, posB);
const ba = calculateFiringSolution(posB, posA);

assert.strictEqual(ab.distance, ba.distance, 'Distance should be symmetric');
assert.strictEqual(ab.heightDelta, -ba.heightDelta, 'Height delta should be opposite');
assert(Math.abs(ab.azimuth - ba.azimuth - 180) < 0.1, 'Azimuth should differ by 180°');
```

### Recipe 4: In-Game Validation

**Steps to collect in-game data:**

1. Enter PR server in practice mode
2. Place mortar at known grid reference (e.g., D6-7)
3. Get elevation from console: `pr.showElevation`
4. Set target at known grid reference
5. Note in-game firing solution (mils, azimuth)
6. Compare with calculator output

**Expected accuracy:**
- Distance: ±10 meters
- Azimuth: ±2 degrees
- Elevation: ±1 mil

**Validation test:**

```javascript
// In-game measurement from Muttrah City 2
const inGameData = {
  mortarRef: 'D6-7',
  targetRef: 'H9-3',
  expectedDistance: 875, // ±10m
  expectedAzimuth: 132,  // ±2°
  expectedElevation: 1245 // ±1 mil
};

// Calculator result
const solution = testFiringSolution(
  'muttrah_city_2',
  inGameData.mortarRef,
  inGameData.targetRef,
  mapData
);

// Validate within tolerance
assertApprox(solution.distance, inGameData.expectedDistance, 10);
assertApprox(solution.azimuth, inGameData.expectedAzimuth, 2);
assertApprox(solution.elevationMils, inGameData.expectedElevation, 1);
```

## Memory Profiling

### Heap Snapshot Analysis

#### Taking Snapshots

```javascript
// In browser console or Node.js
// 1. Before loading any maps
const memBefore = process.memoryUsage().heapUsed / 1024 / 1024;

// 2. Load map
await loadHeightmap('korengal');

// 3. After loading
const memAfter = process.memoryUsage().heapUsed / 1024 / 1024;
const delta = memAfter - memBefore;

console.log(`Heightmap memory: ${delta.toFixed(2)} MB`);
```

#### Expected Memory Footprint

| Map Size | Resolution | Array Size | Uint16Array | Regular Array | Savings |
|----------|------------|------------|-------------|---------------|---------|
| 1024m    | 513×513    | 263,169    | ~0.5 MB     | ~2 MB         | 75%     |
| 2048m    | 1025×1025  | 1,050,625  | ~2 MB       | ~8 MB         | 75%     |
| 4096m    | 2049×2049  | 4,198,401  | ~8 MB       | ~32 MB        | 75%     |

### Memory Leak Detection

**Common causes:**
1. Event listeners not removed
2. Closures retaining large objects
3. Cache growing without bound

**Detection:**

```javascript
// Monitor cache size
setInterval(() => {
  console.log('Heightmap cache size:', heightmapCache.size);
  console.log('Metadata cache size:', metadataCache.size);
}, 10000);

// Clear cache if needed
if (heightmapCache.size > 10) {
  clearCache(); // Defined in heightmap.js
}
```

## Adding New Features

### Example: Add Low-Angle Solution

Currently only high-angle solution is implemented. To add low-angle:

**1. Modify `calculateElevationAngle` in `ballistics.js`:**

```javascript
export function calculateElevationAngles(distance, heightDiff) {
  // ... existing discriminant check ...
  
  const sqrtDisc = Math.sqrt(discriminant);
  
  // High-angle solution (existing)
  const highAngle = Math.atan((v2 + sqrtDisc) / (g * distance));
  
  // Low-angle solution (NEW)
  const lowAngle = Math.atan((v2 - sqrtDisc) / (g * distance));
  
  return { highAngle, lowAngle };
}
```

**2. Update `calculateFiringSolution`:**

```javascript
const angles = calculateElevationAngles(distance, heightDelta);

// Return both solutions
return {
  highAngle: {
    elevationRadians: angles.highAngle,
    elevationMils: radiansToMils(angles.highAngle),
    timeOfFlight: calculateTimeOfFlight(distance, angles.highAngle, heightDelta)
  },
  lowAngle: {
    elevationRadians: angles.lowAngle,
    elevationMils: radiansToMils(angles.lowAngle),
    timeOfFlight: calculateTimeOfFlight(distance, angles.lowAngle, heightDelta)
  }
};
```

**3. Add unit tests:**

```javascript
// Test that high angle > low angle
const solution = calculateFiringSolution(mortar, target);
assert(solution.highAngle.elevationDegrees > solution.lowAngle.elevationDegrees,
  'High angle should be steeper than low angle');

// Test that both hit same target (within tolerance)
const highTOF = solution.highAngle.timeOfFlight;
const lowTOF = solution.lowAngle.timeOfFlight;
assert(highTOF > lowTOF, 'High angle should take longer to reach target');
```

## Troubleshooting

### Issue: Calculations return NaN

**Symptom:** `solution.elevationMils === NaN`

**Causes:**
1. Invalid heightmap data
2. Division by zero
3. Negative discriminant

**Debugging:**

```javascript
console.log('Distance:', distance);
console.log('Height delta:', heightDelta);
console.log('Discriminant:', v4 - g * (g * D * D + 2 * v2 * dZ));

// Check heightmap
console.log('Mortar Z:', mortarZ, 'Target Z:', targetZ);
console.log('Heightmap stats:', getHeightmapStats(heightmap.data));
```

### Issue: Slow performance (>50ms per calculation)

**Diagnosis:**

```bash
node calculator/tests/bench.js 1000
```

**If slow:**
1. Check bilinear interpolation is using typed arrays
2. Verify heightmap is cached
3. Profile in browser DevTools
4. Check for memory pressure (GC pauses)

**Optimization checklist:**
- [ ] Heightmap uses Uint16Array
- [ ] Cache is enabled and hit rate >90%
- [ ] No repeated JSON parsing
- [ ] Minimal array allocations in hot paths

### Issue: Wrong elevation values

**Symptom:** Elevation doesn't match in-game

**Checklist:**
1. Verify heightmap formula: `elevation = (pixel / 65535) * height_scale`
2. Check height_scale in metadata.json
3. Verify bilinear interpolation boundary handling
4. Test with known elevation points

**Validation:**

```javascript
// Center of map should be ~mid-height
const centerX = mapSize / 2;
const centerY = mapSize / 2;
const centerElev = getElevation(centerX, centerY, ...);

console.log('Center elevation:', centerElev);
console.log('Expected range: 0 to', heightScale);
assert(centerElev >= 0 && centerElev <= heightScale);
```

### Issue: Grid reference parsing fails

**Symptom:** `gridRefToXY returns null`

**Valid formats:**
- `"D6-7"`  OK 
- `"Delta 6-7"`  OK 
- `"d6-7"`  OK  (case insensitive)
- `"D6-kpad7"`  OK 

**Invalid formats:**
- `"D-6-7"` (wrong delimiter)
- `"D6"` (missing keypad)
- `"D14-7"` (row out of range)
- `"N6-7"` (column out of range)

**Debugging:**

```javascript
import { parseGridReference } from './coordinates.js';

const result = parseGridReference('D6-7');
console.log(result);
// Should output: { column: 'D', row: 6, keypad: 7 }
```

---

## Quick Reference

### Key Files

- `calculator/static/js/ballistics.js` - Physics calculations
- `calculator/static/js/coordinates.js` - Grid system
- `calculator/static/js/heightmap.js` - Elevation sampling
- `calculator/tests/` - All test files
- `processed_maps/` - Heightmap data (one folder per map)

### Important Constants

```javascript
PR_PHYSICS.GRAVITY = 14.86              // m/s²
PR_PHYSICS.PROJECTILE_VELOCITY = 148.64 // m/s
PR_PHYSICS.MAX_RANGE = 1500             // meters
PR_PHYSICS.MILS_PER_CIRCLE = 6400       // NATO standard
```

### Coordinate System

- Origin (0,0) = Top-left corner (Northwest)
- X-axis: Left to right (West to East)
- Y-axis: Top to bottom (North to South)
- Grid: 13×13 (A-M columns, 1-13 rows)
- Keypad: 1-9 (phone layout within each grid square)

### Test Commands

```bash
npm test                                    # All unit + integration tests
node calculator/tests/bench.js 1000        # Performance benchmark
node calculator/tests/test_map_specific.js # Map-specific validation
```

### Performance Targets

- Grid parsing: <1ms  OK 
- Elevation sampling: <1ms  OK 
- Firing solution: <10ms  OK 
- **Full pipeline: <50ms  OK ** (Currently ~0.004ms avg)

---

**Last Updated:** 2025-11-19  
**Version:** 1.0  
**Maintainer:** Project Reality Mortar Calculator Team
