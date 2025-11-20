# Processed Maps

This directory contains processed heightmaps (JSON), metadata (JSON), and minimap images (PNG).

## Structure

```
processed_maps/
├── muttrah_city_2/
│   ├── heightmap.json        # 16-bit height data
│   ├── metadata.json         # Map configuration (includes minimap info)
│   ├── minimap.png           # Visual map representation (converted from DDS)
│   └── background.png        # Optional: Scaled version for UI
├── fallujah_west/
│   ├── heightmap.json
│   ├── metadata.json
│   ├── minimap.png
│   └── background.png
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
