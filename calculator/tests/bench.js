/**
 * Performance Benchmark for Ballistics Calculation Engine
 * 
 * Measures execution times for:
 * - Grid coordinate parsing and conversion
 * - Heightmap elevation sampling
 * - Firing solution calculation
 * - Full end-to-end pipeline
 * 
 * Usage:
 *   node calculator/tests/bench.js [iterations]
 * 
 * Example:
 *   node calculator/tests/bench.js 1000
 */

import { performance } from 'node:perf_hooks';
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseGridReference, gridRefToXY, calculateGridScale } from '../static/js/coordinates.js';
import { bilinearInterpolation, worldToPixel } from '../static/js/heightmap.js';
import { calculateFiringSolution } from '../static/js/ballistics.js';

// Get the directory path for resolving relative paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Load heightmap data from file system
 */
async function loadHeightmapFromFile(mapName) {
  const heightmapPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'heightmap.json');
  const data = await readFile(heightmapPath, 'utf-8');
  const heightmapData = JSON.parse(data);
  heightmapData.data = new Uint16Array(heightmapData.data);
  return heightmapData;
}

/**
 * Load metadata from file system
 */
async function loadMetadataFromFile(mapName) {
  const metadataPath = join(__dirname, '..', '..', 'processed_maps', mapName, 'metadata.json');
  const data = await readFile(metadataPath, 'utf-8');
  return JSON.parse(data);
}

/**
 * Get elevation at XY coordinates
 */
function getElevation(x, y, heightmapData, heightScale, mapSize, resolution) {
  x = Math.max(0, Math.min(mapSize, x));
  y = Math.max(0, Math.min(mapSize, y));
  
  const { pixelX, pixelY } = worldToPixel(x, y, mapSize, resolution);
  const rawValue = bilinearInterpolation(heightmapData, pixelX, pixelY, resolution, resolution);
  const elevation = (rawValue / 65535.0) * heightScale;
  
  return elevation;
}

/**
 * Format number with thousands separator
 */
function formatNumber(num) {
  return num.toLocaleString('en-US');
}

/**
 * Calculate statistics from array of measurements
 */
