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

  // Test Uint16Array compatibility
  // Convert regular array to Uint16Array
  const typedHeightmapData = new Uint16Array(heightmapData);
  
  // Test that bilinear interpolation works the same with typed array
  const typedValueCenter = bilinearInterpolation(typedHeightmapData, 1, 1, width, height);
  assert.strictEqual(Math.round(typedValueCenter), centerMax, 'Uint16Array center value should match');
  
  const typedValueFraction = bilinearInterpolation(typedHeightmapData, 1.5, 1.5, width, height);
  assertApprox(typedValueFraction, 16383.75, 1, `Uint16Array fractional interpolation: ${typedValueFraction}`);
  
  // Test that getElevation works the same with typed array
  const typedElevation = getElevation(1, 1, typedHeightmapData, heightScale, mapSize, resolution);
  assertApprox(typedElevation, heightScale, 0.0001, 'Uint16Array getElevation should match');
  
  // Verify exact equivalence between regular array and typed array results
  assert.strictEqual(valueCenter, typedValueCenter, 'Regular and typed array center values must be identical');
  assert.strictEqual(valueFraction, typedValueFraction, 'Regular and typed array fractional values must be identical');
  assert.strictEqual(elevation, typedElevation, 'Regular and typed array elevations must be identical');
}
