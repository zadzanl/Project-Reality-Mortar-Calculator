# ballistics-engine Specification

## Purpose
TBD - created by archiving change add-ballistics-calculation-engine. Update Purpose after archive.
## Requirements
### Requirement: Project Reality Physics Constants

The system SHALL use Project Reality: BF2 engine-specific physics constants (NOT real-world Earth physics) for all ballistic calculations.

#### Scenario: Gravity constant validation
- **WHEN** ballistics module is loaded
- **THEN** PR_PHYSICS.GRAVITY is set to 14.86 m/s²
- **AND** constant is marked immutable (Object.freeze or const)
- **AND** code comment warns against modification

#### Scenario: Projectile velocity validation
- **WHEN** firing solution is calculated
- **THEN** projectile initial velocity is 148.64 m/s
- **AND** value is sourced from PR_PHYSICS.PROJECTILE_VELOCITY constant

#### Scenario: Maximum range enforcement
- **WHEN** target distance exceeds 1500 meters
- **THEN** validation function returns error "OUT OF RANGE - Maximum range 1500m"
- **AND** no firing solution is calculated

### Requirement: High-Angle Firing Solution Calculation

The system SHALL calculate mortar elevation angle using high-angle ballistic formula accounting for horizontal distance and height difference.

#### Scenario: Standard firing solution
- **WHEN** mortar at (1000, 1000, 50m elevation) targets position at (1500, 1300, 120m elevation)
- **THEN** horizontal distance D is calculated: sqrt((1500-1000)² + (1300-1000)²) = 583.1m
- **AND** height difference ΔZ is calculated: 120 - 50 = 70m (positive, target higher)
- **AND** discriminant is calculated: v⁴ - g*(g*D² + 2*v²*ΔZ)
- **AND** elevation angle φ is calculated: arctan((v² + sqrt(discriminant)) / (g*D))
- **AND** result is returned in radians

#### Scenario: Impossible shot (discriminant negative)
- **WHEN** distance is 2000m and height difference is -500m (target much lower)
- **THEN** discriminant calculation yields negative value
- **AND** function returns error "TARGET UNREACHABLE - Reduce distance or elevation difference"
- **AND** no firing solution is provided

#### Scenario: Zero distance edge case
- **WHEN** mortar and target are at same XY position (distance < 1m)
- **THEN** function returns error "ERROR - Mortar and target positions too close"
- **AND** division by zero is avoided

### Requirement: Angular Unit Conversions

The system SHALL convert elevation angles between radians (internal calculations), Mils (primary display), and Degrees (secondary display).

#### Scenario: Radians to Mils conversion
- **WHEN** elevation angle is 1.22 radians
- **THEN** conversion calculates: 1.22 × (6400 / (2π)) = 1.22 × 1018.59 = 1242.7 mils
- **AND** result is rounded to nearest whole mil: 1243 mils

#### Scenario: Radians to Degrees conversion
- **WHEN** elevation angle is 1.22 radians
- **THEN** conversion calculates: 1.22 × (180 / π) = 1.22 × 57.2958 = 69.9°
- **AND** result is rounded to 1 decimal place: 69.9°

#### Scenario: Mils to Degrees direct conversion
- **WHEN** elevation is displayed as 1600 mils
- **THEN** degrees equivalent is: 1600 / 1018.59 × 57.2958 = 90.0°

### Requirement: Distance and Azimuth Calculation

The system SHALL calculate horizontal distance and compass bearing (azimuth) from mortar to target using X-Y coordinates.

#### Scenario: Distance calculation (Euclidean)
- **WHEN** mortar is at (1000, 1500) and target is at (1300, 1800)
- **THEN** distance is: sqrt((1300-1000)² + (1800-1500)²) = sqrt(90000 + 90000) = 424.3 meters

#### Scenario: Azimuth calculation (compass bearing)
- **WHEN** mortar is at (1000, 1000) and target is at (1500, 1000) (directly East)
- **THEN** atan2(1000-1000, 1500-1000) = atan2(0, 500) = 0 radians
- **AND** converted to compass bearing: 90° (East)