function calculateStats(measurements) {
  const sorted = [...measurements].sort((a, b) => a - b);
  const sum = measurements.reduce((a, b) => a + b, 0);
  const mean = sum / measurements.length;
  
  // Calculate standard deviation
  const squaredDiffs = measurements.map(x => Math.pow(x - mean, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / measurements.length;
  const stdDev = Math.sqrt(variance);
  
  return {
    min: sorted[0],
    max: sorted[sorted.length - 1],
    mean: mean,
    median: sorted[Math.floor(sorted.length / 2)],
    p95: sorted[Math.floor(sorted.length * 0.95)],
    p99: sorted[Math.floor(sorted.length * 0.99)],
    stdDev: stdDev
  };
}

/**
 * Print benchmark results
 */
function printResults(label, stats, iterations) {
  console.log(`\n${label}:`);
  console.log(`  Iterations: ${formatNumber(iterations)}`);
  console.log(`  Min:        ${stats.min.toFixed(3)}ms`);
  console.log(`  Mean:       ${stats.mean.toFixed(3)}ms`);
  console.log(`  Median:     ${stats.median.toFixed(3)}ms`);
  console.log(`  P95:        ${stats.p95.toFixed(3)}ms`);
  console.log(`  P99:        ${stats.p99.toFixed(3)}ms`);
  console.log(`  Max:        ${stats.max.toFixed(3)}ms`);
  console.log(`  Std Dev:    ${stats.stdDev.toFixed(3)}ms`);
  
  // Performance assessment
  if (stats.mean < 1) {
    console.log(`  Assessment: ✓ EXCELLENT (< 1ms)`);
  } else if (stats.mean < 10) {
    console.log(`  Assessment: ✓ GOOD (< 10ms)`);
  } else if (stats.mean < 50) {
    console.log(`  Assessment: ✓ ACCEPTABLE (< 50ms)`);
  } else {
    console.log(`  Assessment: ⚠ SLOW (> 50ms) - optimization recommended`);
  }
}

/**
 * Benchmark grid reference parsing
 */
function benchmarkGridParsing(iterations) {
  const gridRefs = ['A1-5', 'D6-7', 'M13-9', 'G7-3', 'Delta 6-7'];
  const measurements = [];
  
  for (let i = 0; i < iterations; i++) {
    const gridRef = gridRefs[i % gridRefs.length];
    
    const start = performance.now();
    const result = parseGridReference(gridRef);
    const end = performance.now();
    
    measurements.push(end - start);
    
    // Prevent optimization elimination
    if (!result) throw new Error('Parse failed');
  }
  
  return calculateStats(measurements);
}

/**
 * Benchmark grid to XY conversion
 */
function benchmarkGridToXY(iterations, gridScale) {
  const testCases = [
    { column: 'A', row: 1, keypad: 5 },
    { column: 'D', row: 6, keypad: 7 },
    { column: 'M', row: 13, keypad: 9 },
    { column: 'G', row: 7, keypad: 3 }
  ];
  const measurements = [];
  
  for (let i = 0; i < iterations; i++) {
    const test = testCases[i % testCases.length];
    
    const start = performance.now();
    const gridRef = `${test.column}${test.row}-${test.keypad}`;
    const result = gridRefToXY(gridRef, gridScale);
    const end = performance.now();
    
    measurements.push(end - start);
    
    if (!result) throw new Error('Conversion failed');
  }
  
  return calculateStats(measurements);
}

/**
 * Benchmark elevation sampling
 */
function benchmarkElevationSampling(iterations, heightmap, metadata) {
  const mapSize = metadata.map_size;
  const measurements = [];
  
  // Pre-generate random coordinates
  const coords = [];
  for (let i = 0; i < iterations; i++) {
    coords.push({
      x: Math.random() * mapSize,
      y: Math.random() * mapSize
    });
  }
  
  for (let i = 0; i < iterations; i++) {
    const { x, y } = coords[i];
    
    const start = performance.now();
    const elevation = getElevation(
      x, y,
      heightmap.data,
      metadata.height_scale,
      metadata.map_size,
      heightmap.resolution
    );
    const end = performance.now();
    
    measurements.push(end - start);
    
    if (isNaN(elevation)) throw new Error('Elevation failed');
  }
  
  return calculateStats(measurements);
}

/**
 * Benchmark firing solution calculation
 */
function benchmarkFiringSolution(iterations) {
  const measurements = [];
  
  // Pre-generate random test cases
  const testCases = [];
  for (let i = 0; i < iterations; i++) {
    testCases.push({
      mortar: {
        x: Math.random() * 4000,
        y: Math.random() * 4000,
        z: Math.random() * 200
      },
      target: {
        x: Math.random() * 4000,
        y: Math.random() * 4000,
        z: Math.random() * 200
      }
    });
  }
  
  for (let i = 0; i < iterations; i++) {
    const { mortar, target } = testCases[i];
    
    const start = performance.now();
    const solution = calculateFiringSolution(mortar, target);
    const end = performance.now();
    
    measurements.push(end - start);
    
    if (!solution) throw new Error('Solution failed');
  }
  
  return calculateStats(measurements);
}

/**
 * Benchmark full end-to-end pipeline
 */
function benchmarkFullPipeline(iterations, heightmap, metadata, gridScale) {
  const measurements = [];
  
  // Pre-generate test cases
  const testCases = [];
  for (let i = 0; i < iterations; i++) {
    const col = String.fromCharCode(65 + Math.floor(Math.random() * 13)); // A-M
    const row = 1 + Math.floor(Math.random() * 13); // 1-13
    const keypad = 1 + Math.floor(Math.random() * 9); // 1-9
    
    testCases.push({
      mortarRef: `${col}${row}-${keypad}`,
      targetRef: `${String.fromCharCode(65 + Math.floor(Math.random() * 13))}${1 + Math.floor(Math.random() * 13)}-${1 + Math.floor(Math.random() * 9)}`
    });
  }
  
  for (let i = 0; i < iterations; i++) {
    const { mortarRef, targetRef } = testCases[i];
    
    const start = performance.now();
    
    // 1. Parse grid references
    const mortarXY = gridRefToXY(mortarRef, gridScale);
    const targetXY = gridRefToXY(targetRef, gridScale);
    
    if (!mortarXY || !targetXY) continue;
    
    // 2. Get elevations
    const mortarZ = getElevation(
      mortarXY.x, mortarXY.y,
      heightmap.data,
      metadata.height_scale,
      metadata.map_size,
      heightmap.resolution
    );
    
    const targetZ = getElevation(
      targetXY.x, targetXY.y,
      heightmap.data,
      metadata.height_scale,
      metadata.map_size,
      heightmap.resolution
    );
    
    // 3. Calculate firing solution
    const solution = calculateFiringSolution(
      { x: mortarXY.x, y: mortarXY.y, z: mortarZ },
      { x: targetXY.x, y: targetXY.y, z: targetZ }
    );
    
    const end = performance.now();
    
    measurements.push(end - start);
    
    if (!solution) throw new Error('Pipeline failed');
  }
  
  return calculateStats(measurements);
}

/**
 * Main benchmark runner
 */
async function runBenchmarks() {
  // Get iterations from command line (default 1000)
  const iterations = parseInt(process.argv[2]) || 1000;
  
  console.log('='.repeat(70));
  console.log('PERFORMANCE BENCHMARK - Ballistics Calculation Engine');
  console.log('='.repeat(70));
  console.log(`\nTarget: <50ms per full pipeline calculation`);
  console.log(`Date: ${new Date().toISOString()}`);
  
  try {
    // Load test data
    console.log('\nLoading test_bootcamp map data...');
    const [heightmap, metadata] = await Promise.all([
      loadHeightmapFromFile('test_bootcamp'),
      loadMetadataFromFile('test_bootcamp')
    ]);
    const gridScale = calculateGridScale(metadata.map_size);
    
    console.log(`Map size: ${metadata.map_size}m`);
    console.log(`Resolution: ${heightmap.resolution}×${heightmap.resolution}`);
    console.log(`Grid scale: ${gridScale.toFixed(2)}m`);
    
    // Warm-up runs to stabilize JIT compilation
    console.log('\nWarming up...');
    benchmarkGridParsing(100);
    benchmarkGridToXY(100, gridScale);
    benchmarkElevationSampling(100, heightmap, metadata);
    benchmarkFiringSolution(100);
    benchmarkFullPipeline(100, heightmap, metadata, gridScale);
    
    console.log('\n' + '='.repeat(70));
    console.log('BENCHMARK RESULTS');
    console.log('='.repeat(70));
    
    // Run benchmarks
    console.log('\n--- Component Benchmarks ---');
    
    printResults(
      '1. Grid Reference Parsing',
      benchmarkGridParsing(iterations),
      iterations
    );
    
    printResults(
      '2. Grid to XY Conversion',
      benchmarkGridToXY(iterations, gridScale),
      iterations
    );
    
    printResults(
      '3. Elevation Sampling (with bilinear interpolation)',
      benchmarkElevationSampling(iterations, heightmap, metadata),
      iterations
    );
    
    printResults(
      '4. Firing Solution Calculation',
      benchmarkFiringSolution(iterations),
      iterations
    );
    
    console.log('\n--- End-to-End Benchmark ---');
    
    printResults(
      '5. Full Pipeline (Grid → XY → Elevation → Solution)',
      benchmarkFullPipeline(iterations, heightmap, metadata, gridScale),
      iterations
    );
    
    console.log('\n' + '='.repeat(70));
    console.log('SUMMARY');
    console.log('='.repeat(70));
    
    const pipelineStats = benchmarkFullPipeline(iterations, heightmap, metadata, gridScale);
    
    console.log(`\nFull pipeline average: ${pipelineStats.mean.toFixed(3)}ms`);
    
    if (pipelineStats.mean < 50) {
      console.log(`\n✓ PERFORMANCE TARGET MET: Average < 50ms`);
      console.log(`  Margin: ${(50 - pipelineStats.mean).toFixed(3)}ms below target`);
    } else {
      console.log(`\n⚠ PERFORMANCE TARGET MISSED: Average > 50ms`);
      console.log(`  Overage: ${(pipelineStats.mean - 50).toFixed(3)}ms above target`);
      console.log(`\nOptimization recommendations:`);
      console.log(`  - Consider WebAssembly for heightmap interpolation`);
      console.log(`  - Implement spatial indexing for large maps`);
      console.log(`  - Cache frequently accessed elevations`);
    }
    
    console.log('\n' + '='.repeat(70));
    
  } catch (error) {
    console.error('\nBenchmark error:', error);
    process.exit(1);
  }
}

// Run benchmarks
runBenchmarks();
