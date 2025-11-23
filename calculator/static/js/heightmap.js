/**
 * Heightmap Sampling Module for Project Reality Mortar Calculator
 * 
 * Handles loading heightmap data and sampling elevation at any XY position
 * using bilinear interpolation for smooth results.
 * 
 * Heightmap Format:
 * - JSON file containing 16-bit height values (0-65535)
 * - Stored as flat array in row-major order
 * - Resolution: typically 1025×1025 or 2049×2049 pixels
 * - Includes +1 border for terrain stitching
 * 
 * Height Formula:
 * elevation_meters = (pixel_value / 65535) × height_scale
 * 
 * @module heightmap
 */

/**
 * Cache for loaded heightmap data to avoid redundant fetches
 * @type {Map<string, Object>}
 */
const heightmapCache = new Map();

/**
 * Cache for loaded metadata
 * @type {Map<string, Object>}
 */
const metadataCache = new Map();

/**
 * Load heightmap data from JSON file.
 * 
 * Fetches heightmap.json from /maps/[mapName]/ directory (served by Flask).
 * Results are cached to avoid redundant network requests.
 * 
 * Performance optimization: Converts the data array to Uint16Array for:
 * - Reduced memory footprint (50% less than regular array)
 * - Faster access times (typed array optimization)
 * - Direct memory mapping (no intermediate conversions)
 * 
 * @param {string} mapName - Name of the map (e.g., "muttrah_city_2")
 * @returns {Promise<Object>} Heightmap data object
 * @returns {number} returns.resolution - Image resolution (e.g., 1025)
 * @returns {number} returns.width - Image width in pixels
 * @returns {number} returns.height - Image height in pixels
 * @returns {string} returns.format - Data format ("uint16")
 * @returns {Uint16Array} returns.data - Typed array of 16-bit height values
 * 
 * @throws {Error} If fetch fails or JSON is invalid
 * 
 * @example
 * const heightmap = await loadHeightmap('muttrah_city_2');
 * console.log(heightmap.resolution); // 1025
 * console.log(heightmap.data instanceof Uint16Array); // true
 */
export async function loadHeightmap(mapName) {
  // Check cache first
  if (heightmapCache.has(mapName)) {
    return heightmapCache.get(mapName);
  }
  
  try {
    // Load compressed heightmap (only .gz format is distributed)
    const url = `/maps/${mapName}/heightmap.json.gz`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to load heightmap: ${response.status} ${response.statusText}`);
    }
    
    // Decompress gzipped response
    const blob = await response.blob();
    const ds = new DecompressionStream('gzip');
    const decompressedStream = blob.stream().pipeThrough(ds);
    const decompressedBlob = await new Response(decompressedStream).blob();
    const text = await decompressedBlob.text();
    const heightmapData = JSON.parse(text);
    
    // Validate data structure
    if (!heightmapData.resolution || !heightmapData.data || !Array.isArray(heightmapData.data)) {
      throw new Error('Invalid heightmap format: missing required fields');
    }
    
    // Convert data array to Uint16Array for performance
    // This reduces memory usage and speeds up interpolation
    const typedData = new Uint16Array(heightmapData.data);
    
    // Replace the data array with typed array
    const optimizedData = {
      ...heightmapData,
      data: typedData
    };
    
    // Cache the result
    heightmapCache.set(mapName, optimizedData);
    
    return optimizedData;
  } catch (error) {
    console.error(`Error loading heightmap for ${mapName}:`, error);
    throw error;
  }
}

/**
 * Load map metadata from JSON file.
 * 
 * Fetches metadata.json containing map configuration:
 * - map_size: Total map size in meters
 * - height_scale: Maximum terrain height in meters
 * - grid_scale: Size of one grid square in meters
 * 
 * @param {string} mapName - Name of the map
 * @returns {Promise<Object>} Metadata object
 * @returns {number} returns.map_size - Map size in meters
 * @returns {number} returns.height_scale - Maximum height in meters
 * @returns {number} returns.grid_scale - Grid square size in meters
 * @returns {number} returns.resolution - Heightmap resolution
 * 
 * @throws {Error} If fetch fails or JSON is invalid
 * 
 * @example
 * const metadata = await loadMetadata('muttrah_city_2');
 * console.log(metadata.map_size); // 2048
 */
export async function loadMetadata(mapName) {
  // Check cache first
  if (metadataCache.has(mapName)) {
    return metadataCache.get(mapName);
  }
  
  try {
    const url = `/maps/${mapName}/metadata.json`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to load metadata: ${response.status} ${response.statusText}`);
    }
    
    const metadata = await response.json();
    
    // Validate required fields
    if (!metadata.map_size || !metadata.height_scale) {
      throw new Error('Invalid metadata format: missing required fields');
    }
    
    // Cache the result
    metadataCache.set(mapName, metadata);
    
    return metadata;
  } catch (error) {
    console.error(`Error loading metadata for ${mapName}:`, error);
    throw error;
  }
}

