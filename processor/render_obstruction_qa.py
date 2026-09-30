#!/usr/bin/env python3
"""Render minimap and extracted obstruction geometry for maintainer QA."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
MAPS = ("asad_khal", "fools_road", "muttrah_city_2", "belyaevo", "adak")
OUTPUT = ROOT / "openspec" / "changes" / "add-opening-flow-simulator" / "artifacts" / "qa_obstruction_images"

COLORS = {
    "road": (230, 30, 30, 210),
    "building": (0, 110, 255, 230),
    "wall": (0, 170, 255, 230),
    "fence": (40, 220, 255, 230),
    "container": (40, 80, 220, 230),
    "unclassified": (255, 170, 0, 190),
    "vegetation": (0, 220, 70, 150),
}


def point(value, map_size, width):
    return int(round(float(value) / map_size * (width - 1)))


def render(map_name):
    directory = ROOT / "processed_maps" / map_name
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    data = json.loads((directory / "obstructions.json").read_text(encoding="utf-8"))
    base = Image.open(directory / "minimap.png").convert("RGBA")
    width, height = base.size
    map_size = float(metadata["map_size"])
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for road in data["roads"]:
        for triangle in road["triangles"]:
            points = [(point(x, map_size, width), point(y, map_size, height)) for x, y in triangle]
            draw.line(points + [points[0]], fill=COLORS["road"], width=max(1, width // 1500))

    radius = max(1, width // 700)
    for item in data["statics"]:
        color = COLORS.get(item["class"], COLORS["unclassified"])
        x = point(item["x"], map_size, width)
        y = point(item["y"], map_size, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    plant_radius = max(1, width // 1200)
    for item in data["vegetation"]:
        x = point(item["x"], map_size, width)
        y = point(item["y"], map_size, height)
        draw.ellipse((x - plant_radius, y - plant_radius, x + plant_radius, y + plant_radius), fill=COLORS["vegetation"])

    result = Image.alpha_composite(base, overlay)
    output = OUTPUT / ("qa_obstructions_" + map_name + ".png")
    result.save(output)
    all_points = [(item["x"], item["y"]) for item in data["statics"]]
    if all_points:
        span = (min(x for x, _ in all_points), max(x for x, _ in all_points),
                min(y for _, y in all_points), max(y for _, y in all_points))
    else:
        span = None
    print("%s: %s counts=%s static_span=%s" % (map_name, output, data["counts"], span))


def main():
    names = tuple(sys.argv[1:]) or MAPS
    for name in names:
        render(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())