## ADDED Requirements

### Requirement: Authoritative terrain sampling
The terrain pipeline SHALL load each map's processed 16-bit heightmap and metadata, convert raw samples to meters using `pixel_value / 65535.0 * height_scale`, and use horizontal spacing `map_size / (resolution - 1)`. It SHALL record the source metadata, resolution, spacing, and conversion formula in its output sidecar.

#### Scenario: Correct metric conversion
- **WHEN** the pipeline processes a map with a 1024 meter world, 513 samples, and height scale 163.8375
- **THEN** adjacent samples use 2 meter horizontal spacing
- **AND** a raw height value of 65535 converts to 163.8375 meters
- **AND** the sidecar records those values and the authoritative metadata source

#### Scenario: Coarse source resolution
- **WHEN** a map's heightmap spacing is coarser than the requested simulation cell size
- **THEN** the pipeline does not invent subcell terrain detail
- **AND** the sidecar records the degraded source spacing

### Requirement: Native-resolution slope feature
The terrain pipeline SHALL calculate a per-sample slope feature from metric elevation using the documented native-resolution gradient method and SHALL handle map boundaries without invented elevation padding.

#### Scenario: Flat terrain
- **WHEN** the input heightmap is a constant-elevation plane
- **THEN** slope is zero or within the documented floating-point tolerance at every interior sample
- **AND** the resulting terrain classification is not extreme slope

#### Scenario: Constant ramp
- **WHEN** the input heightmap is a plane with a known constant grade
- **THEN** the calculated interior slope matches the analytic grade within the configured test tolerance
- **AND** the result does not depend on whether the plane is oriented north-south or east-west

#### Scenario: Boundary samples
- **WHEN** slope is calculated at the outermost heightmap samples
- **THEN** the pipeline uses its documented one-sided or equivalent boundary rule
- **AND** no artificial zero-height border is introduced

### Requirement: Step and ledge detection
The terrain pipeline SHALL calculate neighboring elevation rise and edge grade as separate features from average slope, including the correct horizontal distance for any diagonal neighbor. These features SHALL be available for conservative simulation-cell aggregation.

#### Scenario: Single ledge
- **WHEN** a synthetic heightmap contains two flat areas separated by a one-cell elevation step
- **THEN** the edge-rise feature identifies the step
- **AND** downsampling does not remove the hazard merely because most of the destination cell is flat

#### Scenario: Diagonal neighbor
- **WHEN** a diagonal neighbor is evaluated
- **THEN** its horizontal distance uses the diagonal sample spacing rather than the cardinal spacing

### Requirement: Metric-scale roughness
The pipeline SHALL support a configurable local roughness feature based on detrended elevation residuals over an odd, metric-bounded neighborhood. A map-width-relative moving average SHALL NOT be the primary terrain classifier.

#### Scenario: Tilted smooth plane
- **WHEN** roughness is calculated on a smooth tilted plane
- **THEN** detrended roughness is near zero even though slope is nonzero

#### Scenario: Local uneven terrain
- **WHEN** a local neighborhood contains bumps or depressions around its fitted grade
- **THEN** roughness increases relative to an equally sloped smooth plane
- **AND** the sidecar records the neighborhood size and roughness policy

#### Scenario: Map-width window rejected
- **WHEN** a configuration requests a `map_size / 32` window as the primary roughness or traversability signal
- **THEN** the pipeline rejects it or records a validation error
- **AND** it does not silently apply a 32-to-128 meter window across maps of different sizes

### Requirement: Continuous terrain movement cost
The pipeline SHALL produce one continuous movement cost per simulation cell by combining configured terrain signals, including slope and optional roughness, with separately sourced water, vegetation, static-obstruction, and road evidence. It SHALL preserve the distinction between low-cost terrain and explicit road membership.

#### Scenario: Flat terrain without road geometry
- **WHEN** a map has passable flat terrain but no decoded road triangles
- **THEN** the terrain cells receive ordinary baseline terrain cost
- **AND** they remain eligible for movement
- **AND** they are not labeled as explicit roads solely because they are flat

#### Scenario: Explicit road geometry
- **WHEN** a road triangle covers a simulation cell
- **THEN** the cell records road membership separately from terrain class
- **AND** the configured road modifier may lower its movement cost
- **AND** road membership does not bypass configured extreme-slope or step hazards

#### Scenario: Heavy but passable surfaces
- **WHEN** a cell is identified as water, vegetation-heavy, or a heuristic static obstruction
- **THEN** its cost increases according to configured multipliers
- **AND** it remains passable unless an independent extreme-slope rule blocks it