/**
 * Convert world coordinates to pixel coordinates in heightmap.
 * 
 * World coordinates are in meters from origin (0,0) at top-left.
 * Pixel coordinates may be fractional (e.g., 123.7) for interpolation.
 * 
 * Note: Heightmap has +1 border, so resolution is typically 1025 or 2049
 * for 1024 or 2048 meter maps. We calculate based on (resolution - 1).
 * 
 * @param {number} x - World X coordinate (meters)
 * @param {number} y - World Y coordinate (meters)
 * @param {number} mapSize - Total map size (meters)
 * @param {number} resolution - Heightmap resolution (pixels)
 * @returns {Object} Pixel coordinates (may be fractional)
 * @returns {number} returns.pixelX - X position in heightmap
 * @returns {number} returns.pixelY - Y position in heightmap
 * 
 * @example
 * const pixel = worldToPixel(1024, 1024, 2048, 1025);
 * console.log(pixel); // { pixelX: 512, pixelY: 512 }
 */
export function worldToPixel(x, y, mapSize, resolution) {
  // Calculate pixels per meter (accounting for +1 border)
  const pixelsPerMeter = (resolution - 1) / mapSize;
  
  // Convert to pixel coordinates
  const pixelX = x * pixelsPerMeter;
  const pixelY = y * pixelsPerMeter;
  
  return { pixelX, pixelY };
}

/**
 * Read height value from heightmap at integer pixel coordinates.
 * 
 * Works with both regular arrays and Uint16Array for compatibility.
 * 
 * @param {number[]|Uint16Array} heightmapData - Flat array of height values
 * @param {number} x - Pixel X coordinate (integer)
 * @param {number} y - Pixel Y coordinate (integer)
 * @param {number} width - Heightmap width in pixels
 * @returns {number} Raw height value (0-65535)
 * 
 * @example
 * const value = getPixelValue(heightmap.data, 512, 512, 1025);
 * console.log(value); // 32768 (middle gray)
 */
function getPixelValue(heightmapData, x, y, width) {
  // Convert 2D coordinates to 1D array index (row-major order)
  const index = y * width + x;
  return heightmapData[index] || 0;
}

/**
 * Perform bilinear interpolation to get smooth height between pixels.
 * 
 * Bilinear interpolation averages the 4 surrounding pixels weighted by
 * fractional position. This produces smooth elevation changes instead of
 * stepped/blocky terrain.
 * 
 * Works with both regular arrays and Uint16Array for performance.
 * 
 * Steps:
 * 1. Find 4 surrounding pixels (top-left, top-right, bottom-left, bottom-right)
 * 2. Get fractional parts of pixel position (how far between pixels)
 * 3. Interpolate horizontally (top row, bottom row)
 * 4. Interpolate vertically (combine top and bottom results)
 * 
 * @param {number[]|Uint16Array} heightmapData - Flat array of height values
 * @param {number} pixelX - Pixel X coordinate (may be fractional)
 * @param {number} pixelY - Pixel Y coordinate (may be fractional)
 * @param {number} width - Heightmap width in pixels
 * @param {number} height - Heightmap height in pixels
 * @returns {number} Interpolated height value (0-65535)
 * 
 * @example
 * // Position 123.7, 456.3 will interpolate between pixels 123-124 and 456-457
 * const value = bilinearInterpolation(heightmap.data, 123.7, 456.3, 1025, 1025);
 */
export function bilinearInterpolation(heightmapData, pixelX, pixelY, width, height) {
  // Get integer parts (floor)
  const x0 = Math.floor(pixelX);
  const y0 = Math.floor(pixelY);
  
  // Get next pixel coordinates (ceiling)
  const x1 = Math.min(x0 + 1, width - 1);
  const y1 = Math.min(y0 + 1, height - 1);
  
  // Get fractional parts (how far between pixels, 0-1 range)
  const fx = pixelX - x0;
  const fy = pixelY - y0;
  
  // Read 4 surrounding pixel values
  const topLeft = getPixelValue(heightmapData, x0, y0, width);
  const topRight = getPixelValue(heightmapData, x1, y0, width);
  const bottomLeft = getPixelValue(heightmapData, x0, y1, width);
  const bottomRight = getPixelValue(heightmapData, x1, y1, width);
  
  // Interpolate horizontally along top edge
  const topValue = topLeft + fx * (topRight - topLeft);
  
  // Interpolate horizontally along bottom edge
  const bottomValue = bottomLeft + fx * (bottomRight - bottomLeft);
  
  // Interpolate vertically between top and bottom
  const finalValue = topValue + fy * (bottomValue - topValue);
  
  return finalValue;
}

