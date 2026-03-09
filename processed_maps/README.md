# Processed Maps

This directory contains processed heightmaps (JSON), metadata (JSON), and minimap images (PNG).

## Structure

```
processed_maps/
├── muttrah_city_2/
│   ├── heightmap.json.gz     # Compressed 16-bit height data (gzip)
│   ├── metadata.json         # Map configuration (includes minimap info)
│   └── minimap.png           # Visual map representation (converted from DDS)
├── fallujah_west/
│   ├── heightmap.json.gz
│   ├── metadata.json
│   └── minimap.png
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

### heightmap.json.gz
- **Purpose:** 16-bit elevation data (gzip compressed)
- **Format:** Compressed JSON array of uint16 values (0-65535)
- **Size:** Typically 1-2 MB per map (compressed from 4-10 MB)
- **Resolution:** 1025×1025 or 2049×2049 pixels
- **Compression:** gzip level 9 (maximum compression)
- **Note:** Uncompressed .json files are NOT distributed to reduce package size

### minimap.png
- **Purpose:** Visual map representation (satellite/overview imagery)
- **Format:** PNG image (converted from DDS)
- **Size:** Typically 1-5 MB per map
- **Resolution:** 1024×1024, 2048×2048, or 4096×4096 pixels
- **Source:** Extracted from client.zip/info/ directory

### metadata.json
- **Purpose:** Map configuration
- **Contains:** Map size, height scale, grid scale, resolution, minimap metadata
- **Size:** ~500 bytes

## For End Users

These files are pre-processed and included in the repository. The web calculator loads them directly - no processing needed.

## Do Not Modify Manually

This directory is managed by `process_maps.ipynb`. The notebook automatically commits and pushes processed maps to GitHub.

## Excluded Maps

### the_falklands
This map is intentionally excluded from processing. The primary game area is 8km × 8km, but airfields and a helicopter carrier extend beyond this boundary, making the total map area significantly larger than standard maps. The processing pipeline's default size inference would produce incorrect results for this non-standard layout. The raw data exists in `raw_map_data/the_falklands/` but requires special handling in a dedicated change.
