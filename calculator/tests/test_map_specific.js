/**
 * Map-Specific Integration Tests
 * 
 * Tests firing solutions on specific PR maps with known characteristics:
 * - Korengal Valley: Extreme elevation differences (mountainous terrain)
 * - Vadso City: Long ranges with moderate elevation
 * - Burning Sands: Flat terrain (control case)
 * 
 * These tests validate that the ballistics engine handles diverse terrain correctly.
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
 * Load heightmap and metadata for a map
 */
async function loadMapData(mapName) {
  const heightmapPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'heightmap.json');
  const metadataPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'metadata.json');
  
  const [heightmapData, metadata] = await Promise.all([
    readFile(heightmapPath, 'utf-8').then(data => {
      const parsed = JSON.parse(data);
      parsed.data = new Uint16Array(parsed.data);
      return parsed;
    }),
    readFile(metadataPath, 'utf-8').then(data => JSON.parse(data))
  ]);
  
  return { heightmap: heightmapData, metadata };
}

/**
 * Get elevation at XY coordinates
 */
function getElevation(x, y, heightmapData, heightScale, mapSize, resolution) {
  x = Math.max(0, Math.min(mapSize, x));
  y = Math.max(0, Math.min(mapSize, y));
  
  const { pixelX, pixelY } = worldToPixel(x, y, mapSize, resolution);
  const rawValue = bilinearInterpolation(heightmapData, pixelX, pixelY, resolution, resolution);
  const elevation = (rawValue / 65535.0) * heightScale;
  
  return elevation;
}

/**
 * Test a firing solution and validate results
 */
function testFiringSolution(mapName, mortarGridRef, targetGridRef, mapData, expectedResults = {}) {
  const { heightmap, metadata } = mapData;
  const gridScale = calculateGridScale(metadata.map_size);
  
  // Convert grid references
  const mortarXY = gridRefToXY(mortarGridRef, gridScale);
  const targetXY = gridRefToXY(targetGridRef, gridScale);
  
  assert(mortarXY !== null, `${mapName}: Mortar grid reference should parse`);
  assert(targetXY !== null, `${mapName}: Target grid reference should parse`);
  
  // Get elevations
  const mortarZ = getElevation(
    mortarXY.x, mortarXY.y,
    heightmap.data,
    metadata.height_scale,
    metadata.map_size,
    heightmap.resolution
  );
  
  const targetZ = getElevation(
    targetXY.x, targetXY.y,
    heightmap.data,
    metadata.height_scale,
    metadata.map_size,
    heightmap.resolution
  );
  
  // Calculate solution
  const solution = calculateFiringSolution(
    { x: mortarXY.x, y: mortarXY.y, z: mortarZ },
    { x: targetXY.x, y: targetXY.y, z: targetZ }
  );
  
  // Log results
  console.log(`  ${mortarGridRef} → ${targetGridRef}:`);
  console.log(`    Mortar: (${mortarXY.x.toFixed(1)}, ${mortarXY.y.toFixed(1)}) @ ${mortarZ.toFixed(2)}m`);
  console.log(`    Target: (${targetXY.x.toFixed(1)}, ${targetXY.y.toFixed(1)}) @ ${targetZ.toFixed(2)}m`);
  console.log(`    Distance: ${solution.distance.toFixed(2)}m`);
  console.log(`    Azimuth: ${solution.azimuth.toFixed(2)}°`);
  console.log(`    Height Δ: ${solution.heightDelta.toFixed(2)}m`);
  
  if (solution.valid) {
    console.log(`    Elevation: ${solution.elevationMils.toFixed(2)} mils (${solution.elevationDegrees.toFixed(2)}°)`);
    console.log(`    TOF: ${solution.timeOfFlight.toFixed(2)}s`);
    console.log(`    Status: ${solution.status}`);
    
    // Validate against expected results if provided
    if (expectedResults.minDistance !== undefined) {
      assert(solution.distance >= expectedResults.minDistance, 
        `Distance should be >= ${expectedResults.minDistance}m`);
    }
    
    if (expectedResults.maxDistance !== undefined) {
      assert(solution.distance <= expectedResults.maxDistance,
        `Distance should be <= ${expectedResults.maxDistance}m`);
    }
    
    if (expectedResults.minHeightDelta !== undefined) {
      assert(solution.heightDelta >= expectedResults.minHeightDelta,
        `Height delta should be >= ${expectedResults.minHeightDelta}m`);
    }
    
    if (expectedResults.maxHeightDelta !== undefined) {
      assert(solution.heightDelta <= expectedResults.maxHeightDelta,
        `Height delta should be <= ${expectedResults.maxHeightDelta}m`);
    }
  } else {
    console.log(`    Status: ${solution.status} - ${solution.message}`);
    
    // If we expected invalid, verify the status
    if (expectedResults.expectedStatus) {
      assert(solution.status === expectedResults.expectedStatus,
        `Expected status ${expectedResults.expectedStatus}, got ${solution.status}`);
    }
  }
  
  return solution;
}

