# Archived Proposal: Map Processing Pipeline

> Status: ARCHIVED (Completed)
> Archived on: 2025-11-19
> Archived file: openspec/changes/archive/add-map-processing-pipeline-archived-2025-11-19.md

## Why

The mortar calculator needs height data from Project Reality: BF2 maps. This height data tells us if the target is higher or lower than the mortar.

We need to:
1. Copy height data files from the game installation
2. Check that files are not corrupted
3. Convert files to JSON format (a format web browsers can read)
4. Make files work without internet

Right now, we have no system to do this.

## What Changes

- **Phase 1 - Local Collection Script** (`processor/collect_maps.py`):
  - Find PR:BF2 game installation on your computer
  - Search `/mods/pr/levels/` folder for map files named `server.zip`
  - Check each server.zip file (make sure it is not broken and contains heightmapprimary.raw, case-insensitive)
  - Calculate file fingerprints to find duplicate files and detect changes
  - Copy good files to `/raw_map_data/[map_name]/` folder
  - Create `manifest.json` list file showing all collected maps
  - Set up Git LFS (large file storage) if total file size is bigger than 10MB
  - Create report showing what was collected and what to do next

- **Phase 2 - Cloud Processing Notebook** (`processor/process_maps.ipynb`):
  - Jupyter notebook (runs in Google Colab or on your computer)
  - Read the manifest list and find all server.zip files in `/raw_map_data/`
  - Extract heightmapprimary.raw (height data file) from each zip (case-insensitive)
  - Read map settings files (init.con has map size, terrain.con has height scale)
  - Convert height data to JSON format (no data loss, works in web browsers)
  - Calculate grid size based on map size (PR uses 13×13 grid)
  - Create metadata.json for each map (stores map size, height scale, grid size, image size)
  - Save all processed files to `/processed_maps/[map_name]/` folder
  - Upload results to GitHub automatically
  - Show progress as maps are processed

- **Data Format Specifications**:
  - Input: 16-bit little-endian RAW files (1025×1025 or 2049×2049 pixels)
  - Output: JSON with uint16 array, resolution metadata, uncompressed
  - Metadata: Map size (meters), height scale (meters), grid scale, resolution

## Impact

- **Affected Specs**: Creates new capability `map-processor`
- **Affected Code**: 
  - New files: `processor/collect_maps.py`, `processor/process_maps.ipynb`, `processor/README.md`
  - New directories: `/raw_map_data/`, `/processed_maps/`
  - Repository root: `.gitattributes` (Git LFS configuration)
- **Dependencies**: Python 3.8 or newer, NumPy library, built-in Python tools
- **Data Flow**: Game files → raw_map_data/ → processed_maps/ → GitHub
- **User Impact**: Only maintainers run this. End users get pre-processed files ready to use
