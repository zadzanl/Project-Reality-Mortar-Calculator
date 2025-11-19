import assert from 'node:assert';
import { assertApprox } from './assertApprox.js';
import { bilinearInterpolation, worldToPixel, getElevation } from '../static/js/heightmap.js';

export async function runHeightmapTests() {
  // Synthetic small heightmap (3x3) with center pixel = max (65535)
  const resolution = 3;
  const width = resolution;
  const height = resolution;
  const centerMax = 65535;
  const heightmapData = [
    0, 0, 0,
    0, centerMax, 0,
    0, 0, 0
  ];

  // worldToPixel on mapSize 2 -> pixelsPerMeter = (resolution -1)/mapSize = 1
  const mapSize = 2;
  const p = worldToPixel(1, 1, mapSize, resolution);
  assert.strictEqual(p.pixelX, 1);
  assert.strictEqual(p.pixelY, 1);

  // direct pixel interpolation at integer center should yield 65535
  const valueCenter = bilinearInterpolation(heightmapData, 1, 1, width, height);
  assert.strictEqual(Math.round(valueCenter), centerMax);

  // fractional interpolation (1.5, 1.5) -> approx 16383.75
  const valueFraction = bilinearInterpolation(heightmapData, 1.5, 1.5, width, height);
  assertApprox(valueFraction, 16383.75, 1, `fractional interpolation: ${valueFraction}`);

  // getElevation should convert to meters correctly for heightScale
  const heightScale = 300; // meters
  const elevation = getElevation(1, 1, heightmapData, heightScale, mapSize, resolution);
  assertApprox(elevation, heightScale, 0.0001, 'getElevation at center should equal heightScale');
}
