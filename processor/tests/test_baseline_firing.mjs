/**
 * Regression tests for processor/baseline_firing.mjs
 * (OpenSpec change reduce-map-data-footprint, review-001 finding B-01).
 *
 * Guards the fixture's elevation path: the fixture MUST sample elevation
 * through production calculator/static/js/heightmap.js::getElevation, which
 * flips Y (heightmap storage row 0 = south; world Y=0 = north). The pre-fix
 * fixture interpolated the raw south-first array WITHOUT the flip and
 * produced non-production firing solutions (tripwire evidence: 4/6 adak
 * samples mismatched production by up to ~47.6 m, recorded in
 * artifacts/impl-002b.md).
 *
 * Uses a synthetic asymmetric 4x4 south-first heightmap written to a temp
 * directory; no files under processed_maps/ or raw_map_data/ are touched.
 *
 * Run: node --test processor/tests/test_baseline_firing.mjs
 */

import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { loadMap, computePairs, elevationAt } from '../baseline_firing.mjs';
import { getElevation } from '../../calculator/static/js/heightmap.js';
import { calculateFiringSolution } from '../../calculator/static/js/ballistics.js';
import { gridRefToXY, calculateGridScale } from '../../calculator/static/js/coordinates.js';

const BASELINE_SCRIPT = fileURLToPath(new URL('../baseline_firing.mjs', import.meta.url));

// Synthetic 4x4 heightmap, SOUTH-FIRST storage (row 0 = south), chosen so
// every row differs by 10000 raw units: a missing Y flip cannot go unnoticed.
// value(yy, xx) = xx*100 + yy*10000  (max 30300, fits uint16).
const RESOLUTION = 4;
const MAP_SIZE = 3000; // meters; pixelsPerMeter = (4-1)/3000 = 0.001
const HEIGHT_SCALE = 100;
const RAW = [];
for (let yy = 0; yy < RESOLUTION; yy++) {
  for (let xx = 0; xx < RESOLUTION; xx++) {
    RAW.push(xx * 100 + yy * 10000);
  }
}
const METADATA = {
  map_name: 'synthetic_test',
  map_size: MAP_SIZE,
  height_scale: HEIGHT_SCALE,
  grid_scale: MAP_SIZE / 13,
  resolution: RESOLUTION,
};

const rawToMeters = raw => (raw / 65535.0) * HEIGHT_SCALE;

let mapDir;

before(async () => {
  mapDir = await mkdtemp(join(tmpdir(), 'baseline-firing-'));
  const heightmapJson = {
    resolution: RESOLUTION,
    width: RESOLUTION,
    height: RESOLUTION,
    format: 'uint16',
    data: RAW,
  };
  await writeFile(join(mapDir, 'heightmap.json.gz'), gzipSync(JSON.stringify(heightmapJson)));
  await writeFile(join(mapDir, 'metadata.json'), JSON.stringify(METADATA));
});

after(async () => {
  await rm(mapDir, { recursive: true, force: true });
});

test('loader gunzips heightmap and converts data to Uint16Array (16-bit)', async () => {
  const { heightmap, metadata } = await loadMap(mapDir);
  assert.equal(heightmap.resolution, RESOLUTION);
  assert.equal(heightmap.format, 'uint16');
  assert.ok(heightmap.data instanceof Uint16Array, 'data must be Uint16Array');
  assert.equal(heightmap.data.length, RESOLUTION * RESOLUTION);
  assert.equal(heightmap.data[13], 30100); // row 3, col 1
  assert.equal(metadata.map_size, MAP_SIZE);
  assert.equal(metadata.height_scale, HEIGHT_SCALE);
});

test('elevationAt matches production getElevation with Y flip (integer pixels, Y=0 edge)', async () => {
  const { heightmap, metadata } = await loadMap(mapDir);
  // x=1000 -> pixelX=1.0 exactly. y=0 (north edge) must read STORAGE ROW 3.
  assert.equal(elevationAt(heightmap, metadata, 1000, 0), rawToMeters(30100));
  // y=map_size (south edge) must read STORAGE ROW 0.
  assert.equal(elevationAt(heightmap, metadata, 1000, MAP_SIZE), rawToMeters(100));
  // Corner (0,0): north-west -> storage row 3, col 0.
  assert.equal(elevationAt(heightmap, metadata, 0, 0), rawToMeters(30000));
  // Sanity: identical to calling production getElevation directly.
  assert.equal(
    elevationAt(heightmap, metadata, 1000, 0),
    getElevation(1000, 0, heightmap.data, HEIGHT_SCALE, MAP_SIZE, RESOLUTION)
  );
});

