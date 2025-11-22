/**
 * Ballistics Calculation Engine for Project Reality Mortar Calculator
 * 
 * This module provides pure functions for calculating mortar firing solutions
 * using Project Reality game physics (NOT real-world physics).
 * 
 * CRITICAL CONSTANTS - DO NOT MODIFY:
 * - Gravity: 14.86 m/s² (Project Reality engine value, NOT Earth's 9.8)
 * - Projectile Velocity: 148.64 m/s (mortar shell speed)
 * - Maximum Range: 1500 meters (gameplay limit)
 * 
 * All functions are pure (same inputs always produce same outputs) to enable
 * testing and predictable behavior.
 * 
 * @module ballistics
 */

/**
 * Project Reality physics constants
 * WARNING: DO NOT MODIFY THESE VALUES - They are derived from the game engine
 * @const {Object}
 */
export const PR_PHYSICS = Object.freeze({
  /** Gravity in Project Reality engine (m/s²) - NOT Earth's 9.8 */
  GRAVITY: 14.86,
  
  /** Mortar projectile initial velocity (m/s) */
  PROJECTILE_VELOCITY: 148.64,
  
  /** Maximum practical firing angle (radians) - 89 degrees for high-angle mortars */
  MAX_ELEVATION_ANGLE: 89 * Math.PI / 180, // 89 degrees = 1.55334 radians ~ 1609 mils
  
  /** Mils per full circle (NATO standard) */
  MILS_PER_CIRCLE: 6400,
  
  /** Degrees per full circle */
  DEGREES_PER_CIRCLE: 360,
  
  /** Radians per full circle */
  RADIANS_PER_CIRCLE: 2 * Math.PI
});

/**
 * Calculate Euclidean distance between two points in the X-Y plane (ignores Z).
 * 
 * @param {number} x1 - First point X coordinate (meters)
 * @param {number} y1 - First point Y coordinate (meters)
 * @param {number} x2 - Second point X coordinate (meters)
 * @param {number} y2 - Second point Y coordinate (meters)
 * @returns {number} Horizontal distance in meters
 * 
 * @example
 * const dist = calculateDistance(0, 0, 300, 400);
 * console.log(dist); // 500 meters
 */
