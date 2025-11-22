/**
 * Integration Tests for Ballistics Calculation Engine
 * 
 * Tests the full pipeline: Grid Reference → XY Coordinates → Elevation → Firing Solution
 * Uses real map data from processed_maps directory
 */

import assert from 'node:assert';
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertApprox } from './assertApprox.js';
import { gridRefToXY, calculateGridScale } from '../static/js/coordinates.js';
import { bilinearInterpolation, worldToPixel } from '../static/js/heightmap.js';
import { calculateFiringSolution } from '../static/js/ballistics.js';

// Get the directory path for resolving relative paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Load heightmap data from file system (Node.js version)
 */
async function loadHeightmapFromFile(mapName) {
  const heightmapPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'heightmap.json');
  const data = await readFile(heightmapPath, 'utf-8');
  const heightmapData = JSON.parse(data);
  
  // Convert to Uint16Array for consistency with production code
  heightmapData.data = new Uint16Array(heightmapData.data);
  
  return heightmapData;
}

/**
 * Load metadata from file system (Node.js version)
 */
async function loadMetadataFromFile(mapName) {
  const metadataPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'metadata.json');
  const data = await readFile(metadataPath, 'utf-8');
  return JSON.parse(data);
}

/**
 * Get elevation at XY coordinates
 */
function getElevation(x, y, heightmapData, heightScale, mapSize, resolution) {
  // Clamp to bounds
  x = Math.max(0, Math.min(mapSize, x));
  y = Math.max(0, Math.min(mapSize, y));
  
  // Convert world to pixel coordinates
  const { pixelX, pixelY } = worldToPixel(x, y, mapSize, resolution);
  
  // Get interpolated height value
  const rawValue = bilinearInterpolation(heightmapData, pixelX, pixelY, resolution, resolution);
  
  // Apply height scale formula
  const elevation = (rawValue / 65535.0) * heightScale;
  
  return elevation;
}

/**
 * Test the full pipeline with test_bootcamp map
 * This is a small map (513×513 resolution) suitable for testing
 */
