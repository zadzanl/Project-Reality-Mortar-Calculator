import assert from 'node:assert';
import { assertApprox } from './assertApprox.js';
import {
  calculateDistance,
  calculateAzimuth,
  calculateElevationAngle,
  radiansToMils,
  radiansToDegrees,
  milsToDegrees,
  calculateTimeOfFlight,
  validateFiringSolution,
  calculateFiringSolution,
  PR_PHYSICS
} from '../static/js/ballistics.js';

export async function runBallisticsTests() {
  // Distance test
  const dist = calculateDistance(0, 0, 300, 400);
  assertApprox(dist, 500, 0.5, 'calculateDistance should return ~500 for 3-4-5 triangle');

  // Azimuth tests
  assert.strictEqual(calculateAzimuth(0, 0, 100, 0), 90, 'Azimuth East');
  assert.strictEqual(calculateAzimuth(0, 0, 0, 100), 180, 'Azimuth South');
  assert.strictEqual(calculateAzimuth(0, 0, 0, -100), 0, 'Azimuth North (negative Y)');

  // Elevation test: example scenario in spec (approx check)
  const d = calculateDistance(1000, 1000, 1500, 1300); // 583.095...
  const dz = 120 - 50; // 70
  const elev = calculateElevationAngle(d, dz);
  assert.ok(elev !== null, 'Elevation angle should compute for valid geometry');
  assert.ok(elev > 0 && elev < Math.PI / 2, 'Elevation in valid range (0-90°)');

  // Radians conversions
  const quarter = Math.PI / 4;
  const mils = radiansToMils(quarter);
  // π/4 radians = 800 mils (6400 mils per circle -> π/2 = 1600 mils; π/4 = 800 mils)
  assertApprox(mils, 800, 1, `radiansToMils(pi/4) -> ~800`);
  const deg = radiansToDegrees(quarter);
  assertApprox(deg, 45, 0.0001, '45° check');
  assert.ok(Math.abs(milsToDegrees(1600) - 90) < 0.01, '1600 mils -> 90°');

  // Time of flight sanity
  const tof = calculateTimeOfFlight(d, elev, dz);
  assert.ok(Number.isFinite(tof) && tof > 0 && tof < 60, `TOF should be positive and < 60s (got ${tof})`);

  // Additional check: TOF should be consistent with horizontal time D/(v*cos(phi))
  const v0 = PR_PHYSICS.PROJECTILE_VELOCITY;
  const horizontalTime = d / (v0 * Math.cos(elev));
  assertApprox(tof, horizontalTime, 0.1, 'Time-of-flight matches horizontal time D/(v*cos(phi))');

  // For ΔZ = 0, TOF should approximate 2*v*sin(phi)/g
  const d0 = 600;
  const elev0 = calculateElevationAngle(d0, 0);
  assert.ok(elev0 !== null, 'Elevation for ΔZ=0 computed');
  const tof0 = calculateTimeOfFlight(d0, elev0, 0);
  const approx0 = 2 * v0 * Math.sin(elev0) / PR_PHYSICS.GRAVITY;
  assertApprox(tof0, approx0, 0.1, 'TOF approximates 2*v*sin(phi)/g for ΔZ=0');

  // calculateFiringSolution basic object shape
  const sol = calculateFiringSolution({ x: 1000, y: 1000, z: 50 }, { x: 1500, y: 1300, z: 120 });
  assert.ok(sol.distance && sol.azimuth !== undefined && sol.elevationRadians !== null, 'calculateFiringSolution returns fields');
  assertApprox(sol.distance, d, 1, 'distance approx match');

  // Validate constants
  assert.strictEqual(PR_PHYSICS.GRAVITY, 14.86, 'Gravity constant must be 14.86');
  assert.strictEqual(PR_PHYSICS.PROJECTILE_VELOCITY, 148.64, 'Projectile velocity');

  // validateFiringSolution edge cases
  const overRange = validateFiringSolution(1600, 0);
  assert.ok(!overRange.valid && overRange.status === 'OUT_OF_RANGE', 'DIST > MAX -> OUT_OF_RANGE');

  const tooClose = validateFiringSolution(0.5, 0);
  assert.ok(!tooClose.valid && tooClose.status === 'TOO_CLOSE', 'distance < 1m -> TOO_CLOSE');

  const extreme = validateFiringSolution(1000, 300);
  assert.ok(extreme.valid && extreme.status === 'EXTREME_ELEVATION', 'Large elevation -> EXTREME_ELEVATION');
}
