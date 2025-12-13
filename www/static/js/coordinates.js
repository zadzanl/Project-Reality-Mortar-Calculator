/**
 * Coordinate Conversion Module for Project Reality Mortar Calculator
 * 
 * Handles conversion between PR grid notation and world XY coordinates.
 * 
 * Grid System:
 * - Columns: A-M (13 columns, A=leftmost/West, M=rightmost/East)
 * - Rows: 1-13 (13 rows, 1=topmost/North, 13=bottommost/South)
 * - Keypad: 1-9 (subgrid within each square, phone keypad layout)
 * 
 * Keypad Layout:
 * 7 8 9  (top row)
 * 4 5 6  (middle row)
 * 1 2 3  (bottom row)
 * 
 * Coordinate System:
 * - Origin (0,0) at top-left corner (Northwest)
 * - X-axis increases rightward (West to East)
 * - Y-axis increases downward (North to South)
 * 
 * @module coordinates
 */

/**
 * Column letters A through M
 * @const {string[]}
 */
export const GRID_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M'];

/**
 * Row numbers 1 through 13
 * @const {number[]}
 */
export const GRID_ROWS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

/**
 * Keypad numbers in phone layout order
 * @const {number[]}
 */
export const KEYPAD_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/**
 * Keypad position offsets as fractions (0, 0.5, 1) for each keypad number.
 * These represent the position within a grid square as a fraction of the square size.
 * 
 * Layout:
 * 7(0,0)   8(0.5,0)   9(1,0)
 * 4(0,0.5) 5(0.5,0.5) 6(1,0.5)
 * 1(0,1)   2(0.5,1)   3(1,1)
 * 
 * @const {Object.<number, {x: number, y: number}>}
 */
const KEYPAD_OFFSETS = {
  7: { x: 0.0, y: 0.0 },   // Top-left
  8: { x: 0.5, y: 0.0 },   // Top-center
  9: { x: 1.0, y: 0.0 },   // Top-right
  4: { x: 0.0, y: 0.5 },   // Middle-left
  5: { x: 0.5, y: 0.5 },   // Center
  6: { x: 1.0, y: 0.5 },   // Middle-right
  1: { x: 0.0, y: 1.0 },   // Bottom-left
  2: { x: 0.5, y: 1.0 },   // Bottom-center
  3: { x: 1.0, y: 1.0 }    // Bottom-right
};

/**
 * NATO column words mapping to letters (A-M)
 * Accepts full words like 'Alpha', 'Bravo', 'Charlie', 'Delta', etc.
 * @const {Object.<string, string>}
 */
const NATO_COLUMN_WORDS = {
  alpha: 'A', bravo: 'B', charlie: 'C', delta: 'D', echo: 'E',
  foxtrot: 'F', golf: 'G', hotel: 'H', india: 'I', juliet: 'J',
  kilo: 'K', lima: 'L', mike: 'M'
};

/**
 * Parse a grid reference string into components.
 * 
 * Accepts formats:
 * - "D6-7" (standard short form)
 * - "D6-kpad7" (with keypad prefix)
 * - "Delta 6-7" (long form, case-insensitive)
 * - "d6-7" (lowercase)
 * 
 * @param {string} gridRef - Grid reference string
 * @returns {Object|null} Parsed components, or null if invalid
 * @returns {string} returns.column - Column letter (A-M)
 * @returns {number} returns.row - Row number (1-13)
 * @returns {number} returns.keypad - Keypad position (1-9)
 * 
 * @example
 * const parsed = parseGridReference("D6-7");
 * console.log(parsed); // { column: 'D', row: 6, keypad: 7 }
 */
export function parseGridReference(gridRef) {
  if (!gridRef || typeof gridRef !== 'string') {
    return null;
  }
  
  // Regex pattern: Single letter (A-M) OR full NATO word (Alpha..Mike), Number(s), optional separator/keypad prefix, Digit
  // Matches: D6-7, D6-kpad7, Delta 6-7, d6-7, alpha 6-7, etc.
  // Place word alternatives before single-letter match so 'Delta 6-7' doesn't match 'D' only
  const pattern = /^((?:alpha|bravo|charlie|delta|echo|foxtrot|golf|hotel|india|juliet|kilo|lima|mike|[A-Ma-m]))\s*(\d{1,2})[-\s]*(?:kpad\s*)?(\d)$/i;
  const match = gridRef.trim().match(pattern);
  
  if (!match) {
    return null;
  }
  
  // Column may be a single letter or a NATO word; normalize to letter A-M
  let columnKey = match[1];
  let column = columnKey.toUpperCase();
  if (columnKey.length > 1) {
    const mapped = NATO_COLUMN_WORDS[columnKey.toLowerCase()];
    if (!mapped) {
      return null;
    }
    column = mapped;
  }
  const row = parseInt(match[2], 10);
  const keypad = parseInt(match[3], 10);
  
  // Validate components
  if (!GRID_COLUMNS.includes(column)) {
    return null;
  }
  
  if (row < 1 || row > 13) {
    return null;
  }
  
  if (keypad < 1 || keypad > 9) {
    return null;
  }
  
  return { column, row, keypad };
}