/**
 * Get elevation at world XY coordinates (full pipeline).
 * 
 * This is the main function for height sampling:
 * 1. Convert world coordinates to pixel coordinates
 * 2. Perform bilinear interpolation
 * 3. Apply height scale formula: elevation = (value / 65535) × height_scale
 * 
 * @param {number} x - World X coordinate (meters)
 * @param {number} y - World Y coordinate (meters)
 * @param {number[]|Uint16Array} heightmapData - Flat array of height values
 * @param {number} heightScale - Maximum terrain height (meters)
 * @param {number} mapSize - Total map size (meters)
 * @param {number} resolution - Heightmap resolution (pixels)
 * @returns {number} Elevation in meters
 * 
 * @example
 * const elevation = getElevation(1024, 1024, heightmap.data, 300, 2048, 1025);
 * console.log(elevation); // 150.5 meters
 */
export function getElevation(x, y, heightmapData, heightScale, mapSize, resolution) {
  // Validate inputs
  if (x < 0 || x > mapSize || y < 0 || y > mapSize) {
    console.warn(`Coordinates (${x}, ${y}) outside map bounds (0-${mapSize})`);
    // Clamp to bounds
    x = Math.max(0, Math.min(mapSize, x));
    y = Math.max(0, Math.min(mapSize, y));
  }
  
  // Convert world to pixel coordinates
  const { pixelX, pixelY } = worldToPixel(x, y, mapSize, resolution);
  
  // Get interpolated height value (0-65535)
  const rawValue = bilinearInterpolation(heightmapData, pixelX, pixelY, resolution, resolution);
  
  // Apply height scale formula: elevation = (value / 65535) × height_scale
  const elevation = (rawValue / 65535.0) * heightScale;
  
  return elevation;
}

/**
 * Load map data (heightmap + metadata) and prepare for use.
 * 
 * Convenience function that loads both heightmap and metadata,
 * returning everything needed for elevation sampling.
 * 
 * @param {string} mapName - Name of the map
 * @returns {Promise<Object>} Complete map data
 * @returns {Object} returns.heightmap - Heightmap data
 * @returns {Object} returns.metadata - Map metadata
 * @returns {Function} returns.getElevationAt - Convenience function to get elevation at (x,y)
 * 
 * @example
 * const mapData = await loadMapData('muttrah_city_2');
 * const elevation = mapData.getElevationAt(1024, 1024);
 * console.log(elevation); // 150.5 meters
 */
export async function loadMapData(mapName) {
  // Load both heightmap and metadata in parallel
  const [heightmap, metadata] = await Promise.all([
    loadHeightmap(mapName),
    loadMetadata(mapName)
  ]);
  
  // Create convenience function for getting elevation
  const getElevationAt = (x, y) => {
    return getElevation(
      x,
      y,
      heightmap.data,
      metadata.height_scale,
      metadata.map_size,
      heightmap.resolution
    );
  };
  
  return {
    heightmap,
    metadata,
    getElevationAt
  };
}

/**
 * Clear heightmap cache (useful for testing or memory management).
 * 
 * @param {string} [mapName] - Optional: clear specific map. If omitted, clears all.
 * 
 * @example
 * clearCache('muttrah_city_2'); // Clear one map
 * clearCache(); // Clear all cached maps
 */
export function clearCache(mapName) {
  if (mapName) {
    heightmapCache.delete(mapName);
    metadataCache.delete(mapName);
  } else {
    heightmapCache.clear();
    metadataCache.clear();
  }
}

/**
 * Check if coordinates are valid (within bounds with small tolerance).
 * 
 * @param {number} x - X coordinate (meters)
 * @param {number} y - Y coordinate (meters)
 * @param {number} mapSize - Map size (meters)
 * @returns {boolean} True if valid, false otherwise
 * 
 * @example
 * const valid = isValidCoordinate(1024, 1024, 2048);
 * console.log(valid); // true
 */
export function isValidCoordinate(x, y, mapSize) {
  // Allow small tolerance for floating-point errors
  const tolerance = 0.1;
  return x >= -tolerance && x <= mapSize + tolerance &&
         y >= -tolerance && y <= mapSize + tolerance;
}

/**
 * Get heightmap data statistics (for debugging).
 * 
 * Works with both regular arrays and Uint16Array.
 * 
 * @param {number[]|Uint16Array} heightmapData - Flat array of height values
 * @returns {Object} Statistics
 * @returns {number} returns.min - Minimum value
 * @returns {number} returns.max - Maximum value
 * @returns {number} returns.mean - Average value
 * 
 * @example
 * const stats = getHeightmapStats(heightmap.data);
 * console.log(stats); // { min: 0, max: 65535, mean: 32768 }
 */
export function getHeightmapStats(heightmapData) {
  if (!heightmapData || heightmapData.length === 0) {
    return { min: 0, max: 0, mean: 0 };
  }
  
  let min = Infinity;
  let max = -Infinity;
  let sum = 0;
  
  for (const value of heightmapData) {
    if (value < min) min = value;
    if (value > max) max = value;
    sum += value;
  }
  
  const mean = sum / heightmapData.length;
  
  return { min, max, mean };
}
