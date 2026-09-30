#!/usr/bin/env python3
"""Compare terrain samples with ground-hugging gameplay object elevations."""
import gzip
import json
from pathlib import Path
import statistics
import sys
import zipfile

from bf2_mapinfo import read_mapinfo
from extract_gamelayers import parse_gameplayobjects

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_map_data"
OUT = ROOT / "processed_maps"
MAPS = ("asad_khal", "adak", "fools_road", "muttrah_city_2", "kunar_province")


def sample(heightmap, x, y, map_size):
    resolution = int(heightmap["resolution"])
    fx = max(0.0, min(resolution - 1.0, x / map_size * (resolution - 1)))
    fy = max(0.0, min(resolution - 1.0, y / map_size * (resolution - 1)))
    ix, iy = int(fx), int(fy)
    jx, jy = min(ix + 1, resolution - 1), min(iy + 1, resolution - 1)
    tx, ty = fx - ix, fy - iy
    data = heightmap["data"]
    def value(px, py):
        return data[py * resolution + px]
    raw = ((value(ix, iy) * (1 - tx) + value(jx, iy) * tx) * (1 - ty)
           + (value(ix, jy) * (1 - tx) + value(jx, jy) * tx) * ty)
    return raw / 65535.0


def load_objects(map_name):
    with zipfile.ZipFile(RAW / map_name / "server.zip") as archive:
        names = [n for n in archive.namelist()
                 if n.replace("\\", "/").lower().startswith("gamemodes/")
                 and n.replace("\\", "/").lower().endswith("gameplayobjects.con")]
        preferred = next((n for n in names if "gpm_cq/32/" in n.replace("\\", "/").lower()), names[0])
        return parse_gameplayobjects(archive.read(preferred).decode("utf-8", errors="replace"))


def main():
    for name in MAPS:
        info = read_mapinfo(RAW / name / "server.zip")
        with gzip.open(OUT / name / "heightmap.json.gz", "rt", encoding="utf-8") as stream:
            heightmap = json.load(stream)
        residuals = []
        for item in load_objects(name)["spawn_points"]:
            if len(residuals) >= 12 or not all(key in item for key in ("x", "y", "z")):
                break
            world_x = item["x"] + info["map_size"] / 2.0
            world_y = info["map_size"] / 2.0 - item["z"]
            residuals.append(sample(heightmap, world_x, world_y, info["map_size"]) * info["height_scale"] - item["y"])
        if residuals:
            print("%s: n=%d median_abs=%.3f median=%.3f" %
                  (name, len(residuals), statistics.median(abs(x) for x in residuals), statistics.median(residuals)))
        else:
            print(name + ": no positioned spawn points")
    return 0


if __name__ == "__main__":
    sys.exit(main())