export async function runIntegrationTests() {
  console.log('  Loading test_bootcamp map data...');
  
  // Load map data
  const mapName = 'test_bootcamp';
  let heightmap, metadata;
  
  try {
    [heightmap, metadata] = await Promise.all([
      loadHeightmapFromFile(mapName),
      loadMetadataFromFile(mapName)
    ]);
  } catch (error) {
    console.warn(`  Warning: Could not load ${mapName} map data. Integration tests skipped.`);
    console.warn(`  Error: ${error.message}`);
    return;
  }
  
  // Calculate grid scale from map size
  const gridScale = calculateGridScale(metadata.map_size);
  
  console.log(`  Map: ${mapName}`);
  console.log(`  Map size: ${metadata.map_size}m`);
  console.log(`  Grid scale: ${gridScale.toFixed(2)}m`);
  console.log(`  Height scale: ${metadata.height_scale}m`);
  console.log(`  Resolution: ${metadata.heightmap_resolution}×${metadata.heightmap_resolution}`);
  
  // Helper function to get elevation
  const getElevationAt = (x, y) => getElevation(
    x, y, 
    heightmap.data, 
    metadata.height_scale, 
    metadata.map_size, 
    heightmap.resolution
  );
  
  // Test Case 1: Basic pipeline with valid positions
  console.log('\n  Test 1: Basic firing solution pipeline');
  
  const mortarGridRef = 'D6-5'; // Center of map approximately
  const targetGridRef = 'F8-5';
  
  // Convert grid references to XY coordinates
  const mortarXY = gridRefToXY(mortarGridRef, gridScale);
  const targetXY = gridRefToXY(targetGridRef, gridScale);
  
  assert(mortarXY !== null, 'Mortar grid reference should parse successfully');
  assert(targetXY !== null, 'Target grid reference should parse successfully');
  
  console.log(`  Mortar: ${mortarGridRef} → (${mortarXY.x.toFixed(1)}, ${mortarXY.y.toFixed(1)})`);
  console.log(`  Target: ${targetGridRef} → (${targetXY.x.toFixed(1)}, ${targetXY.y.toFixed(1)})`);
  
  // Get elevations from heightmap
  const mortarZ = getElevationAt(mortarXY.x, mortarXY.y);
  const targetZ = getElevationAt(targetXY.x, targetXY.y);
  
  assert(typeof mortarZ === 'number', 'Mortar elevation should be a number');
  assert(typeof targetZ === 'number', 'Target elevation should be a number');
  assert(mortarZ >= 0 && mortarZ <= metadata.height_scale, 'Mortar elevation should be within height scale');
  assert(targetZ >= 0 && targetZ <= metadata.height_scale, 'Target elevation should be within height scale');
  
  console.log(`  Mortar elevation: ${mortarZ.toFixed(2)}m`);
  console.log(`  Target elevation: ${targetZ.toFixed(2)}m`);
  
  // Calculate firing solution
  const mortar = { x: mortarXY.x, y: mortarXY.y, z: mortarZ };
  const target = { x: targetXY.x, y: targetXY.y, z: targetZ };
  
  const solution = calculateFiringSolution(mortar, target);
  
  assert(solution !== null, 'Firing solution should not be null');
  assert(typeof solution.distance === 'number', 'Distance should be a number');
  assert(typeof solution.azimuth === 'number', 'Azimuth should be a number');
  assert(typeof solution.heightDelta === 'number', 'Height delta should be a number');
  
  console.log(`  Distance: ${solution.distance.toFixed(2)}m`);
  console.log(`  Azimuth: ${solution.azimuth.toFixed(2)}°`);
  console.log(`  Height delta: ${solution.heightDelta.toFixed(2)}m`);
  
  if (solution.valid) {
    assert(typeof solution.elevationMils === 'number', 'Elevation in mils should be a number');
    assert(typeof solution.elevationDegrees === 'number', 'Elevation in degrees should be a number');
    assert(typeof solution.timeOfFlight === 'number', 'Time of flight should be a number');
    
    console.log(`  Elevation: ${solution.elevationMils.toFixed(2)} mils (${solution.elevationDegrees.toFixed(2)}°)`);
    console.log(`  Time of flight: ${solution.timeOfFlight.toFixed(2)}s`);
    console.log(`  Status: ${solution.status}`);
    
    // Validate ranges
    assert(solution.distance > 0, 'Distance should be positive');
    assert(solution.azimuth >= 0 && solution.azimuth < 360, 'Azimuth should be 0-360°');
    assert(solution.elevationMils >= 0 && solution.elevationMils <= 3200, 'Elevation should be 0-3200 mils (0-180°)');
    assert(solution.timeOfFlight > 0, 'Time of flight should be positive');
  } else {
    console.log(`  Status: ${solution.status} - ${solution.message}`);
  }
  
  // Test Case 2: Multiple grid references on same map
  console.log('\n  Test 2: Multiple firing solutions');
  
  const testCases = [
    { mortar: 'A1-5', target: 'A2-5', description: 'Short range (1 grid square)' },
    { mortar: 'D6-5', target: 'J6-5', description: 'Medium range (horizontal)' },
    { mortar: 'G1-5', target: 'G13-5', description: 'Long range (vertical)' }
  ];
  
  for (const testCase of testCases) {
    const mXY = gridRefToXY(testCase.mortar, gridScale);
    const tXY = gridRefToXY(testCase.target, gridScale);
    
    if (!mXY || !tXY) continue;
    
    const mZ = getElevationAt(mXY.x, mXY.y);
    const tZ = getElevationAt(tXY.x, tXY.y);
    
    const sol = calculateFiringSolution(
      { x: mXY.x, y: mXY.y, z: mZ },
      { x: tXY.x, y: tXY.y, z: tZ }
    );
    
    console.log(`  ${testCase.description}: ${testCase.mortar} → ${testCase.target}`);
    console.log(`    Distance: ${sol.distance.toFixed(2)}m, Azimuth: ${sol.azimuth.toFixed(2)}°`);
    
    if (sol.valid) {
      console.log(`    Elevation: ${sol.elevationMils.toFixed(2)} mils, TOF: ${sol.timeOfFlight.toFixed(2)}s`);
    } else {
      console.log(`    Status: ${sol.status}`);
    }
    
    // Basic validation
    assert(sol.distance >= 0, 'Distance should be non-negative');
    assert(sol.azimuth >= 0 && sol.azimuth < 360, 'Azimuth should be valid');
  }
  
  // Test Case 3: Edge cases
  console.log('\n  Test 3: Edge cases');
  
  // Same position (zero distance)
  const samePos = { x: 1000, y: 1000, z: 100 };
  const zeroDistSolution = calculateFiringSolution(samePos, samePos);
  
  assert(!zeroDistSolution.valid, 'Zero distance should be invalid');
  assert(zeroDistSolution.status === 'TOO_CLOSE', 'Zero distance should return TOO_CLOSE status');
  console.log(`  Zero distance: ${zeroDistSolution.status}  OK `);
  
  // Out of range (2000m on flat ground is beyond physical max)
  const outOfRangeSolution = calculateFiringSolution(
    { x: 0, y: 0, z: 100 },
    { x: 2000, y: 0, z: 100 }
  );
  
  assert(!outOfRangeSolution.valid, 'Out of range should be invalid');
  // At 2000m, discriminant is negative (physically unreachable)
  assert(outOfRangeSolution.status === 'UNREACHABLE', 'Should return UNREACHABLE status');
  console.log(`  Out of range: ${outOfRangeSolution.status}  OK `);
  
  // Test Case 4: Validate calculation consistency
  console.log('\n  Test 4: Calculation consistency');
  
  // Calculate same solution multiple times - should be identical
  const refMortar = { x: 1000, y: 1000, z: 50 };
  const refTarget = { x: 1500, y: 1300, z: 80 };
  
  const sol1 = calculateFiringSolution(refMortar, refTarget);
  const sol2 = calculateFiringSolution(refMortar, refTarget);
  const sol3 = calculateFiringSolution(refMortar, refTarget);
  
  assert.strictEqual(sol1.distance, sol2.distance, 'Distance should be consistent');
  assert.strictEqual(sol1.azimuth, sol2.azimuth, 'Azimuth should be consistent');
  assert.strictEqual(sol1.elevationMils, sol2.elevationMils, 'Elevation should be consistent');
  assert.strictEqual(sol1.timeOfFlight, sol2.timeOfFlight, 'TOF should be consistent');
  
  assert.strictEqual(sol2.distance, sol3.distance, 'Distance should be consistent (2nd iteration)');
  assert.strictEqual(sol2.azimuth, sol3.azimuth, 'Azimuth should be consistent (2nd iteration)');
  
  console.log(`  Consistency check: All calculations identical  OK `);
  
  // Test Case 5: Grid conversion round-trip
  console.log('\n  Test 5: Grid conversion round-trip');
  
  const originalXY = gridRefToXY('E7-3', gridScale);
  assert(originalXY !== null, 'Grid reference should parse');
  
  // Elevation should be retrievable
  const elevation = getElevationAt(originalXY.x, originalXY.y);
  assert(typeof elevation === 'number', 'Elevation should be retrievable');
  assert(!isNaN(elevation), 'Elevation should not be NaN');
  
  console.log(`  E7-3 → (${originalXY.x.toFixed(1)}, ${originalXY.y.toFixed(1)}) → elevation ${elevation.toFixed(2)}m  OK `);
  
  console.log('\n  Integration tests completed successfully!');
}

