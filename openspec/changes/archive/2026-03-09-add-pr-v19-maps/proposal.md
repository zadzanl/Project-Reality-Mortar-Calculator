## Why

Project Reality: BF2 v1.9 was released on February 27th, 2026, adding two new maps: **Talbisah** and **Icebreaker**. The mortar calculator currently supports 83 maps from v1.8 and earlier. Players on v1.9 servers using these new maps have no mortar calculation support. The tool needs to process and include these maps to stay current.

Additionally, `mapsList.json` (used by the Android/offline build) is maintained manually and has no generation script — it must be updated by hand whenever maps are added. A small helper script would prevent future drift between `processed_maps/` and the static manifest.

## What Changes

- **Collect raw map data** for `talbisah` and `icebreaker` from a local PR v1.9 installation using `collect_maps.py`
- **Process heightmaps** for both maps using `process_maps.ipynb` — generates `heightmap.json.gz`, `metadata.json`, and `minimap.png`
- **Generate contour maps** for both maps using `generate_contours.ipynb` — generates `contourmap.png` and updates `metadata.json`
- **Update `mapsList.json`** — add both maps and update `count` from 83 to 85
- **Add a `generate_maps_list.py` script** to auto-generate `mapsList.json` from `processed_maps/` contents, preventing manual drift
- **Document `the_falklands` exclusion** in `processed_maps/README.md` and `AGENTS.md` — it is intentionally skipped due to its non-standard 8km+ map boundary

## Capabilities

### New Capabilities
- `maps-list-generation`: Script to auto-generate `mapsList.json` from `processed_maps/` directory contents, replacing manual maintenance

### Modified Capabilities
- `map-processor`: Add `talbisah` and `icebreaker` to the set of processed maps (no requirement changes to the pipeline itself — just new data flowing through it)

## Impact

- **Data files**: New folders `processed_maps/talbisah/` and `processed_maps/icebreaker/` (4 files each)
- **Data files**: New folders `raw_map_data/talbisah/` and `raw_map_data/icebreaker/` (2 files each)
- **Manifest**: `raw_map_data/manifest.json` updated by `collect_maps.py`
- **Static manifest**: `mapsList.json` updated (count 83 → 85)
- **New script**: `processor/generate_maps_list.py`
- **Documentation**: `processed_maps/README.md` and `AGENTS.md` updated with `the_falklands` note
- **Android build**: No changes needed — `build-android.bat` already copies `mapsList.json` into `www/`
- **Frontend**: No code changes — Flask auto-discovers new maps via `/maps/list`, Android uses updated `mapsList.json`
- **Physics/ballistics**: No changes — v1.9 did not alter mortar mechanics