/**
 * Get the keypad offset within a grid square.
 * 
 * @param {number} keypadNum - Keypad number (1-9)
 * @param {number} gridScale - Size of one grid square (meters)
 * @returns {Object} Offset in meters
 * @returns {number} returns.x - X offset (meters)
 * @returns {number} returns.y - Y offset (meters)
 * 
 * @example
 * const offset = getKeypadOffset(5, 150);
 * console.log(offset); // { x: 75, y: 75 } (center of 150m square)
 */
export function getKeypadOffset(keypadNum, gridScale) {
  if (!KEYPAD_OFFSETS[keypadNum]) {
    throw new Error(`Invalid keypad number: ${keypadNum}. Must be 1-9.`);
  }
  
  const offset = KEYPAD_OFFSETS[keypadNum];
  return {
    x: offset.x * gridScale,
    y: offset.y * gridScale
  };
}

/**
 * Convert grid reference to world XY coordinates.
 * 
 * @param {string} column - Column letter (A-M)
 * @param {number} row - Row number (1-13)
 * @param {number} keypad - Keypad position (1-9)
 * @param {number} gridScale - Size of one grid square in meters
 * @returns {Object} World coordinates
 * @returns {number} returns.x - X coordinate (meters)
 * @returns {number} returns.y - Y coordinate (meters)
 * 
 * @example
 * const pos = gridToXY('D', 6, 7, 150);
 * console.log(pos); // { x: 450, y: 750 } (for 150m grid scale)
 */
export function gridToXY(column, row, keypad, gridScale) {
  // Validate inputs
  if (!GRID_COLUMNS.includes(column)) {
    throw new Error(`Invalid column: ${column}. Must be A-M.`);
  }
  
  if (row < 1 || row > 13) {
    throw new Error(`Invalid row: ${row}. Must be 1-13.`);
  }
  
  if (keypad < 1 || keypad > 9) {
    throw new Error(`Invalid keypad: ${keypad}. Must be 1-9.`);
  }
  
  if (gridScale <= 0) {
    throw new Error(`Invalid grid scale: ${gridScale}. Must be positive.`);
  }
  
  // Convert column letter to index (A=0, B=1, ..., M=12)
  const columnIndex = GRID_COLUMNS.indexOf(column);
  
  // Convert row to index (1→0, 2→1, ..., 13→12)
  const rowIndex = row - 1;
  
  // Calculate base position (top-left corner of grid square)
  const baseX = columnIndex * gridScale;
  const baseY = rowIndex * gridScale;
  
  // Get keypad offset within the square
  const offset = getKeypadOffset(keypad, gridScale);
  
  // Final position
  return {
    x: baseX + offset.x,
    y: baseY + offset.y
  };
}

/**
 * Convert world XY coordinates to grid reference.
 * 
 * Returns the grid square and approximate keypad position for given coordinates.
 * The keypad is determined by which third of the square the position falls into.
 * 
 * @param {number} x - X coordinate (meters)
 * @param {number} y - Y coordinate (meters)
 * @param {number} gridScale - Size of one grid square (meters)
 * @returns {Object} Grid reference components
 * @returns {string} returns.column - Column letter (A-M)
 * @returns {number} returns.row - Row number (1-13)
 * @returns {number} returns.keypad - Keypad position (1-9)
 * @returns {string} returns.gridRef - Formatted grid reference (e.g., "D6-7")
 * 
 * @example
 * const grid = xyToGrid(475, 775, 150);
 * console.log(grid); // { column: 'D', row: 6, keypad: 5, gridRef: 'D6-5' }
 */
export function xyToGrid(x, y, gridScale) {
  // Calculate which grid square we're in
  const columnIndex = Math.floor(x / gridScale);
  const rowIndex = Math.floor(y / gridScale);
  
  // Validate bounds
  if (columnIndex < 0 || columnIndex >= 13) {
    throw new Error(`X coordinate ${x} is out of map bounds (0-${13 * gridScale}m)`);
  }
  
  if (rowIndex < 0 || rowIndex >= 13) {
    throw new Error(`Y coordinate ${y} is out of map bounds (0-${13 * gridScale}m)`);
  }
  
  // Get column letter and row number
  const column = GRID_COLUMNS[columnIndex];
  const row = rowIndex + 1;
  
  // Calculate position within the square (0-1 range)
  const inSquareX = (x % gridScale) / gridScale;
  const inSquareY = (y % gridScale) / gridScale;
  
  // Determine keypad position (divide square into 3x3 grid)
  // X: 0-0.33 = left (0), 0.33-0.67 = center (0.5), 0.67-1 = right (1)
  // Y: 0-0.33 = top (0), 0.33-0.67 = middle (0.5), 0.67-1 = bottom (1)
  let keypadX, keypadY;
  
  if (inSquareX < 0.33) {
    keypadX = 0; // Left
  } else if (inSquareX < 0.67) {
    keypadX = 1; // Center
  } else {
    keypadX = 2; // Right
  }
  
  if (inSquareY < 0.33) {
    keypadY = 0; // Top
  } else if (inSquareY < 0.67) {
    keypadY = 1; // Middle
  } else {
    keypadY = 2; // Bottom
  }
  
  // Convert to keypad number (7-8-9 / 4-5-6 / 1-2-3)
  const keypadMap = [
    [7, 8, 9],  // Top row
    [4, 5, 6],  // Middle row
    [1, 2, 3]   // Bottom row
  ];
  const keypad = keypadMap[keypadY][keypadX];
  
  // Format grid reference
  const gridRef = `${column}${row}-${keypad}`;
  
  return { column, row, keypad, gridRef };
}

