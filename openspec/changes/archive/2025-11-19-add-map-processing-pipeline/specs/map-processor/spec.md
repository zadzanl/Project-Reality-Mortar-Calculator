# Map Processor Specification

## ADDED Requirements

### Requirement: PR Installation Auto-Detection

The system SHALL automatically detect Project Reality: BF2 installation at standard Windows paths and allow custom path specification via command-line argument.

#### Scenario: Standard installation found
- **WHEN** script is run without arguments on system with PR:BF2 at `C:\Program Files (x86)\Project Reality\Project Reality BF2`
- **THEN** installation is detected and `/mods/pr/levels/` directory is scanned for maps

#### Scenario: Custom path provided
- **WHEN** script is run with `--path "D:\Games\PR"` argument
- **THEN** custom path is checked first before standard paths

#### Scenario: No installation found
- **WHEN** script is run on system without PR:BF2 installation
- **THEN** error message displays searched paths and instructs user to provide --path argument
- **AND** script exits with code 1

### Requirement: Server.zip Validation

The system SHALL validate each server.zip file for integrity and required content before processing.

#### Scenario: Valid server.zip
- **WHEN** server.zip is well-formed zip file containing heightmapprimary.raw (case-insensitive)
- **THEN** validation passes and file is queued for processing

#### Scenario: Corrupted zip file
- **WHEN** server.zip is corrupted or incomplete
- **THEN** validation fails with error "Corrupted file in zip: [filename]"
- **AND** map is skipped and error is logged

#### Scenario: Missing heightmap
- **WHEN** server.zip is valid but does not contain heightmapprimary.raw (case-insensitive)
- **THEN** validation fails with error "Missing heightmapprimary.raw"
- **AND** map is skipped and error is logged

### Requirement: MD5 Checksum Duplicate Detection

The system SHALL calculate MD5 checksums for each server.zip and compare against existing manifest to detect duplicates and version changes.

#### Scenario: Identical file already collected
- **WHEN** server.zip MD5 matches existing entry in manifest.json
- **THEN** file is skipped with message "Skipped (identical to existing)"
- **AND** existing manifest entry is preserved

#### Scenario: Modified file detected
- **WHEN** server.zip MD5 differs from existing entry in manifest.json
- **THEN** file is re-copied and manifest entry is updated with new MD5 and timestamp
- **AND** status is marked as "updated"

#### Scenario: New map discovered
- **WHEN** map name not found in existing manifest
- **THEN** file is copied and new manifest entry is created
- **AND** status is marked as "new"

### Requirement: Manifest Generation

The system SHALL generate manifest.json containing inventory of all collected maps with metadata (name, MD5, size, timestamp, source path).

#### Scenario: Manifest created successfully
- **WHEN** collection completes with 45 maps processed
- **THEN** manifest.json is created in raw_map_data/ directory
- **AND** manifest contains array of 45 map entries
- **AND** manifest includes total_maps, total_size_bytes, total_size_mb, collection_date, format_version

#### Scenario: Empty collection
- **WHEN** no valid maps are found
- **THEN** manifest.json is created with empty maps array
- **AND** total_maps is 0

### Requirement: Git LFS Auto-Configuration

The system SHALL automatically configure Git LFS if total collected file size exceeds 10MB threshold.

#### Scenario: Size below threshold
- **WHEN** total collected size is 8MB
- **THEN** message displays "Total size (8.0 MB) below 10 MB threshold"
- **AND** Git LFS configuration is optional
- **AND** .gitattributes is not modified

#### Scenario: Size exceeds threshold
- **WHEN** total collected size is 150MB
- **THEN** .gitattributes file is created or updated
- **AND** LFS patterns are added: `*.zip filter=lfs diff=lfs merge=lfs -text`
- **AND** message instructs user to run `git lfs install` if not configured

#### Scenario: LFS already configured
- **WHEN** .gitattributes already contains LFS patterns
- **THEN** message displays "LFS patterns already configured"
- **AND** file is not modified

### Requirement: 16-bit RAW Heightmap Extraction

The system SHALL extract heightmapprimary.raw (case-insensitive) from server.zip and parse as 16-bit little-endian unsigned integer array.

#### Scenario: Standard 2km map
- **WHEN** heightmapprimary.raw is extracted from 2km map server.zip
- **THEN** raw bytes are parsed as little-endian uint16 (`<u2` dtype in NumPy)
- **AND** array is reshaped to 1025×1025 resolution (including +1 border)
- **AND** values range from 0 to 65535

#### Scenario: Large 4km map
- **WHEN** heightmapprimary.raw is extracted from 4km map server.zip
- **THEN** array is reshaped to 2049×2049 resolution
- **AND** +1 border is preserved for engine compatibility

#### Scenario: Corrupted heightmap
- **WHEN** heightmapprimary.raw cannot be parsed or has unexpected size
- **THEN** error "Failed to extract heightmap" is raised
- **AND** map processing is skipped

### Requirement: Map Configuration Parsing

The system SHALL extract and parse init.con and terrain.con files to determine map size and height scale using regex patterns.

#### Scenario: Config files present
- **WHEN** init.con contains `heightmapCluster.create 2048 2048`
- **AND** terrain.con contains `HeightmapCluster.setHeightScale 300`
- **THEN** map_size is parsed as 2048 meters
- **AND** height_scale is parsed as 300 meters