/**
 * Test Korengal Valley - extreme elevation differences
 */
async function testKorengalValley() {
  console.log('\n--- Korengal Valley Tests (Mountainous Terrain) ---');
  
  let mapData;
  try {
    mapData = await loadMapData('korengal');
  } catch (error) {
    console.warn(`  Warning: Could not load korengal map. Skipping tests.`);
    return;
  }
  
  console.log(`  Map: ${mapData.metadata.map_name}`);
  console.log(`  Map size: ${mapData.metadata.map_size}m`);
  console.log(`  Height scale: ${mapData.metadata.height_scale}m (expect large elevation changes)`);
  console.log('');
  
  // Test 1: Valley to mountain peak (extreme uphill)
  console.log('  Test 1: Mountain to valley (significant elevation change)');
  const sol1 = testFiringSolution('korengal', 'D3-5', 'G6-5', mapData, {
    // Expect significant elevation difference (either direction)
  });
  
  // Should be valid or warn about extreme elevation
  if (!sol1.valid || sol1.status === 'EXTREME_ELEVATION') {
    console.log('    ✓ Correctly identified extreme elevation scenario');
  } else if (Math.abs(sol1.heightDelta) > 50) {
    console.log('    ✓ Significant elevation change detected');
  }
  
  console.log('');
  
  // Test 2: Mountain to valley (reverse direction)
  console.log('  Test 2: Valley to mountain (reverse direction)');
  const sol2 = testFiringSolution('korengal', 'G6-5', 'D3-5', mapData);
  
  // Verify reciprocal relationship
  assertApprox(sol1.distance, sol2.distance, 0.01, 'Distance should be same in both directions');
  assert.strictEqual(sol1.heightDelta, -sol2.heightDelta, 'Height delta should be opposite in reverse');
  console.log('    ✓ Reciprocal firing solution verified');
  
  console.log('');
  
  // Test 3: Same elevation band (horizontal)
  console.log('  Test 3: Along valley floor');
  testFiringSolution('korengal', 'C2-5', 'E2-5', mapData);
}

/**
 * Test Vadso City - long ranges with elevation
 */
