#!/usr/bin/env python3
"""Render deterministic terrain classes, roads, water, and coverage warnings."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from terrain_artifact import load_terrain_artifact

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "openspec" / "changes" / "add-terrain-traversability-model" / "artifacts" / "qa_terrain_images"
COLORS = {0: (160, 160, 160, 180), 1: (80, 200, 80, 120),
          2: (220, 200, 50, 150), 3: (255, 140, 20, 170),
          4: (220, 20, 20, 190), 5: (30, 100, 220, 180),
          6: (80, 160, 240, 150)}


def render(map_name, profile="infantry"):
    directory = ROOT / "processed_maps" / map_name
    artifact = load_terrain_artifact(directory / "terrain", profile)
    base = Image.open(directory / "minimap.png").convert("RGBA")
    width, height = base.size
    rows, cols = artifact["rows"], artifact["cols"]
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cell_w, cell_h = width / cols, height / rows
    for row in range(rows):
        for col in range(cols):
            color = COLORS[int(artifact["classes"][row, col])]
            box = (int(col * cell_w), int(row * cell_h),
                   int((col + 1) * cell_w), int((row + 1) * cell_h))
            draw.rectangle(box, fill=color)
            if artifact["road_mask"][row, col]:
                draw.rectangle(box, outline=(255, 255, 255, 220), width=1)
    coverage = artifact["source_coverage"]["state"]
    label = "coverage: " + coverage
    draw.rectangle((8, 8, 8 + max(150, len(label) * 8), 28), fill=(0, 0, 0, 190))
    draw.text((12, 12), label, fill=(255, 255, 255, 255))
    output = OUTPUT / ("qa_terrain_" + map_name + ".png")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(base, overlay).save(output)
    print("%s: %s coverage=%s blocked=%d source_spacing=%.3fm" %
          (map_name, output, coverage,
           int((artifact["costs"] < 0).sum()),
           float(json.loads((directory / "terrain" / "sidecar.json").read_text(
               encoding="ascii"))["grid"]["source_spacing_m"])) )


def main():
    for name in (sys.argv[1:] or ["asad_khal", "adak", "muttrah_city_2"]):
        render(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())