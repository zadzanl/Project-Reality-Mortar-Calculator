## 1. Collect Raw Map Data (Phase 1)

- [x] 1.1 Run `python processor/collect_maps.py` on machine with PR v1.9 installed
- [x] 1.2 Verify `raw_map_data/talbisah/server.zip` and `raw_map_data/talbisah/client.zip` exist
- [x] 1.3 Verify `raw_map_data/icebreaker/server.zip` and `raw_map_data/icebreaker/client.zip` exist
- [x] 1.4 Verify `raw_map_data/manifest.json` is updated with both new maps

## 2. Process Heightmaps and Minimaps (Phase 2)

- [x] 2.1 Run `processor/process_maps.ipynb` to process `talbisah` and `icebreaker`
- [x] 2.2 Verify `processed_maps/talbisah/heightmap.json.gz` exists and is valid
- [x] 2.3 Verify `processed_maps/talbisah/metadata.json` contains correct map_size and height_scale
- [x] 2.4 Verify `processed_maps/talbisah/minimap.png` exists
- [x] 2.5 Verify `processed_maps/icebreaker/heightmap.json.gz` exists and is valid
- [x] 2.6 Verify `processed_maps/icebreaker/metadata.json` contains correct map_size and height_scale
- [x] 2.7 Verify `processed_maps/icebreaker/minimap.png` exists

## 3. Generate Contour Maps (Phase 3)

- [x] 3.1 Run `processor/generate_contours.ipynb` for `talbisah` and `icebreaker`
- [x] 3.2 Verify `processed_maps/talbisah/contourmap.png` exists and has correct resolution
- [x] 3.3 Verify `processed_maps/talbisah/metadata.json` includes `contourmap` section
- [x] 3.4 Verify `processed_maps/icebreaker/contourmap.png` exists and has correct resolution
- [x] 3.5 Verify `processed_maps/icebreaker/metadata.json` includes `contourmap` section

## 4. Create Maps List Generation Script

- [x] 4.1 Create `processor/generate_maps_list.py` that scans `processed_maps/` for folders with `metadata.json`
- [x] 4.2 Script outputs `mapsList.json` at repo root with `{count, maps: [{name, path}]}` format
- [x] 4.3 Script sorts maps alphabetically and skips folders without `metadata.json`
- [x] 4.4 Run script and verify `mapsList.json` matches expected output (count: 85, includes talbisah and icebreaker)

## 5. Documentation Updates

- [x] 5.1 Add `the_falklands` exclusion note to `processed_maps/README.md` explaining non-standard map boundary
- [x] 5.2 Add `the_falklands` exclusion note to `AGENTS.md` so agents do not attempt to process it

## 6. Verification

- [x] 6.1 Start Flask server (`python calculator/server.py`) and verify both maps appear in dropdown
- [x] 6.2 Load `talbisah` map — verify minimap renders, heightmap loads, contour overlay works
- [x] 6.3 Load `icebreaker` map — verify minimap renders, heightmap loads, contour overlay works
- [x] 6.4 Place mortar and target on each new map — verify distance, bearing, and elevation calculations produce valid results
