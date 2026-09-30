#!/usr/bin/env python3
"""Extract road triangles, static obstructions, and vegetation placements."""
import json
import math
import re
import sys
import zipfile
from pathlib import Path

from bf2_road_mesh import decode_compiled_road_mesh, road_vertices_world

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_map_data"
OUT = ROOT / "processed_maps"
EXCLUDED = {"the_falklands"}
CLASS_RULES = (
    ("building", ("house", "building", "shed", "hut", "bunker", "tower", "mosque")),
    ("wall", ("wall", "barrier", "sandbag", "hesco")),
    ("fence", ("fence", "hedgerow", "net", "wire")),
    ("container", ("container", "crate", "dumpster")),
    ("vegetation", ("tree", "olive", "palm", "bush", "vegetation", "vegitation", "grass")),
)
CREATE_RE = re.compile(r"^\s*object\.create\s+(\S+)", re.I)
PROP_RE = re.compile(r"^\s*object\.(\S+)\s*(.*)", re.I)
FLOATS_RE = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?")


def parse_slash(value):
    try:
        values = [float(part) for part in value.strip().split("/")]
        return values if len(values) == 3 else None
    except ValueError:
        return None


def parse_object_blocks(text):
    blocks = []
    current = None
    for line in text.splitlines():
        match = CREATE_RE.match(line)
        if match:
            if current is not None:
                blocks.append(current)
            current = {"template": match.group(1), "props": {}}
            continue
        if current is not None:
            match = PROP_RE.match(line)
            if match and match.group(1).lower() != "create":
                current["props"].setdefault(match.group(1).lower(), []).append(match.group(2).strip())
    if current is not None:
        blocks.append(current)
    return blocks


def classify(template):
    name = template.lower()
    for kind, words in CLASS_RULES:
        if any(word in name for word in words):
            return kind
    return "unclassified"


def bf2_to_repo(x, z, map_size):
    return x + map_size / 2.0, map_size / 2.0 - z


def parse_statics(text, map_size):
    result = []
    for block in parse_object_blocks(text):
        position = parse_slash(block["props"].get("absoluteposition", [""])[0])
        if position is None:
            continue
        rotation = 0.0
        raw_rotation = block["props"].get("rotation", [""])[0]
        values = parse_slash(raw_rotation)
        if values is not None:
            rotation = values[1] if len(values) > 1 else values[0]
        else:
            try:
                rotation = float(raw_rotation)
            except ValueError:
                pass
        x, y = bf2_to_repo(position[0], position[2], map_size)
        result.append({"template": block["template"], "class": classify(block["template"]),
                       "x": x, "y": y, "rotation_deg": rotation})
    return result


def parse_vegetation(text, map_size):
    result = []
    for block in parse_object_blocks(text):
        raw = block["props"].get("absolutetransformation", [""])[0]
        groups = re.findall(r"\[([^\]]+)\]", raw)
        if len(groups) < 4:
            continue
        values = FLOATS_RE.findall(groups[3])
        if len(values) < 3:
            continue
        x, y = bf2_to_repo(float(values[0]), float(values[2]), map_size)
        result.append({"template": block["template"], "x": x, "y": y})
    return result


def parse_roads(text, client, map_name, map_size, log):
    roads = []
    for block in parse_object_blocks(text):
        reference = block["props"].get("geometry.loadmesh", [""])[0]
        if not reference:
            continue
        archive_name = "roads/" + reference.replace("\\", "/").rsplit("/", 1)[-1].lower()
        member = next((name for name in client.namelist() if name.replace("\\", "/").lower() == archive_name), None)
        if member is None:
            log(f"  missing mesh: {reference}")
            continue
        try:
            mesh = decode_compiled_road_mesh(client.read(member), member)
            position = parse_slash(block["props"].get("absoluteposition", [""])[0])
            vertices = road_vertices_world(mesh, position)
            triangles = []
            for indices in mesh.triangles:
                triangle = []
                for index in indices:
                    x, y = bf2_to_repo(float(vertices[index, 0]), float(vertices[index, 2]), map_size)
                    triangle.append([x, y])
                triangles.append(triangle)
            roads.append({"name": block["template"], "triangles": triangles})
        except (ValueError, OSError, zipfile.BadZipFile) as error:
            log(f"  mesh error {reference}: {error}")
    return roads


def read_member(archive, suffix):
    matches = [name for name in archive.namelist() if name.replace("\\", "/").lower() == suffix]
    return archive.read(matches[0]).decode("utf-8", errors="replace") if matches else ""


def process_map(map_dir, index, total):
    name = map_dir.name
    print(f"[{index}/{total}] Processing {name}...")
    metadata_path = OUT / name / "metadata.json"
    try:
        map_size = float(json.loads(metadata_path.read_text(encoding="utf-8"))["map_size"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"  error: metadata: {error}")
        return False, 1
    errors = 0
    messages = []
    def log(message):
        nonlocal errors
        errors += 1
        messages.append(message)
        print(message)
    roads, statics, vegetation = [], [], []
    try:
        with zipfile.ZipFile(map_dir / "server.zip") as server:
            road_text = read_member(server, "compiledroads.con")
            static_text = read_member(server, "staticobjects.con")
            growth_text = read_member(server, "overgrowth/overgrowthcollision.con")
            client_path = map_dir / "client.zip"
            if road_text and client_path.exists():
                with zipfile.ZipFile(client_path) as client:
                    roads = parse_roads(road_text, client, name, map_size, log)
            elif road_text:
                log("  missing client.zip; roads omitted")
            if static_text:
                statics = parse_statics(static_text, map_size)
            if growth_text:
                vegetation = parse_vegetation(growth_text, map_size)
    except (OSError, zipfile.BadZipFile) as error:
        log(f"  archive error: {error}")
    classified = sum(item["class"] != "unclassified" for item in statics)
    output = {"map_name": name, "format_version": "1.0", "roads": roads,
              "statics": statics, "vegetation": vegetation,
              "counts": {"roads": len(roads), "road_triangles": sum(len(r["triangles"]) for r in roads),
                         "statics_classified": classified, "statics_unclassified": len(statics) - classified,
                         "vegetation": len(vegetation)}}
    destination = OUT / name / "obstructions.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(f"  roads={len(roads)} statics={len(statics)} classified={classified} vegetation={len(vegetation)} errors={errors}")
    return True, errors


def main():
    maps = sorted(path for path in RAW.iterdir() if path.is_dir() and path.name not in EXCLUDED and (path / "server.zip").exists())
    processed = 0
    errors = 0
    for index, map_dir in enumerate(maps, 1):
        ok, count = process_map(map_dir, index, len(maps))
        processed += int(ok)
        errors += count
    print(f"Summary: {processed}/{len(maps)} maps processed, errors={errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