#### Scenario: Azimuth North (0 degrees)
- **WHEN** mortar is at (1000, 1000) and target is at (1000, 500) (directly North/up)
- **THEN** azimuth calculation yields 0° or 360° (North)

#### Scenario: Azimuth negative angle handling
- **WHEN** atan2 returns negative angle (e.g., -45°)
- **THEN** angle is normalized to 0-360° range by adding 360°

### Requirement: Time of Flight Calculation

The system SHALL calculate projectile time of flight from mortar to target accounting for trajectory arc and height difference.

#### Scenario: Time of flight calculation
- **WHEN** distance is 800m, elevation angle is 1.2 radians, height difference is +50m
- **THEN** TOF is calculated using: `(2 * v₀ * sin(φ)) / g` for high-angle approximation
- **AND** result is returned in seconds (e.g., 8.3 seconds)

#### Scenario: Short range TOF
- **WHEN** distance is 200m
- **THEN** TOF is approximately 2-3 seconds

#### Scenario: Maximum range TOF
- **WHEN** distance is 1500m (maximum)
- **THEN** TOF is approximately 15-18 seconds

### Requirement: Grid Reference Parsing

The system SHALL parse PR grid notation (e.g., "D6-7") and convert to world XY coordinates in meters.

#### Scenario: Standard grid reference
- **WHEN** input is "D6-7" on 2km map (grid_scale = 153.85m)
- **THEN** column D is parsed as index 3 (A=0, B=1, C=2, D=3)
- **AND** row 6 is parsed as index 5 (1=0, 2=1, ..., 6=5)
- **AND** keypad 7 is top-left of square (offsets: x=0, y=0)
- **AND** base X = 3 × 153.85 = 461.54m
- **AND** base Y = 5 × 153.85 = 769.23m
- **AND** final position: {x: 461.54, y: 769.23}

#### Scenario: Keypad offset calculation
- **WHEN** keypad is 5 (center of square) on 2km map
- **THEN** X offset is grid_scale / 3 = 51.28m
- **AND** Y offset is grid_scale / 3 = 51.28m
- **AND** final X = base_x + 51.28, final Y = base_y + 51.28

#### Scenario: Invalid grid reference
- **WHEN** input is "Z99-10" (column Z invalid, row 99 out of range, keypad 10 invalid)
- **THEN** validation fails and error is returned
- **AND** error message lists specific problems: "Invalid column, Invalid row, Invalid keypad"

#### Scenario: Case insensitive parsing
- **WHEN** input is "d6-7" (lowercase)
- **THEN** parsing succeeds identically to "D6-7"

### Requirement: XY to Grid Reference Conversion

The system SHALL convert world XY coordinates back to PR grid notation for display purposes.

#### Scenario: XY to grid conversion
- **WHEN** position is (600, 900) on 2km map (grid_scale = 153.85m)
- **THEN** column is: floor(600 / 153.85) = 3 = 'D'
- **AND** row is: floor(900 / 153.85) = 5 = row 6
- **AND** within-square offsets determine keypad number
- **AND** result is "D6-[keypad]"

### Requirement: Bilinear Interpolation for Height Sampling

The system SHALL use bilinear interpolation to sample elevation smoothly between heightmap pixels avoiding abrupt height changes.

#### Scenario: Fractional pixel coordinates
- **WHEN** world position (1234.5, 2345.6) converts to pixel position (123.7, 234.8)
- **THEN** 4 surrounding pixels are identified: (123,234), (124,234), (123,235), (124,235)
- **AND** height values are read: h1=32000, h2=32100, h3=32050, h4=32150
- **AND** fractional parts are: fx=0.7, fy=0.8
- **AND** top interpolation: (1-0.7)*32000 + 0.7*32100 = 32070
- **AND** bottom interpolation: (1-0.7)*32050 + 0.7*32150 = 32120
- **AND** final interpolation: (1-0.8)*32070 + 0.8*32120 = 32110
- **AND** elevation is: (32110 / 65535) × height_scale

#### Scenario: Integer pixel coordinates (no interpolation needed)
- **WHEN** world position converts exactly to pixel (123.0, 234.0)
- **THEN** height is read directly from pixel (123, 234)
- **AND** no interpolation calculation is performed