test('elevationAt bilinear interpolation at non-center fractional pixel', async () => {
  const { heightmap, metadata } = await loadMap(mapDir);
  // x=1500,y=1500 -> pixel (1.5, 1.5); flipped y = 3 - 1.5 = 1.5, so storage
  // rows 1 and 2, cols 1 and 2: 10100, 10200, 20100, 20200 -> 15150 midpoint.
  assert.equal(elevationAt(heightmap, metadata, 1500, 1500), rawToMeters(15150));
  // y=1200 -> pixelY=1.2, flipped=1.8 -> rows 1,2 with fy=0.8:
  // 10150 + 0.8*(20150-10150) = 18150. Unflipped (fy=0.2) would give 12150;
  // rows differ by exactly 10000 so the two paths cannot coincide here.
  assert.equal(elevationAt(heightmap, metadata, 1500, 1200), rawToMeters(18150));
  assert.notEqual(elevationAt(heightmap, metadata, 1500, 1200), rawToMeters(12150));
});

test('computePairs output matches full production firing solution at fixed grid refs', async () => {
  const { heightmap, metadata } = await loadMap(mapDir);
  const gridScale = calculateGridScale(MAP_SIZE);
  const testPairs = [
    ['C4-5', 'E5-5'], // mid-map, fractional pixels, ~516 m apart
    ['A1-7', 'C2-9'], // mortar exactly at (0,0) north-west corner edge
  ];
  const pairs = computePairs(heightmap, metadata, testPairs);
  assert.equal(pairs.length, testPairs.length);

  let validCount = 0;
  for (let i = 0; i < testPairs.length; i++) {
    const [mRef, tRef] = testPairs[i];
    const mXY = gridRefToXY(mRef, gridScale);
    const tXY = gridRefToXY(tRef, gridScale);
    const expected = calculateFiringSolution(
      { x: mXY.x, y: mXY.y, z: getElevation(mXY.x, mXY.y, heightmap.data, HEIGHT_SCALE, MAP_SIZE, RESOLUTION) },
      { x: tXY.x, y: tXY.y, z: getElevation(tXY.x, tXY.y, heightmap.data, HEIGHT_SCALE, MAP_SIZE, RESOLUTION) }
    );
    const round6 = v => (v === null || v === undefined ? null : Math.round(v * 1e6) / 1e6);
    assert.deepEqual(pairs[i], {
      mortar: mRef,
      target: tRef,
      distance: round6(expected.distance),
      azimuth: round6(expected.azimuth),
      heightDelta: round6(expected.heightDelta),
      elevationMils: round6(expected.elevationMils),
      elevationDegrees: round6(expected.elevationDegrees),
      timeOfFlight: round6(expected.timeOfFlight),
      valid: expected.valid,
      status: expected.status,
    });
    if (expected.valid) validCount++;
  }
  assert.ok(validCount >= 1, 'at least one synthetic pair must produce a valid solution');
});

test('regression guard: pre-fix unflipped sampling disagrees with fixture on asymmetric map', async () => {
  const { heightmap, metadata } = await loadMap(mapDir);
  // Exact copy of the pre-fix baseline_firing.mjs elevation formula (NO Y flip).
  const oldUnflipped = (x, y) => {
    const pixelsPerMeter = (heightmap.resolution - 1) / metadata.map_size;
    const pixelX = x * pixelsPerMeter;
    const pixelY = y * pixelsPerMeter;
    const x0 = Math.floor(pixelX);
    const y0 = Math.floor(pixelY);
    const x1 = Math.min(x0 + 1, heightmap.resolution - 1);
    const y1 = Math.min(y0 + 1, heightmap.resolution - 1);
    const fx = pixelX - x0;
    const fy = pixelY - y0;
    const index = (xx, yy) => yy * heightmap.resolution + xx;
    const tl = heightmap.data[index(x0, y0)];
    const tr = heightmap.data[index(x1, y0)];
    const bl = heightmap.data[index(x0, y1)];
    const br = heightmap.data[index(x1, y1)];
    const top = tl + fx * (tr - tl);
    const bottom = bl + fx * (br - bl);
    return ((top + fy * (bottom - top)) / 65535.0) * metadata.height_scale;
  };

  const gridScale = calculateGridScale(MAP_SIZE);
  const mXY = gridRefToXY('C4-5', gridScale);
  const tXY = gridRefToXY('E5-5', gridScale);
  const oldDelta = oldUnflipped(tXY.x, tXY.y) - oldUnflipped(mXY.x, mXY.y);

  const [pair] = computePairs(heightmap, metadata, [['C4-5', 'E5-5']]);
  assert.notEqual(pair.heightDelta, Math.round(oldDelta * 1e6) / 1e6,
    'fixture must not use the pre-fix unflipped elevation path');
});

test('CLI interface preserved: node baseline_firing.mjs <map_dir> prints fixture JSON', () => {
  const stdout = execFileSync(process.execPath, [BASELINE_SCRIPT, mapDir], { encoding: 'utf-8' });
  const doc = JSON.parse(stdout);
  assert.equal(doc.map, 'synthetic_test');
  assert.ok(Array.isArray(doc.pairs));
  assert.equal(doc.pairs.length, 3); // default PAIRS
  for (const pair of doc.pairs) {
    assert.ok('mortar' in pair && 'target' in pair && 'valid' in pair && 'status' in pair);
    assert.ok('distance' in pair && 'azimuth' in pair && 'heightDelta' in pair);
    assert.ok('elevationMils' in pair && 'elevationDegrees' in pair && 'timeOfFlight' in pair);
  }
});