/**
 * Validate a grid reference string.
 * 
 * Checks if the format is correct and values are within bounds.
 * 
 * @param {string} gridRef - Grid reference to validate
 * @returns {Object} Validation result
 * @returns {boolean} returns.valid - Whether the grid reference is valid
 * @returns {string} returns.error - Error message if invalid, empty if valid
 * 
 * @example
 * const result = validateGridReference("D6-7");
 * console.log(result); // { valid: true, error: '' }
 * 
 * const invalid = validateGridReference("Z99-0");
 * console.log(invalid); // { valid: false, error: 'Invalid format' }
 */
export function validateGridReference(gridRef) {
  if (!gridRef || typeof gridRef !== 'string') {
    return {
      valid: false,
      error: 'Grid reference must be a non-empty string'
    };
  }
  
  const parsed = parseGridReference(gridRef);
  
  if (!parsed) {
    return {
      valid: false,
      error: 'Invalid format. Expected: "D6-7" or "D6-kpad7"'
    };
  }
  
  // All validation passed (parseGridReference already checks bounds)
  return {
    valid: true,
    error: ''
  };
}

/**
 * Calculate grid scale from map size.
 * 
 * PR uses a 13×13 grid system. Grid scale is the size of one square.
 * - 1km maps (1024m): 75m per square (rounded from 1024/13 ≈ 78.8)
 * - 2km maps (2048m): 150m per square (rounded from 2048/13 ≈ 157.5)
 * - 4km maps (4096m): 300m per square (rounded from 4096/13 ≈ 315.1)
 * 
 * @param {number} mapSize - Map size in meters
 * @returns {number} Grid scale in meters
 * 
 * @example
 * const scale = calculateGridScale(2048);
 * console.log(scale); // 150
 */
export function calculateGridScale(mapSize) {
  // Grid scale is map size divided by 13 (PR uses 13×13 grid). Return full precision.
  return mapSize / 13;
}

/**
 * Calculate the X coordinate for the row label anchor on the right side of the map.
 * This places the label approximately gridScale*0.15 meters from the right edge.
 *
 * @param {number} mapSize - Map size in meters
 * @param {number} gridScale - Size of one grid square in meters
 * @returns {number} X coordinate for row label anchor
 */
export function getRowLabelCenterX(mapSize, gridScale) {
  if (typeof mapSize !== 'number' || typeof gridScale !== 'number') {
    throw new Error('mapSize and gridScale must be numbers');
  }
  return mapSize - (gridScale * 0.15);
}

/**
 * Format grid reference from components.
 * 
 * @param {string} column - Column letter (A-M)
 * @param {number} row - Row number (1-13)
 * @param {number} keypad - Keypad position (1-9)
 * @returns {string} Formatted grid reference (e.g., "D6-7")
 * 
 * @example
 * const ref = formatGridReference('D', 6, 7);
 * console.log(ref); // "D6-7"
 */
export function formatGridReference(column, row, keypad) {
  return `${column}${row}-${keypad}`;
}

/**
 * Check if coordinates are within map bounds.
 * 
 * @param {number} x - X coordinate (meters)
 * @param {number} y - Y coordinate (meters)
 * @param {number} mapSize - Map size in meters
 * @returns {boolean} True if within bounds, false otherwise
 * 
 * @example
 * const inBounds = isWithinMapBounds(1000, 1500, 2048);
 * console.log(inBounds); // true
 */
export function isWithinMapBounds(x, y, mapSize) {
  return x >= 0 && x <= mapSize && y >= 0 && y <= mapSize;
}

/**
 * Convert parsed grid reference to XY coordinates (convenience function).
 * 
 * @param {string} gridRef - Grid reference string (e.g., "D6-7")
 * @param {number} gridScale - Size of one grid square (meters)
 * @returns {Object|null} World coordinates, or null if invalid
 * @returns {number} returns.x - X coordinate (meters)
 * @returns {number} returns.y - Y coordinate (meters)
 * 
 * @example
 * const pos = gridRefToXY("D6-7", 150);
 * console.log(pos); // { x: 450, y: 750 }
 */
export function gridRefToXY(gridRef, gridScale) {
  const parsed = parseGridReference(gridRef);
  
  if (!parsed) {
    return null;
  }
  
  return gridToXY(parsed.column, parsed.row, parsed.keypad, gridScale);
}
