#!/usr/bin/env node
/**
 * Firing-solution fixture for processor/baseline.py (OpenSpec change
 * reduce-map-data-footprint, task 1.2). Headless Node ESM script: loads the
 * pure calculator modules (no browser APIs), reads a map's
 * heightmap.json.gz + metadata.json, and computes firing solutions for three
 * fixed mortar/target grid-reference pairs spread across the map.
 *
 * Usage: node processor/baseline_firing.mjs <map_dir>
 * Prints one JSON document to stdout: {"map": <name>, "pairs": [...]}.
 * Exit 0 on success; non-zero with the error on stderr otherwise (baseline.py
 * then records the fixture as "unavailable" and continues -- documented
 * known ceiling, not a hard failure).
 *
 * Elevation formula (never change the 65535):
 *   elevation_m = (pixel_value / 65535.0) * height_scale
 * with bilinear interpolation between pixels, mirroring
 * calculator/tests/test_in_game.js (which mirrors heightmap.js).
 */

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { gunzipSync } from 'node:zlib';
import { gridRefToXY, calculateGridScale } from '../calculator/static/js/coordinates.js';
import { calculateFiringSolution } from '../calculator/static/js/ballistics.js';

// Fixed pairs, valid for any map size (grid refs always span the 13x13 grid).
// Max separation is 2 columns + 2 rows, so even on a 4096 m map the distance
// stays ~890 m, well inside the 1500 m maximum range.
const PAIRS = [
  ['C4-5', 'E5-5'],
  ['H7-5', 'J9-5'],
  ['F11-5', 'D10-5'],
];

function round6(value) {
  return value === null || value === undefined ? null : Math.round(value * 1e6) / 1e6;
}

async function main() {
  const mapDir = process.argv[2];
  if (!mapDir) {
    console.error('usage: node baseline_firing.mjs <map_dir>');
    process.exit(2);
  }

  const [heightmap, metadata] = await Promise.all([
    readFile(join(mapDir, 'heightmap.json.gz')).then(compressed => {
      const parsed = JSON.parse(gunzipSync(compressed).toString('utf-8'));
      parsed.data = new Uint16Array(parsed.data);
      return parsed;
    }),
    readFile(join(mapDir, 'metadata.json'), 'utf-8').then(text => JSON.parse(text)),
  ]);
  const gridScale = calculateGridScale(metadata.map_size);

  // Mirrors the Node elevation lookup in calculator/tests/test_in_game.js.
  const getElevationAtXY = (x, y) => {
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
    const rawValue = top + fy * (bottom - top);
    return (rawValue / 65535.0) * metadata.height_scale;
  };

  const pairs = [];
  for (const [mortarRef, targetRef] of PAIRS) {
    const mortarXY = gridRefToXY(mortarRef, gridScale);
    const targetXY = gridRefToXY(targetRef, gridScale);
    if (!mortarXY || !targetXY) {
      pairs.push({ mortar: mortarRef, target: targetRef, valid: false, status: 'BAD_GRID_REF' });
      continue;
    }
    const solution = calculateFiringSolution(
      { x: mortarXY.x, y: mortarXY.y, z: getElevationAtXY(mortarXY.x, mortarXY.y) },
      { x: targetXY.x, y: targetXY.y, z: getElevationAtXY(targetXY.x, targetXY.y) }
    );
    pairs.push({
      mortar: mortarRef,
      target: targetRef,
      distance: round6(solution.distance),
      azimuth: round6(solution.azimuth),
      heightDelta: round6(solution.heightDelta),
      elevationMils: round6(solution.elevationMils),
      elevationDegrees: round6(solution.elevationDegrees),
      timeOfFlight: round6(solution.timeOfFlight),
      valid: solution.valid,
      status: solution.status,
    });
  }
  console.log(JSON.stringify({ map: metadata.map_name, pairs }));
}

main().catch(err => {
  console.error(String((err && err.stack) || err));
  process.exit(1);
});