### Requirement: Water and source-coverage status
The pipeline SHALL distinguish confirmed water evidence, candidate inland-water evidence, missing road geometry, and no road definitions. It SHALL not classify a surface as water or road from flatness alone.

#### Scenario: Missing client archive
- **WHEN** `compiledroads.con` contains mesh references but the matching `client.zip` is unavailable
- **THEN** the terrain output records road coverage as unavailable
- **AND** terrain cost processing continues using heightmap and other available evidence
- **AND** the result is not reported as a map with no roads

#### Scenario: No road definitions
- **WHEN** a map has no compiled road references
- **THEN** the output records that no road definitions were found
- **AND** ordinary terrain processing still runs

#### Scenario: Flat inland region
- **WHEN** a flat region is above global sea level and lacks independent water evidence
- **THEN** it is recorded as a candidate or unknown inland-water region
- **AND** it is not hard blocked or silently labeled confirmed water from flatness alone

### Requirement: Diagnostic terrain classification
The pipeline SHALL emit explainable diagnostic classes derived from the continuous features and configured thresholds. Diagnostic classes SHALL identify at least smooth traversable, rough traversable, slow, extreme slope, road, water evidence, and unknown coverage states where applicable.

#### Scenario: Class explains cost
- **WHEN** a simulation cell is classified
- **THEN** the output includes the class, continuous cost, and relevant feature values or references
- **AND** a reviewer can determine whether slope, step, roughness, road, water, vegetation, or static evidence affected it

#### Scenario: Road and terrain coexist
- **WHEN** a cell is both low-slope terrain and covered by a decoded road triangle
- **THEN** the output preserves both the terrain classification and explicit road membership
- **AND** the QA renderer can show the road overlay independently

### Requirement: Deterministic terrain artifacts
The terrain pipeline SHALL produce deterministic per-map outputs containing a compact cost grid, diagnostic metadata, source coverage, configuration provenance, and enough information for a later offline flow solver to consume the grid without recomputing terrain physics.

#### Scenario: Repeatable processing
- **WHEN** the same heightmap, obstruction input, metadata, and terrain configuration are processed twice
- **THEN** the cost grid and sidecar are byte-for-byte equivalent or equivalent under a documented serialization normalization
- **AND** no browser or external service is required

#### Scenario: Later flow integration
- **WHEN** a later flow solver loads the terrain artifact
- **THEN** it can obtain grid dimensions, origin, cell size, units, costs, passability sentinel, source coverage, and movement-parameter provenance from the artifact set
- **AND** it does not need to recalculate slope or roughness

### Requirement: Synthetic and map QA
The terrain pipeline SHALL include focused automated tests and maintainer QA overlays covering synthetic geometry and representative real maps.

#### Scenario: Synthetic regression suite
- **WHEN** the processor test suite runs
- **THEN** it covers a flat plane, analytic ramp, one-cell step, ridge threshold, and flat terrain with no road mesh
- **AND** failures identify the terrain feature or aggregation rule that changed

#### Scenario: Representative map QA
- **WHEN** QA overlays are generated for at least Asad Khal, Adak, and an urban map such as Muttrah City 2
- **THEN** slope and cost patterns are inspectable over the minimap
- **AND** missing road coverage is visibly or textually distinguished from true absence of road definitions
- **AND** the report lists any known source-resolution or elevation-calibration limitations

### Requirement: Engine-painted surface material diagnostic
The pipeline SHOULD decode engine-painted terrain material index textures (`detailmaps/tx*.dds` in client.zip) when decodable and emit the per-cell material class as an additive diagnostic. The material class SHALL NOT be a movement-cost multiplier by default. If the texture semantics cannot be verified, the layer SHALL be omitted and the omission recorded. Decal-class road segments SHALL be filtered or flagged before the road-membership mask is built.

#### Scenario: Material spike confirms semantics
- **WHEN** the Asad Khal spike resolves the index-to-material wiring and road-triangle overlap confirms the paved cluster
- **THEN** the terrain artifact includes a per-cell material class in its diagnostic grid and sidecar
- **AND** no cost multiplier is applied from it by default

#### Scenario: Material spike fails
- **WHEN** the texture semantics cannot be verified
- **THEN** the material field is absent or `unknown`
- **AND** the loader contract and remaining diagnostics are unaffected

#### Scenario: Decal-class segments excluded
- **WHEN** the road-membership mask is built
- **THEN** segments whose names match decal classes (stain, decal, parkinglot, oilstain) are filtered or flagged
- **AND** per-map flagged counts appear in the QA report
