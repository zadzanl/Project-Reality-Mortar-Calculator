# Processed Maps

This directory contains processed heightmaps and metadata in JSON format.

## Structure

```
processed_maps/
├── muttrah_city_2/
│   ├── heightmap.json        # 16-bit height data
│   └── metadata.json         # Map configuration
├── fallujah_west/
│   ├── heightmap.json
│   └── metadata.json
└── ...
```

## How to Generate

Process maps using the Jupyter notebook:

```bash
jupyter notebook processor/process_maps.ipynb
```

Or upload to Google Colab for cloud processing.

See `processor/README.md` for detailed instructions.

## File Formats

### heightmap.json
- **Purpose:** 16-bit elevation data
- **Format:** JSON array of uint16 values (0-65535)
- **Size:** Typically 2-10 MB per map
- **Resolution:** 1025×1025 or 2049×2049 pixels

### metadata.json
- **Purpose:** Map configuration
- **Contains:** Map size, height scale, grid scale, resolution
- **Size:** ~300 bytes

## For End Users

These files are pre-processed and included in the repository. The web calculator loads them directly - no processing needed.

## Do Not Modify Manually

This directory is managed by `process_maps.ipynb`. The notebook automatically commits and pushes processed maps to GitHub.