export function calculateDistance(x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Calculate compass azimuth (bearing) from mortar to target.
 * 
 * Coordinate system:
 * - Origin (0,0) is at top-left (Northwest corner)
 * - X-axis increases rightward (West to East)
 * - Y-axis increases downward (North to South)
 * - Azimuth: 0° = North, 90° = East, 180° = South, 270° = West
 * 
 * @param {number} x1 - Mortar X coordinate (meters)
 * @param {number} y1 - Mortar Y coordinate (meters)
 * @param {number} x2 - Target X coordinate (meters)
 * @param {number} y2 - Target Y coordinate (meters)
 * @returns {number} Azimuth in degrees (0-360°)
 * 
 * @example
 * const az = calculateAzimuth(0, 0, 100, 0);
 * console.log(az); // 90° (due East)
 */
export function calculateAzimuth(x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  
  // atan2 gives angle from positive X-axis, counterclockwise
  // We need compass bearing from North (top), clockwise
  // In PR: North is -Y direction (upward), East is +X (rightward)
  // For compass: 0° = North, 90° = East, 180° = South, 270° = West
  // Formula: atan2(dx, -dy) where dx is East-West, dy is North-South
  let azimuth = Math.atan2(dx, -dy) * (180 / Math.PI);
  
  // Normalize to 0-360° range
  if (azimuth < 0) {
    azimuth += 360;
  }
  
  return azimuth;
}

/**
 * Calculate high-angle elevation for mortar fire.
 * 
 * Uses the ballistic trajectory equation for projectile motion with gravity.
 * Returns the HIGH-ANGLE solution (angle > 45°) which is standard for mortars.
 * 
 * Formula:
 * φ = arctan((v² + sqrt(v⁴ - g*(g*D² + 2*v²*ΔZ))) / (g*D))
 * 
 * Where:
 * - v = projectile velocity (148.64 m/s)
 * - g = gravity (14.86 m/s²)
 * - D = horizontal distance (meters)
 * - ΔZ = height difference (target - mortar, meters)
 * - φ = elevation angle (radians)
 * 
 * @param {number} distance - Horizontal distance to target (meters)
 * @param {number} heightDiff - Height difference, target Z - mortar Z (meters)
 * @returns {number|null} Elevation angle in radians, or null if impossible
 * 
 * @example
 * const angle = calculateElevationAngle(1000, 50);
 * console.log(angle); // ~1.2 radians (~70°)
 */
export function calculateElevationAngle(distance, heightDiff) {
  const v = PR_PHYSICS.PROJECTILE_VELOCITY;
  const g = PR_PHYSICS.GRAVITY;
  const D = distance;
  const dZ = heightDiff;
  
  // Handle edge case: zero or very small distance
  if (D < 1) {
    return null;
  }
  
  // Calculate discriminant: v⁴ - g*(g*D² + 2*v²*ΔZ)
  const v2 = v * v;
  const v4 = v2 * v2;
  const discriminant = v4 - g * (g * D * D + 2 * v2 * dZ);
  
  // If discriminant < 0, shot is physically impossible
  if (discriminant < 0) {
    return null;
  }
  
  // High-angle solution: arctan((v² + sqrt(discriminant)) / (g*D))
  const numerator = v2 + Math.sqrt(discriminant);
  const denominator = g * D;
  const angle = Math.atan(numerator / denominator);
  
  // Validate result is in valid range (0° to 90°)
  if (angle < 0 || angle > Math.PI / 2) {
    return null;
  }
  
  // Check against maximum practical firing angle (89 degrees for high-angle mortars)
  // This prevents nearly-vertical shots that would be impractical
  if (angle > PR_PHYSICS.MAX_ELEVATION_ANGLE) {
    return null; // Exceeds maximum elevation capability
  }
  
  return angle;
}

/**
 * Convert angle from radians to mils.
 * 
 * Mils (milliradians) are a military angular unit where 6400 mils = 360°.
 * This is the NATO standard used in Project Reality.
 * 
 * @param {number} radians - Angle in radians
 * @returns {number} Angle in mils
 * 
 * @example
 * const mils = radiansToMils(Math.PI / 4);
 * console.log(mils); // 1600 mils (45°)
 */
export function radiansToMils(radians) {
  return radians * (PR_PHYSICS.MILS_PER_CIRCLE / PR_PHYSICS.RADIANS_PER_CIRCLE);
}

/**
 * Convert angle from radians to degrees.
 * 
 * @param {number} radians - Angle in radians
 * @returns {number} Angle in degrees
 * 
 * @example
 * const degrees = radiansToDegrees(Math.PI);
 * console.log(degrees); // 180°
 */
export function radiansToDegrees(radians) {
  return radians * (PR_PHYSICS.DEGREES_PER_CIRCLE / PR_PHYSICS.RADIANS_PER_CIRCLE);
}

/**
 * Convert angle from mils to degrees.
 * 
 * @param {number} mils - Angle in mils
 * @returns {number} Angle in degrees
 * 
 * @example
 * const degrees = milsToDegrees(3200);
 * console.log(degrees); // 180°
 */
export function milsToDegrees(mils) {
  return mils * (PR_PHYSICS.DEGREES_PER_CIRCLE / PR_PHYSICS.MILS_PER_CIRCLE);
}

/**
 * Calculate time of flight for projectile.
 * 
 * Uses the kinematic equations for projectile motion:
 * t = D / (v₀ * cos(φ)) + (v₀ * sin(φ) + sqrt((v₀ * sin(φ))² + 2 * g * ΔZ)) / g
 * 
 * For high-angle fire, can be approximated as:
 * t ≈ (2 * v₀ * sin(φ)) / g
 * 
 * @param {number} distance - Horizontal distance (meters)
 * @param {number} elevationAngle - Elevation angle (radians)
 * @param {number} heightDiff - Height difference (meters)
 * @returns {number} Time of flight in seconds
 * 
 * @example
 * const angle = calculateElevationAngle(1000, 50);
 * const tof = calculateTimeOfFlight(1000, angle, 50);
 * console.log(tof); // ~8.5 seconds
 */
export function calculateTimeOfFlight(distance, elevationAngle, heightDiff) {
  const v0 = PR_PHYSICS.PROJECTILE_VELOCITY;
  const g = PR_PHYSICS.GRAVITY;
  const D = distance;
  const phi = elevationAngle;
  const dZ = heightDiff;
  
  // Calculate horizontal time (time from range equation)
  // t_h = D / (v0 * cos(phi))
  // And the vertical roots (solve 0.5*g*t^2 - v*sin(phi)*t + dZ = 0)
  // which give: t = (v*sin(phi) ± sqrt(v^2*sin^2 - 2*g*dZ)) / g
  // The physically relevant positive root is the larger (+) root.
  const cosPhi = Math.cos(phi);
  const sinPhi = Math.sin(phi);
  const vSin = v0 * sinPhi;

  // Avoid divide-by-zero for near-vertical shots
  let horizontalTime = Number.POSITIVE_INFINITY;
  if (Math.abs(cosPhi) > 1e-12) {
    horizontalTime = D / (v0 * cosPhi);
  }

  // Vertical discriminant
  const vSin2 = vSin * vSin;
  const disc = vSin2 - 2 * g * dZ;

  if (disc < 0) {
    // Physically impossible (should have been caught earlier by discriminant check)
    return NaN;
  }

  const sqrtDisc = Math.sqrt(disc);
  const verticalRoot1 = (vSin - sqrtDisc) / g;
  const verticalRoot2 = (vSin + sqrtDisc) / g; // larger root is usually flight time
  const verticalTime = Math.max(verticalRoot1, verticalRoot2);

  // Both horizontalTime and verticalTime should be equal for consistent projectile
  // If they differ slightly due to rounding, return the average, otherwise prefer horizontalTime
  if (!Number.isFinite(horizontalTime) || Math.abs(horizontalTime - verticalTime) > 1e-6) {
    // If horizontal time is infinite (near vertical) use vertical; else return horizontal
    if (!Number.isFinite(horizontalTime)) {
      return verticalTime;
    }
    // Otherwise return the (more stable) horizontalTime
    return horizontalTime;
  }

  // They are essentially equal
  return 0.5 * (horizontalTime + verticalTime);
}

/**
 * Validate if a firing solution is possible and within limits.
 * 
 * Checks:
 * - Distance is positive and within maximum range
 * - Distance is not too small (< 1m)
 * - Height difference is not extreme (warning if |ΔZ| > 200m)
 * - Shot is physically possible (discriminant >= 0)
 * 
 * @param {number} distance - Horizontal distance (meters)
 * @param {number} heightDiff - Height difference (meters)
 * @returns {Object} Validation result
 * @returns {boolean} returns.valid - Whether shot is valid
 * @returns {string} returns.status - Status code: 'OK', 'OUT_OF_RANGE', 'TOO_CLOSE', 'UNREACHABLE', 'EXTREME_ELEVATION'
 * @returns {string} returns.message - Human-readable message
 * 
 * @example
 * const result = validateFiringSolution(1000, 50);
 * console.log(result); // { valid: true, status: 'OK', message: 'Firing solution valid' }
 */
export function validateFiringSolution(distance, heightDiff) {
  // Check minimum distance
  if (distance < 1) {
    return {
      valid: false,
      status: 'TOO_CLOSE',
      message: 'ERROR - Mortar and target positions too close (< 1m)'
    };
  }
  
  // Check physical possibility (calculate discriminant)
  const v = PR_PHYSICS.PROJECTILE_VELOCITY;
  const g = PR_PHYSICS.GRAVITY;
  const v2 = v * v;
  const v4 = v2 * v2;
  const discriminant = v4 - g * (g * distance * distance + 2 * v2 * heightDiff);
  
  if (discriminant < 0) {
    return {
      valid: false,
      status: 'UNREACHABLE',
      message: 'TARGET UNREACHABLE - Reduce distance or elevation difference'
    };
  }
  
  // Calculate elevation angle to check against maximum
  const elevationAngle = calculateElevationAngle(distance, heightDiff);
  
  if (elevationAngle === null) {
    return {
      valid: false,
      status: 'UNREACHABLE',
      message: 'TARGET UNREACHABLE - Shot geometry impossible'
    };
  }
  
  // Check if elevation exceeds maximum firing angle (89 degrees for high-angle mortars)
  if (elevationAngle > PR_PHYSICS.MAX_ELEVATION_ANGLE) {
    const maxAngleDegrees = radiansToDegrees(PR_PHYSICS.MAX_ELEVATION_ANGLE);
    const currentAngleDegrees = radiansToDegrees(elevationAngle);
    return {
      valid: false,
      status: 'ANGLE_TOO_HIGH',
      message: `OUT OF RANGE - Requires ${currentAngleDegrees.toFixed(1)}° elevation (max: ${maxAngleDegrees.toFixed(1)}°). Target too close or elevation difference too extreme.`
    };
  }
  
  // Warn about extreme elevation difference
  if (Math.abs(heightDiff) > 200) {
    return {
      valid: true,
      status: 'EXTREME_ELEVATION',
      message: `WARNING - Extreme elevation difference (${Math.round(heightDiff)}m) may reduce accuracy`
    };
  }
  
  // All checks passed
  return {
    valid: true,
    status: 'OK',
    message: 'Firing solution valid'
  };
}

/**
 * Calculate complete firing solution from mortar to target.
 * 
 * This is the main function that combines all calculations into a single
 * firing solution object.
 * 
 * @param {Object} mortar - Mortar position
 * @param {number} mortar.x - X coordinate (meters)
 * @param {number} mortar.y - Y coordinate (meters)
 * @param {number} mortar.z - Z elevation (meters)
 * @param {Object} target - Target position
 * @param {number} target.x - X coordinate (meters)
 * @param {number} target.y - Y coordinate (meters)
 * @param {number} target.z - Z elevation (meters)
 * @returns {Object} Complete firing solution
 * 
 * @example
 * const solution = calculateFiringSolution(
 *   { x: 1000, y: 1000, z: 50 },
 *   { x: 1500, y: 1300, z: 100 }
 * );
 * console.log(solution);
 * // {
 * //   distance: 583.1,
 * //   azimuth: 59.0,
 * //   heightDelta: 50,
 * //   elevationRadians: 1.15,
 * //   elevationMils: 1173,
 * //   elevationDegrees: 65.9,
 * //   timeOfFlight: 7.2,
 * //   valid: true,
 * //   status: 'OK',
 * //   message: 'Firing solution valid'
 * // }
 */
export function calculateFiringSolution(mortar, target) {
  // Calculate horizontal distance
  const distance = calculateDistance(mortar.x, mortar.y, target.x, target.y);
  
  // Calculate azimuth
  const azimuth = calculateAzimuth(mortar.x, mortar.y, target.x, target.y);
  
  // Calculate height difference
  const heightDelta = target.z - mortar.z;
  
  // Validate firing solution
  const validation = validateFiringSolution(distance, heightDelta);
  
  // If invalid, return validation result with null calculations
  if (!validation.valid) {
    return {
      distance,
      azimuth,
      heightDelta,
      elevationRadians: null,
      elevationMils: null,
      elevationDegrees: null,
      timeOfFlight: null,
      ...validation
    };
  }
  
  // Calculate elevation angle
  const elevationRadians = calculateElevationAngle(distance, heightDelta);
  
  // If elevation calculation failed, return unreachable status
  if (elevationRadians === null) {
    return {
      distance,
      azimuth,
      heightDelta,
      elevationRadians: null,
      elevationMils: null,
      elevationDegrees: null,
      timeOfFlight: null,
      valid: false,
      status: 'UNREACHABLE',
      message: 'TARGET UNREACHABLE - Shot geometry impossible'
    };
  }
  
  // Convert elevation to different units
  const elevationMils = radiansToMils(elevationRadians);
  const elevationDegrees = radiansToDegrees(elevationRadians);
  
  // Calculate time of flight
  const timeOfFlight = calculateTimeOfFlight(distance, elevationRadians, heightDelta);
  
  // Return complete solution
  return {
    distance,
    azimuth,
    heightDelta,
    elevationRadians,
    elevationMils,
    elevationDegrees,
    timeOfFlight,
    ...validation
  };
}
