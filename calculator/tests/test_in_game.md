How to use in_game_vectors.json test harness

1. Copy `in_game_vectors.sample.json` to `in_game_vectors.json` in this folder.

2. For each test vector, set values:
   - `mapName`: folder name in `processed_maps`
   - `mortarGridRef`: grid ref of mortar (e.g. `D6-5`)
   - `targetGridRef`: grid ref of target (e.g. `F8-5`)
   - `expectedDistance`: distance measured in-game (meters)
   - `expectedAzimuth`: azimuth measured in-game (degrees)
   - `expectedElevationMils`: elevation measured in-game (mils)
   - `tolerance`: optional object with `distance`, `azimuth`, `elevationMils` thresholds.

3. Run tests:
   ```bash
   node calculator/tests/test_in_game.js
   ```

4. The script will load map files from `processed_maps/<mapName>` and compare the calculator's result to the expected in-game values.

Note: This test harness is a convenience for verifying the calculator's accuracy against in-game measurements and is intentionally not included in the default `npm test` run. It requires manual input of verified in-game measurements.