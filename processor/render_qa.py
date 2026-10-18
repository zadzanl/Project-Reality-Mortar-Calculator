#!/usr/bin/env python3
"""Unified QA renderer for terrain movement classes and extracted obstruction geometry.

ROLE: Maintainer-only diagnostics CLI tool. End users never run this script.
INPUTS:
    - processed_maps/<map>/minimap.png (base map texture)
    - processed_maps/<map>/terrain/ (cost grids from build_terrain_cost.py)
    - processed_maps/<map>/obstructions.json (road & static geometry)
OUTPUTS:
    - openspec/.../qa_terrain_<map>.png (terrain classes and road overlay)
    - openspec/.../qa_obstructions_<map>.png (obstruction geometry overlay)
HOW TO RUN:
    python processor/render_qa.py asad_khal --terrain
    python processor/render_qa.py asad_khal --obstructions
    python processor/render_qa.py asad_khal --all
DID IT WORK CHECK:
    Prints output PNG paths and saves rendered overlays.
"""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

from terrain_artifact import load_terrain_artifact

ROOT = Path(__file__).resolve().parent.parent

# Output directories for QA artifacts
OUTPUT_TERRAIN = (ROOT / "openspec" / "changes" / "add-terrain-traversability-model" /
                  "artifacts" / "qa_terrain_images")
OUTPUT_OBSTRUCTIONS = (ROOT / "openspec" / "changes" / "add-opening-flow-simulator" /
                      "artifacts" / "qa_obstruction_images")

# Compatibility alias for test_terrain_cost.py
OUTPUT = OUTPUT_TERRAIN

# Color palettes
COLORS_TERRAIN = {
    0: (160, 160, 160, 180),
    1: (80, 200, 80, 120),
    2: (220, 200, 50, 150),
    3: (255, 140, 20, 170),
    4: (220, 20, 20, 190),
    5: (30, 100, 220, 180),
    6: (80, 160, 240, 150),
}
# Compatibility alias for test_terrain_cost.py
COLORS = COLORS_TERRAIN

COLORS_OBSTRUCTIONS = {
    "road": (230, 30, 30, 210),
    "building": (0, 110, 255, 230),
    "wall": (0, 170, 255, 230),
    "fence": (40, 220, 255, 230),
    "container": (40, 80, 220, 230),
    "unclassified": (255, 170, 0, 190),
    "vegetation": (0, 220, 70, 150),
}

DEFAULT_TERRAIN_MAPS = ("asad_khal", "adak", "muttrah_city_2")
DEFAULT_OBSTRUCTION_MAPS = ("asad_khal", "fools_road", "muttrah_city_2", "belyaevo", "adak")


def _point(value, map_size, width):
    return int(round(float(value) / map_size * (width - 1)))


def render_terrain(map_name, profile="infantry"):
    """Render deterministic terrain classes, roads, water, and coverage warnings."""
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
            color = COLORS_TERRAIN[int(artifact["classes"][row, col])]
            box = (int(col * cell_w), int(row * cell_h),
                   int((col + 1) * cell_w), int((row + 1) * cell_h))
            draw.rectangle(box, fill=color)
            if artifact["road_mask"][row, col]:
                draw.rectangle(box, outline=(255, 255, 255, 220), width=1)
    coverage = artifact["source_coverage"]["state"]
    label = "coverage: " + coverage
    draw.rectangle((8, 8, 8 + max(150, len(label) * 8), 28), fill=(0, 0, 0, 190))
    draw.text((12, 12), label, fill=(255, 255, 255, 255))
    out_dir = OUTPUT
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / ("qa_terrain_" + map_name + ".png")
    Image.alpha_composite(base, overlay).save(output)
    sidecar_data = json.loads((directory / "terrain" / "sidecar.json").read_text(encoding="ascii"))
    source_spacing = float(sidecar_data["grid"]["source_spacing_m"])
    print("%s: %s coverage=%s blocked=%d source_spacing=%.3fm" %
          (map_name, output, coverage,
           int((artifact["costs"] < 0).sum()),
           source_spacing))
    return output


def render_obstructions(map_name):
    """Render minimap and extracted obstruction geometry (roads, statics, vegetation)."""
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
            points = [(_point(x, map_size, width), _point(y, map_size, height)) for x, y in triangle]
            draw.line(points + [points[0]], fill=COLORS_OBSTRUCTIONS["road"], width=max(1, width // 1500))

    radius = max(1, width // 700)
    for item in data["statics"]:
        color = COLORS_OBSTRUCTIONS.get(item["class"], COLORS_OBSTRUCTIONS["unclassified"])
        x = _point(item["x"], map_size, width)
        y = _point(item["y"], map_size, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    plant_radius = max(1, width // 1200)
    for item in data["vegetation"]:
        x = _point(item["x"], map_size, width)
        y = _point(item["y"], map_size, height)
        draw.ellipse((x - plant_radius, y - plant_radius, x + plant_radius, y + plant_radius),
                     fill=COLORS_OBSTRUCTIONS["vegetation"])

    result = Image.alpha_composite(base, overlay)
    output = OUTPUT_OBSTRUCTIONS / ("qa_obstructions_" + map_name + ".png")
    OUTPUT_OBSTRUCTIONS.mkdir(parents=True, exist_ok=True)
    result.save(output)
    all_points = [(item["x"], item["y"]) for item in data["statics"]]
    if all_points:
        span = (min(x for x, _ in all_points), max(x for x, _ in all_points),
                min(y for _, y in all_points), max(y for _, y in all_points))
    else:
        span = None
    print("%s: %s counts=%s static_span=%s" % (map_name, output, data["counts"], span))
    return output


# Primary compatibility function alias for test_terrain_cost.py
def render(map_name, profile="infantry"):
    """Compatibility wrapper that defaults to rendering terrain QA."""
    return render_terrain(map_name, profile=profile)


def main():
    parser = argparse.ArgumentParser(description="Render QA overlays for terrain and obstructions.")
    parser.add_argument("maps", nargs="*", help="Map names to render")
    parser.add_argument("--terrain", action="store_true", help="Render terrain class overlays")
    parser.add_argument("--obstructions", action="store_true", help="Render obstruction overlays")
    parser.add_argument("--all", action="store_true", help="Render both terrain and obstruction overlays")
    parser.add_argument("--profile", default="infantry", help="Terrain profile (default: infantry)")
    args = parser.parse_args()

    do_terrain = args.terrain or args.all
    do_obstructions = args.obstructions or args.all
    if not do_terrain and not do_obstructions:
        do_terrain = True
        do_obstructions = True

    maps = args.maps
    if not maps:
        if do_terrain and not do_obstructions:
            maps = list(DEFAULT_TERRAIN_MAPS)
        elif do_obstructions and not do_terrain:
            maps = list(DEFAULT_OBSTRUCTION_MAPS)
        else:
            maps = sorted(set(DEFAULT_TERRAIN_MAPS) | set(DEFAULT_OBSTRUCTION_MAPS))

    for map_name in maps:
        if do_terrain:
            try:
                render_terrain(map_name, profile=args.profile)
            except Exception as e:
                print(f"Error rendering terrain for {map_name}: {e}")
        if do_obstructions:
            try:
                render_obstructions(map_name)
            except Exception as e:
                print(f"Error rendering obstructions for {map_name}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
