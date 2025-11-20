import assert from 'node:assert';
import { assertApprox } from './assertApprox.js';
import {
  parseGridReference,
  gridToXY,
  xyToGrid,
  gridRefToXY,
  calculateGridScale
  ,getRowLabelCenterX
} from '../static/js/coordinates.js';

export async function runCoordinatesTests() {
  // parseGridReference
  const p = parseGridReference('D6-7');
  assert.ok(p, 'Parse D6-7');
  assert.strictEqual(p.column, 'D');
  assert.strictEqual(p.row, 6);
  assert.strictEqual(p.keypad, 7);

  // parse NATO word (long form)
  const p2 = parseGridReference('Delta 6-7');
  assert.ok(p2, 'Parse Delta 6-7');
  assert.strictEqual(p2.column, 'D');
  assert.strictEqual(p2.row, 6);
  assert.strictEqual(p2.keypad, 7);

  // gridToXY and gridRefToXY - use calculateGridScale for consistency with metadata
  const gridScale = calculateGridScale(2048);
  const pos = gridToXY('D', 6, 7, gridScale);
  assert.strictEqual(typeof pos.x, 'number');
  assert.strictEqual(typeof pos.y, 'number');
  const pos2 = gridRefToXY('D6-7', gridScale);
  assertApprox(pos.x, pos2.x, 0.01);
  assertApprox(pos.y, pos2.y, 0.01);

  // xyToGrid reverse conversion
  const xy = { x: pos.x + 10, y: pos.y + 15 };
  const grid = xyToGrid(xy.x, xy.y, gridScale);
  assert.ok(grid.column, 'Has column');
  assert.ok(grid.row >= 1 && grid.row <= 13, 'Row in bounds');
  assert.ok(grid.keypad >= 1 && grid.keypad <= 9, 'Keypad in bounds');

  // grid scale calculation (gridScale should equal mapSize/13)
  assertApprox(calculateGridScale(2048), 2048 / 13, 0.001);
  assertApprox(calculateGridScale(1024), 1024 / 13, 0.001);
  assertApprox(calculateGridScale(4096), 4096 / 13, 0.001);

  // getRowLabelCenterX should place labels near the right edge
  const scale1 = calculateGridScale(1024);
  const scale2 = calculateGridScale(2048);
  const scale3 = calculateGridScale(4096);
  // Expect center X to be mapSize - (gridScale * 0.15)
  assertApprox(getRowLabelCenterX(1024, scale1), 1024 - (scale1 * 0.15), 0.0001);
  assertApprox(getRowLabelCenterX(2048, scale2), 2048 - (scale2 * 0.15), 0.0001);
  assertApprox(getRowLabelCenterX(4096, scale3), 4096 - (scale3 * 0.15), 0.0001);
}
