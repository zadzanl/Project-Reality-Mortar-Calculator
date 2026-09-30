#!/usr/bin/env python3
"""Repair processed metadata from authoritative heightdata.con values."""
import json
from pathlib import Path
import sys

from bf2_mapinfo import read_mapinfo

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_map_data"
OUT = ROOT / "processed_maps"
EXCLUDED = {"the_falklands"}


def main():
    repaired = 0
    skipped = []
    for map_dir in sorted(RAW.iterdir()):
        server_zip = map_dir / "server.zip"
        if not map_dir.is_dir() or map_dir.name in EXCLUDED or not server_zip.exists():
            continue
        info = read_mapinfo(server_zip)
        metadata_path = OUT / map_dir.name / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            skipped.append(map_dir.name)
            continue
        required = ("map_size", "height_scale", "heightmap_resolution")
        missing = [key for key in required if info[key] is None]
        if missing:
            skipped.append(map_dir.name + ":" + ",".join(missing))
            continue
        metadata["map_size"] = info["map_size"]
        metadata["height_scale"] = info["height_scale"]
        metadata["heightmap_resolution"] = info["heightmap_resolution"]
        if info["sea_level_m"] is not None:
            metadata["sea_level_m"] = info["sea_level_m"]
        metadata["heightmap_size_source"] = "heightdata.con setHeightmapSize / setScale"
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
        repaired += 1
    print("Repaired metadata:", repaired)
    print("Unverifiable:", ", ".join(skipped) if skipped else "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())