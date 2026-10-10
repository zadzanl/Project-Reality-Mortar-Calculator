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
 * Elevation comes from the PRODUCTION path
 * (calculator/static/js/heightmap.js::getElevation), which flips Y because
 * heightmap storage row 0 is south while world Y=0 is north. Never
 * reimplement the interpolation here (review-001 finding B-01: the previous
 * local copy skipped the Y flip and produced non-production solutions).
 * Elevation formula (never change the 65535):
 *   elevation_m = (pixel_value / 65535.0) * height_scale
 *
 * Regression coverage: processor/tests/test_baseline_firing.mjs
 * (node --test processor/tests/test_baseline_firing.mjs).
 */

import { readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { gridRefToXY, calculateGridScale } from '../calculator/static/js/coordinates.js';
import { calculateFiringSolution } from '../calculator/static/js/ballistics.js';
import { getElevation } from '../calculator/static/js/heightmap.js';

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

// Exported for processor/tests/test_baseline_firing.mjs.
export async function loadMap(mapDir) {
  const [heightmap, metadata] = await Promise.all([
    readFile(join(mapDir, 'heightmap.json.gz')).then(compressed => {
      const parsed = JSON.parse(gunzipSync(compressed).toString('utf-8'));
      parsed.data = new Uint16Array(parsed.data);
      return parsed;
    }),
    readFile(join(mapDir, 'metadata.json'), 'utf-8').then(text => JSON.parse(text)),
  ]);
  return { heightmap, metadata };
}

// Production elevation lookup (Y-flipped). Thin wrapper so the fixture and
// its tests share exactly one elevation path with the app.
export function elevationAt(heightmap, metadata, x, y) {
  return getElevation(
    x,
    y,
    heightmap.data,
    metadata.height_scale,
    metadata.map_size,
    heightmap.resolution
  );
}

// Exported for processor/tests/test_baseline_firing.mjs.
export function computePairs(heightmap, metadata, pairs = PAIRS) {
  const gridScale = calculateGridScale(metadata.map_size);

  const results = [];
  for (const [mortarRef, targetRef] of pairs) {
    const mortarXY = gridRefToXY(mortarRef, gridScale);
    const targetXY = gridRefToXY(targetRef, gridScale);
    if (!mortarXY || !targetXY) {
      results.push({ mortar: mortarRef, target: targetRef, valid: false, status: 'BAD_GRID_REF' });
      continue;
    }
    const solution = calculateFiringSolution(
      { x: mortarXY.x, y: mortarXY.y, z: elevationAt(heightmap, metadata, mortarXY.x, mortarXY.y) },
      { x: targetXY.x, y: targetXY.y, z: elevationAt(heightmap, metadata, targetXY.x, targetXY.y) }
    );
    results.push({
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
  return results;
}

async function main() {
  const mapDir = process.argv[2];
  if (!mapDir) {
    console.error('usage: node baseline_firing.mjs <map_dir>');
    process.exit(2);
  }

  const { heightmap, metadata } = await loadMap(mapDir);
  console.log(JSON.stringify({ map: metadata.map_name, pairs: computePairs(heightmap, metadata) }));
}

// Run main() only when invoked as a CLI, not when imported by tests.
const invokedAsCli = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (invokedAsCli) {
  main().catch(err => {
    console.error(String((err && err.stack) || err));
    process.exit(1);
  });
}
