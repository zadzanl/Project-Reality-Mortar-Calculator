# Archived Proposal: Map Processing Pipeline

> Status: ARCHIVED (Completed)
> Archived on: 2025-11-19
> Archived file: openspec/changes/archive/add-map-processing-pipeline-archived-2025-11-19.md

## Why

The mortar calculator needs two types of data from Project Reality: BF2 maps:
1. **Height data (heightmaps)** - Tells us if the target is higher or lower than the mortar
2. **Visual map data (minimaps)** - Shows satellite/overview imagery for user orientation

We need to:
1. Copy height data files (server.zip) and minimap files (client.zip) from game installation
2. Check that files are not corrupted
3. Convert heightmaps to JSON format and minimaps to PNG format (formats web browsers can read)
4. Make files work without internet

Right now, we have no system to do this.

## What Changes

- **Phase 1 - Local Collection Script** (`processor/collect_maps.py`):
  - Find PR:BF2 game installation on your computer
  - Search `/mods/pr/levels/` folder for map files:
    - `server.zip` (contains heightmap data)
    - `client.zip` (contains minimap textures in info/ directory)
  - Check each file type:
    - server.zip: verify not broken and contains heightmapprimary.raw (case-insensitive)
    - client.zip: verify not broken and contains info/ directory with .dds files
  - Calculate file fingerprints to find duplicate files and detect changes (separate MD5 for each zip type)
  - Copy both zip types to `/raw_map_data/[map_name]/` folder
  - Handle gracefully if client.zip missing (heightmap-only mode)
  - Create `manifest.json` list file showing all collected maps with metadata for both file types
  - Set up Git LFS (large file storage) if total file size is bigger than 10MB
  - Create report showing what was collected (including maps with/without minimaps) and what to do next

- **Phase 2 - Cloud Processing Notebook** (`processor/process_maps.ipynb`):
  - Jupyter notebook (runs in Google Colab or on your computer)
  - Read the manifest list and find all server.zip and client.zip files in `/raw_map_data/`
  - **Heightmap Processing:**
    - Extract heightmapprimary.raw (height data file) from each server.zip (case-insensitive)
    - Read map settings files (init.con has map size, terrain.con has height scale)
    - Convert height data to JSON format (no data loss, works in web browsers)
  - **Minimap Processing:**
    - Extract DDS texture files from client.zip/info/ directory
    - Convert DDS to PNG format using Pillow library (web-compatible)
    - Handle missing client.zip gracefully (heightmap-only mode)
    - Validate PNG dimensions and file size
  - Calculate grid size based on map size (PR uses 13×13 grid)
  - Create metadata.json for each map (stores map size, height scale, grid size, image size, minimap info)
  - Save all processed files to `/processed_maps/[map_name]/` folder (heightmap.json, minimap.png, metadata.json)
  - Upload results to GitHub automatically
  - Show progress as maps are processed

- **Data Format Specifications**:
  - **Heightmap Input:** 16-bit little-endian RAW files (1025×1025 or 2049×2049 pixels)
  - **Heightmap Output:** JSON with uint16 array, resolution metadata, uncompressed
  - **Minimap Input:** DDS texture files (DXT1 compression) from client.zip/info/
  - **Minimap Output:** PNG images (1024×1024, 2048×2048, or 4096×4096 pixels)
  - **Metadata:** Map size (meters), height scale (meters), grid scale, resolution, minimap info (source, resolution, file size)

## Impact

- **Affected Specs**: Creates new capability `map-processor`
- **Affected Code**: 
  - New files: `processor/collect_maps.py`, `processor/process_maps.ipynb`, `processor/README.md`
  - New directories: `/raw_map_data/`, `/processed_maps/`
  - Repository root: `.gitattributes` (Git LFS configuration)
- **Dependencies**: Python 3.8 or newer, NumPy library, Pillow library (DDS to PNG conversion), built-in Python tools
- **Data Flow**: Game files (server.zip + client.zip) → raw_map_data/ → processed_maps/ (JSON + PNG) → GitHub
- **User Impact**: Only maintainers run this. End users get pre-processed heightmaps and minimaps ready to use
