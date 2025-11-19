# Map Processing - Two-Phase Workflow

This directory contains scripts for processing Project Reality map data.

## Overview

The map processing workflow is split into two independent phases:

1. **Phase 1: Local Collection** (`collect_maps.py`) - Extracts server.zip files from PR:BF2 installation
2. **Phase 2: Cloud Processing** (`process_maps.ipynb`) - Converts heightmaps to JSON format

---

## Phase 1: Local Collection

### Prerequisites

- Project Reality: BF2 installed on your machine
- Python 3.8+ with standard library (no external dependencies)

### Usage

```bash
# Auto-detect PR:BF2 installation
python collect_maps.py

# Or specify custom path
python collect_maps.py --path "D:\Games\Project Reality\Project Reality BF2"
```

### What it does

1. Scans PR:BF2 installation for map folders in `/levels/`
2. Validates each `server.zip` file:
   - Checks zip integrity
   - Verifies contains `HeightmapPrimary.raw`
   - Calculates MD5 checksum
3. Copies server.zip files to `/raw_map_data/[map_name]/`
4. Handles duplicates (skips if identical, updates if changed)
5. Generates `manifest.json` with map inventory
6. Configures Git LFS if total size > 10MB

### Output

```
raw_map_data/
├── manifest.json              # Map inventory with checksums
├── muttrah_city_2/
│   └── server.zip
├── fallujah_west/
│   └── server.zip
└── ...
```

### Next Steps

After collection:

```bash
# Review report
cat processor/collection_report.txt

# Commit to GitHub
git add raw_map_data/ .gitattributes
git commit -m "chore: collect maps - [count] maps"
git push origin main
```

---

## Phase 2: Cloud Processing

### Prerequisites

- Repository cloned (includes `/raw_map_data/`)
- Python 3.8+ with NumPy
- Git credentials (name, email, GitHub Personal Access Token)

### Environments

**Google Colab (Recommended):**
1. Upload `process_maps.ipynb` to Google Colab
2. Clone your repository in Colab:
   ```python
   !git clone https://github.com/YOUR_USERNAME/Project_Reality-Mortar-Calculator.git
   %cd Project_Reality-Mortar-Calculator
   ```
3. Open notebook and run all cells

**Local Jupyter:**
```bash
# Install Jupyter (if needed)
pip install jupyter numpy

# Start notebook
jupyter notebook processor/process_maps.ipynb
```

### What it does

1. Reads `manifest.json` from `/raw_map_data/`
2. For each map:
   - Extracts `HeightmapPrimary.raw` from `server.zip`
   - Parses as 16-bit unsigned integer array
   - Extracts config files (`init.con`, `terrain.con`)
   - Converts RAW to JSON format (lossless)
   - Generates `metadata.json` with map configuration
3. Outputs to `/processed_maps/[map_name]/`
4. Automatically commits and pushes to GitHub

### Output

```
processed_maps/
├── muttrah_city_2/
│   ├── heightmap.json    # 16-bit height data
│   └── metadata.json     # Map configuration
├── fallujah_west/
│   ├── heightmap.json
│   └── metadata.json
└── ...
```

### Expected Runtime

- **Google Colab Free Tier:** ~8-12 minutes for 45 maps
- **Local Jupyter (modern laptop):** ~5-7 minutes for 45 maps

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────┐
│ Phase 1: LOCAL COLLECTION (Maintainer)             │
├─────────────────────────────────────────────────────┤
│ 1. Run: python collect_maps.py                     │
│ 2. Validates and copies server.zip files           │
│ 3. Outputs to: raw_map_data/                       │
│ 4. Commit and push to GitHub                       │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ GITHUB REPOSITORY (Source of Truth)                │
├─────────────────────────────────────────────────────┤
│ raw_map_data/        ← Git LFS tracked             │
│ processed_maps/      ← Will be updated by Phase 2  │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ Phase 2: CLOUD PROCESSING (Maintainer)            │
├─────────────────────────────────────────────────────┤
│ 1. Clone repository (git clone ...)                │
│ 2. Open: process_maps.ipynb                        │
│ 3. Run all cells (provide Git credentials)         │
│ 4. Processes maps from raw_map_data/               │
│ 5. Outputs to: processed_maps/                     │
│ 6. Auto-commits and pushes to GitHub               │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ END USERS                                           │
├─────────────────────────────────────────────────────┤
│ 1. Clone repository                                 │
│ 2. Run: calculator/server.py                       │
│ 3. Pre-processed maps already included!            │
└─────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Phase 1 Issues

**"Could not find PR:BF2 installation"**
- Verify game is installed
- Use `--path` to specify custom installation path
- Check that `/levels/` directory exists

**"Validation failed: Missing HeightmapPrimary.raw"**
- server.zip may be corrupted
- Re-verify game files through PR launcher
- Script will skip corrupted maps and continue

### Phase 2 Issues

**"manifest.json not found"**
- Run Phase 1 first: `python collect_maps.py`
- Verify `/raw_map_data/` directory exists
- Check that manifest.json was created

**"Git push failed"**
- Verify GitHub Personal Access Token is valid
- Check token has `repo` permissions
- May need to pull latest changes first: `git pull origin main`

**"NumPy not found"**
- Notebook will auto-install NumPy
- If fails, manually install: `pip install numpy`

---

## File Formats

### manifest.json Structure

```json
{
  "maps": [
    {
      "name": "muttrah_city_2",
      "md5": "a1b2c3d4e5f6...",
      "size_bytes": 1048576,
      "collected_at": "2024-11-19T10:30:00Z",
      "source_path": "C:\\PR\\levels\\muttrah_city_2",
      "status": "new"
    }
  ],
  "total_maps": 45,
  "total_size_bytes": 91750400,
  "total_size_mb": 87.5,
  "collection_date": "2024-11-19T10:30:00Z",
  "format_version": "1.0"
}
```

### heightmap.json Structure

```json
{
  "resolution": 1025,
  "width": 1025,
  "height": 1025,
  "format": "uint16",
  "data": [0, 1234, 5678, ...],
  "compression": "none"
}
```

### metadata.json Structure

```json
{
  "map_name": "muttrah_city_2",
  "map_size": 2048,
  "height_scale": 300,
  "grid_scale": 157.538,
  "heightmap_resolution": 1025,
  "processed_at": "2024-11-19T11:45:00Z",
  "format_version": "1.0"
}
```

---

## Development Notes

### Why Two Phases?

**Phase 1 (Local):**
- Requires PR:BF2 installation (not everyone has this)
- Fast and simple (standard library only)
- Maintainer-only operation
- Creates source of truth in Git

**Phase 2 (Cloud):**
- Works anywhere (no game installation needed)
- Can run on free cloud platforms (Colab, Kaggle)
- Reproducible and documented (Jupyter notebook)
- Auto-commits results back to repo

### Separation of Concerns

- Phase 1: File extraction and validation
- Phase 2: Data processing and conversion
- Each phase is independent and testable
- Clear handoff point: `/raw_map_data/` in GitHub

### Why Not Combine?

- Separation allows cloud processing without game installation
- Clear data lineage: raw → processed
- Easier to update processing logic without re-extracting
- End users never need to run either phase

---

## For End Users

**You don't need to run these scripts!**

Pre-processed maps are already included in the repository. Just:

1. Clone the repository
2. Run `calculator/server.py` or use `run.bat`
3. Maps will load automatically

**For custom maps:** Contact the maintainer to add maps to `/raw_map_data/`.

---

## License

See repository LICENSE file.