#### Scenario: Missing init.con
- **WHEN** init.con is not found in server.zip
- **THEN** map_size is inferred from heightmap resolution (1025 → 2048m, 2049 → 4096m)
- **AND** warning message displays "Map size not found, using default"

#### Scenario: Missing terrain.con
- **WHEN** terrain.con is not found in server.zip
- **THEN** height_scale defaults to 300 meters
- **AND** warning message displays "Height scale not found, using default: 300m"

### Requirement: JSON Heightmap Conversion

The system SHALL convert NumPy uint16 arrays to JSON format preserving full 16-bit precision (0-65535) in lossless, web-compatible structure.

#### Scenario: Successful conversion
- **WHEN** 1025×1025 heightmap array is converted to JSON
- **THEN** JSON file contains:
  - `resolution`: 1025
  - `width`: 1025
  - `height`: 1025
  - `format`: "uint16"
  - `data`: flat array of 1050625 integers (1025²)
  - `compression`: "none"
- **AND** file is written with compact separators (`,` and `:`)
- **AND** file size is 2-10 MB

#### Scenario: Conversion failure
- **WHEN** JSON serialization fails due to memory or disk error
- **THEN** error "Failed to convert heightmap to JSON" is raised
- **AND** map processing is skipped

### Requirement: Metadata JSON Generation

The system SHALL generate metadata.json for each map containing map_name, map_size, height_scale, grid_scale, heightmap_resolution, processed_at timestamp, and format_version.

#### Scenario: Metadata with parsed config
- **WHEN** map_size is 2048m and height_scale is 400m from config files
- **THEN** metadata.json contains:
  - `map_name`: "[map_name]"
  - `map_size`: 2048
  - `height_scale`: 400
  - `grid_scale`: 157.538 (2048 / 13)
  - `heightmap_resolution`: 1025
  - `processed_at`: ISO 8601 timestamp with 'Z' suffix
  - `format_version`: "1.0"

#### Scenario: Metadata with defaults
- **WHEN** config files are missing
- **THEN** default values are used (map_size inferred, height_scale=300)
- **AND** grid_scale is calculated from inferred map_size

### Requirement: Git Automation with Token Authentication

The system SHALL automatically commit processed maps to Git and push to GitHub using provided user credentials (name, email, personal access token).

#### Scenario: Successful commit and push
- **WHEN** user provides valid Git credentials and 45 maps are processed
- **THEN** processed_maps/ directory is staged with `git add processed_maps/`
- **AND** commit is created with message "chore: process maps - 45 updated (2025-11-19)"
- **AND** changes are pulled from origin/main first
- **AND** changes are pushed to GitHub using HTTPS URL with token authentication
- **AND** success message displays "Successfully pushed to GitHub!"

#### Scenario: No changes to commit
- **WHEN** all processed maps are already up-to-date in repository
- **THEN** message displays "No changes to commit (maps already up to date)"
- **AND** no commit is created

#### Scenario: Push conflict detected
- **WHEN** git pull returns merge conflict
- **THEN** error message displays conflict details
- **AND** manual instructions are provided for user to resolve

#### Scenario: Invalid credentials
- **WHEN** GitHub token is invalid or expired
- **THEN** push fails with authentication error
- **AND** manual push instructions are displayed

### Requirement: Processing Progress Indicators

The system SHALL display real-time progress indicators during batch processing including current map, X of Y completed, and per-map status.

#### Scenario: Batch processing display
- **WHEN** processing 45 maps
- **THEN** console displays "[1/45] muttrah_city_2" followed by per-operation status
- **AND** operations display progress: "Extracting heightmap...", "Converting to JSON...", etc.
- **AND** completion status shows "✓ muttrah_city_2 processed successfully"
- **AND** final summary displays processed count, errors, and duration in seconds/minutes

#### Scenario: Error during processing
- **WHEN** map 23 fails with extraction error
- **THEN** error displays "✗ ERROR: [error message]"
- **AND** processing continues with map 24
- **AND** failed maps are listed in final summary

### Requirement: Collection Report Generation

The system SHALL generate comprehensive collection report with summary statistics, collected maps list, errors, output paths, and next steps.

#### Scenario: Report with successful collection
- **WHEN** collection completes with 40 new maps, 3 updated, 2 unchanged, 0 errors
- **THEN** report displays:
  - Summary section with totals
  - Collected maps list with status icons (+, ↻, =), sizes, MD5 checksums
  - Output paths (raw_map_data/, manifest.json)
  - Next steps (review, commit, push, process)
- **AND** report is printed to console
- **AND** report is saved to processor/collection_report.txt

#### Scenario: Report with errors
- **WHEN** collection completes with 2 maps failing validation
- **THEN** errors section lists failed maps with reasons
- **AND** summary shows "✗ Errors: 2"

### Requirement: Continuous Processing on Failure

The system SHALL continue processing remaining maps if individual map processing fails, logging errors without halting execution.

#### Scenario: Single map failure in batch
- **WHEN** map 10 fails with corrupted zip error during batch of 45 maps
- **THEN** error is logged for map 10
- **AND** processing continues with map 11
- **AND** maps 11-45 are processed normally
- **AND** final summary shows 44 processed, 1 error
