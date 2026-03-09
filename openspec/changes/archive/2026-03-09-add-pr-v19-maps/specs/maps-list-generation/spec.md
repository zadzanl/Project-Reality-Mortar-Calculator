## ADDED Requirements

### Requirement: Maps List JSON Generation

The system SHALL provide a script (`processor/generate_maps_list.py`) that auto-generates `mapsList.json` from the contents of `processed_maps/` directory.

#### Scenario: Generate from processed maps directory
- **WHEN** script is run with no arguments
- **THEN** script scans `processed_maps/` for subdirectories containing `metadata.json`
- **AND** generates `mapsList.json` at the repository root
- **AND** JSON contains `count` (integer) and `maps` (sorted array of `{name, path}` objects)
- **AND** maps are sorted alphabetically by name

#### Scenario: Map folder without metadata
- **WHEN** a subdirectory in `processed_maps/` does not contain `metadata.json`
- **THEN** that directory is excluded from the generated list
- **AND** a warning is printed to console: "Skipped [folder_name]: no metadata.json"

#### Scenario: Output matches Flask endpoint format
- **WHEN** `mapsList.json` is generated
- **THEN** its schema matches the Flask `/maps/list` response exactly:
  ```json
  {
    "count": 85,
    "maps": [
      {"name": "adak", "path": "adak"},
      ...
    ]
  }
  ```
- **AND** Android build scripts (`build-android.bat`, `build-android.sh`) can consume it without modification

#### Scenario: Idempotent regeneration
- **WHEN** script is run multiple times with no changes to `processed_maps/`
- **THEN** `mapsList.json` content is identical each run (deterministic output)
