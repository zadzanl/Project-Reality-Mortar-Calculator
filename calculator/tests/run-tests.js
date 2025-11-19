import { runBallisticsTests } from './test_ballistics.js';
import { runCoordinatesTests } from './test_coordinates.js';
import { runHeightmapTests } from './test_heightmap.js';
import { runIntegrationTests } from './test_integration.js';

async function runAll() {
  try {
    console.log('Running Ballistics tests...');
    await runBallisticsTests();
    console.log('Ballistics tests passed.\n');

    console.log('Running Coordinates tests...');
    await runCoordinatesTests();
    console.log('Coordinates tests passed.\n');

    console.log('Running Heightmap tests...');
    await runHeightmapTests();
    console.log('Heightmap tests passed.\n');

    console.log('Running Integration tests...');
    await runIntegrationTests();
    console.log('Integration tests passed.\n');

    console.log('All tests passed! 🎉');
    process.exit(0);
  } catch (err) {
    console.error('Test failure:', err);
    process.exit(1);
  }
}

runAll();