#### Scenario: Boundary pixel handling
- **WHEN** pixel coordinates are at edge (0, Y) or (X, 0)
- **THEN** boundary pixels are used for interpolation
- **AND** +1 border pixels are accessible (resolution includes border)

### Requirement: Heightmap JSON Loading and Caching

The system SHALL load heightmap JSON files from `/processed_maps/` directory and cache in memory to avoid redundant network requests.

#### Scenario: First heightmap load
- **WHEN** user selects "Muttrah City 2" map
- **THEN** fetch request is made to `/processed_maps/muttrah_city_2/heightmap.json`
- **AND** JSON is parsed and stored in memory cache
- **AND** subsequent elevation queries use cached data

#### Scenario: Cached heightmap reuse
- **WHEN** second elevation query is made on same map
- **THEN** no network request is made
- **AND** cached heightmap data is used directly

#### Scenario: Metadata loading
- **WHEN** map is selected
- **THEN** metadata.json is loaded from `/processed_maps/[map]/metadata.json`
- **AND** map_size, height_scale, grid_scale values are extracted and cached

#### Scenario: Missing heightmap file
- **WHEN** heightmap.json does not exist for requested map
- **THEN** fetch returns 404 error
- **AND** error message displays: "Heightmap not found for [map_name]"
- **AND** UI shows error state instead of crashing

### Requirement: Coordinate System Implementation (Top-Left Origin)

The system SHALL use top-left corner as origin (0, 0) with X increasing rightward (East) and Y increasing downward (South).

#### Scenario: Origin position
- **WHEN** coordinate is (0, 0)
- **THEN** position is at top-left corner of map (Northwest)

#### Scenario: X-axis direction
- **WHEN** X increases from 1000 to 1500
- **THEN** position moves rightward (West to East)

#### Scenario: Y-axis direction
- **WHEN** Y increases from 1000 to 1500
- **THEN** position moves downward (North to South)

#### Scenario: Azimuth 0 degrees (North)
- **WHEN** target is directly above (lower Y) mortar
- **THEN** azimuth is 0° (North, upward on map)

#### Scenario: Azimuth 90 degrees (East)
- **WHEN** target is directly right (higher X) of mortar
- **THEN** azimuth is 90° (East, rightward on map)

### Requirement: Edge Case Validation

The system SHALL validate all inputs and edge cases, returning descriptive errors instead of crashing or producing invalid results.

#### Scenario: Out of map bounds
- **WHEN** coordinate X is -100 or Y is 5000 on 2km map (map_size = 2048)
- **THEN** validation fails with error "Position outside map boundaries"

#### Scenario: Extreme elevation difference warning
- **WHEN** height difference ΔZ is +250m (target 250m higher than mortar)
- **THEN** warning message displays: "WARNING - Extreme elevation difference may reduce accuracy"
- **AND** calculation still proceeds if physically possible

#### Scenario: Invalid heightmap resolution
- **WHEN** loaded heightmap has resolution 512×512 (unexpected)
- **THEN** error displays: "Invalid heightmap resolution - expected 1025 or 2049"
- **AND** map is marked as unusable

### Requirement: Pure Function Architecture

The system SHALL implement all calculation functions as pure functions (deterministic, no side effects, no DOM access) enabling unit testing and reusability.

#### Scenario: Function purity test
- **WHEN** calculateDistance(1000, 1000, 1500, 1300) is called twice
- **THEN** both calls return identical result: 583.1 meters
- **AND** no global state is modified
- **AND** no DOM elements are accessed or modified

#### Scenario: Modularity test
- **WHEN** ballistics.js module is imported in Node.js (no browser)
- **THEN** all exported functions work correctly
- **AND** no "window is not defined" or "document is not defined" errors occur

### Requirement: Performance Target Compliance

The system SHALL complete all calculations within 50ms to ensure responsive user experience during interactive marker dragging.

#### Scenario: Single firing solution performance
- **WHEN** full calculation pipeline executes (grid parse → XY → elevation → firing solution)
- **THEN** total execution time is less than 50ms on mid-range hardware

#### Scenario: Bilinear interpolation performance
- **WHEN** 100 elevation samples are taken rapidly
- **THEN** total time is less than 500ms (5ms per sample average)

