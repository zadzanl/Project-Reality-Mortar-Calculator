import assert from 'node:assert';

export function assertApprox(actual, expected, tolerance = 0.01, message = '') {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) {
    assert.fail(message || `Non-finite value: actual=${actual}, expected=${expected}`);
  }
  const diff = Math.abs(actual - expected);
  assert.ok(diff <= tolerance, message || `Expected approx ${expected} ±${tolerance}, got ${actual} (diff=${diff})`);
}