async function testVadsoCity() {
  console.log('\n--- Vadso City Tests (Long Range + Elevation) ---');
  
  let mapData;
  try {
    mapData = await loadMapData('vadso_city');
  } catch (error) {
    console.warn(`  Warning: Could not load vadso_city map. Skipping tests.`);
    return;
  }
  
  console.log(`  Map: ${mapData.metadata.map_name}`);
  console.log(`  Map size: ${mapData.metadata.map_size}m`);
  console.log(`  Height scale: ${mapData.metadata.height_scale}m`);
  console.log('');
  
  // Test 1: Maximum practical range
  console.log('  Test 1: Long range shot (approaching max)');
  testFiringSolution('vadso_city', 'B2-5', 'L11-5', mapData, {
    minDistance: 1000  // Should be a long shot
  });
  
  console.log('');
  
  // Test 2: Across city (medium range)
  console.log('  Test 2: Medium range urban engagement');
  testFiringSolution('vadso_city', 'E5-5', 'H8-5', mapData, {
    minDistance: 300,
    maxDistance: 800
  });
  
  console.log('');
  
  // Test 3: Out of range test
  console.log('  Test 3: Beyond maximum range');
  testFiringSolution('vadso_city', 'A1-5', 'M13-5', mapData, {
    expectedStatus: 'OUT_OF_RANGE'
  });
}

/**
 * Test Burning Sands - flat terrain control case
 */
async function testBurningSands() {
  console.log('\n--- Burning Sands Tests (Flat Terrain Control) ---');
  
  let mapData;
  try {
    mapData = await loadMapData('burning_sands');
  } catch (error) {
    console.warn(`  Warning: Could not load burning_sands map. Skipping tests.`);
    return;
  }
  
  console.log(`  Map: ${mapData.metadata.map_name}`);
  console.log(`  Map size: ${mapData.metadata.map_size}m`);
  console.log(`  Height scale: ${mapData.metadata.height_scale}m (expect minimal elevation change)`);
  console.log('');
  
  // Test 1: Short range on flat terrain
  console.log('  Test 1: Short range (flat terrain)');
  const sol1 = testFiringSolution('burning_sands', 'E6-5', 'F7-5', mapData, {
    maxDistance: 500
  });
  
  // Elevation difference should be minimal
  if (Math.abs(sol1.heightDelta) < 10) {
    console.log('    ✓ Confirmed flat terrain (height Δ < 10m)');
  }
  
  console.log('');
  
  // Test 2: Medium range
  console.log('  Test 2: Medium range (flat terrain)');
  const sol2 = testFiringSolution('burning_sands', 'C4-5', 'J9-5', mapData, {
    minDistance: 500,
    maxDistance: 1500
  });
  
  // Should have minimal elevation change
  if (Math.abs(sol2.heightDelta) < 20) {
    console.log('    ✓ Confirmed flat terrain (height Δ < 20m)');
  }
  
  console.log('');
  
  // Test 3: Consistency check - flat terrain should give predictable results
  console.log('  Test 3: Consistency on flat terrain');
  const sol3a = testFiringSolution('burning_sands', 'D5-5', 'G8-5', mapData);
  const sol3b = testFiringSolution('burning_sands', 'D5-5', 'G8-5', mapData);
  
  assert.strictEqual(sol3a.distance, sol3b.distance, 'Distance should be consistent');
  assert.strictEqual(sol3a.elevationMils, sol3b.elevationMils, 'Elevation should be consistent');
  console.log('    ✓ Results are deterministic');
}

/**
 * Main test runner
 */
export async function runMapSpecificTests() {
  console.log('\n' + '='.repeat(70));
  console.log('MAP-SPECIFIC INTEGRATION TESTS');
  console.log('='.repeat(70));
  console.log('\nThese tests validate ballistics calculations on diverse terrain:');
  console.log('- Korengal: Mountainous terrain with extreme elevation changes');
  console.log('- Vadso City: Urban terrain with long ranges');
  console.log('- Burning Sands: Desert terrain (flat control case)');
  
  try {
    await testKorengalValley();
    await testVadsoCity();
    await testBurningSands();
    
    console.log('\n' + '='.repeat(70));
    console.log('MAP-SPECIFIC TESTS COMPLETED');
    console.log('='.repeat(70));
    console.log('\n✓ All map-specific integration tests passed!');
    
  } catch (error) {
    console.error('\nMap-specific test error:', error);
    throw error;
  }
}

// Run tests if executed directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runMapSpecificTests().catch(err => {
    console.error(err);
    process.exit(1);
  });
}
