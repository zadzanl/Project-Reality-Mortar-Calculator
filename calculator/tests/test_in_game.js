import assert from 'node:assert';
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { gridRefToXY, calculateGridScale } from '../static/js/coordinates.js';
import { calculateFiringSolution } from '../static/js/ballistics.js';
import { assertApprox } from './assertApprox.js';

// Directory helpers
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const SAMPLE_FILE = join(__dirname, 'in_game_vectors.json');

/**
 * Load vectors from JSON file
 */
async function loadInGameVectors() {
  try {
    const raw = await readFile(SAMPLE_FILE, 'utf-8');
    const data = JSON.parse(raw);
    return data;
  } catch (err) {
    // File not found or invalid JSON
    return null;
  }
}

/**
 * Run in-game measurement comparisons
 */
export async function runInGameTests() {
  console.log('\n  Loading in_game_vectors.json...');
  const vectors = await loadInGameVectors();
  if (!vectors || vectors.length === 0) {
    console.warn('  No in-game vectors found (calculator/tests/in_game_vectors.json). Skipping in-game validation.');
    return;
  }

  for (const v of vectors) {
    const {
      mapName,
      mortarGridRef,
      targetGridRef,
      expectedDistance,
      expectedAzimuth,
      expectedElevationMils,
      tolerance = { distance: 10, azimuth: 2, elevationMils: 1 }
    } = v;

    console.log(`\n  Testing map: ${mapName} | ${mortarGridRef} -> ${targetGridRef}`);

    // Load map data (Node.js file-loader version)
    const heightmapPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'heightmap.json.gz');
    const metadataPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'metadata.json');
    const [heightmapData, metadata] = await Promise.all([
      readFile(heightmapPath).then(compressed => {
        const decompressed = gunzipSync(compressed);
        const parsed = JSON.parse(decompressed.toString('utf-8'));
        parsed.data = new Uint16Array(parsed.data);
        return parsed;
      }),
      readFile(metadataPath, 'utf-8').then(data => JSON.parse(data))
    ]);
    const gridScale = calculateGridScale(metadata.map_size);

    const mortarXY = gridRefToXY(mortarGridRef, gridScale);
    const targetXY = gridRefToXY(targetGridRef, gridScale);

    if (!mortarXY || !targetXY) {
      console.warn(`  Skipping test (invalid grid ref: ${mortarGridRef}, ${targetGridRef})`);
      continue;
    }

    // Get elevations
    // Node-based elevation retrieval
    const worldToPixel = (x, y, mapSize, resolution) => {
      const pixelsPerMeter = (resolution - 1) / mapSize;
      return { pixelX: x * pixelsPerMeter, pixelY: y * pixelsPerMeter };
    };
    const getElevationAtXY = (x, y) => {
      const { pixelX, pixelY } = worldToPixel(x, y, metadata.map_size, heightmapData.resolution);
      const rawValue = (function bilinear() {
        const x0 = Math.floor(pixelX);
        const y0 = Math.floor(pixelY);
        const x1 = Math.min(x0 + 1, heightmapData.resolution - 1);
        const y1 = Math.min(y0 + 1, heightmapData.resolution - 1);
        const fx = pixelX - x0;
        const fy = pixelY - y0;
        const index = (xx, yy) => yy * heightmapData.resolution + xx;
        const tl = heightmapData.data[index(x0, y0)];
        const tr = heightmapData.data[index(x1, y0)];
        const bl = heightmapData.data[index(x0, y1)];
        const br = heightmapData.data[index(x1, y1)];
        const top = tl + fx * (tr - tl);
        const bottom = bl + fx * (br - bl);
        return top + fy * (bottom - top);
      })();
      return (rawValue / 65535.0) * metadata.height_scale;
    };
    const mortarZ = getElevationAtXY(mortarXY.x, mortarXY.y);
    const targetZ = getElevationAtXY(targetXY.x, targetXY.y);

    // Calculate solution
    const solution = calculateFiringSolution(
      { x: mortarXY.x, y: mortarXY.y, z: mortarZ },
      { x: targetXY.x, y: targetXY.y, z: targetZ }
    );

    // If solution invalid, fail the test unless expected status
    if (!solution.valid) {
      throw new Error(`  In-game test failed: Unreachable target - ${solution.status} - ${solution.message}`);
    }

    // Compare
    if (expectedDistance !== undefined) {
      assertApprox(solution.distance, expectedDistance, tolerance.distance, `Distance mismatch: ${solution.distance} vs ${expectedDistance}`);
    }

    if (expectedAzimuth !== undefined) {
      assertApprox(solution.azimuth, expectedAzimuth, tolerance.azimuth, `Azimuth mismatch: ${solution.azimuth} vs ${expectedAzimuth}`);
    }

    if (expectedElevationMils !== undefined) {
      assertApprox(solution.elevationMils, expectedElevationMils, tolerance.elevationMils, `Elevation mismatch: ${solution.elevationMils} vs ${expectedElevationMils}`);
    }

    console.log('   OK  Match within tolerance');
  }

  console.log('\n  In-game validation tests completed.');
}

// Run if executed directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runInGameTests().catch(err => {
    console.error('In-game tests failed:', err);
    process.exit(1);
  });
}
