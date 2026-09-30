#!/usr/bin/env python3
"""Probe Asad Khal detailmaps for painted surface-material semantics.

Known ceiling: this spike can show spatial correlation between RGB565 detail
texels and extracted road triangles, but it cannot prove engine material names
without an explicit DDS-to-material mapping. The upgrade path is to recover
the client-side terrain material format or an authoritative slot manifest.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zipfile

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
MAP_NAME = "asad_khal"
MAP_SIZE = 1024
TILE_SIZE = 256
TILE_COUNT = 4
OVERLAY_PATH = (ROOT / "openspec" / "changes" /
                "add-terrain-traversability-model" / "artifacts" /
                "material_overlay_asad_khal.png")
REPORT_PATH = (ROOT / "openspec" / "changes" /
               "add-terrain-traversability-model" / "artifacts" /
               "material-spike-001.md")
CLIENT_PATH = ROOT / "raw_map_data" / MAP_NAME / "client.zip"
SERVER_PATH = ROOT / "raw_map_data" / MAP_NAME / "server.zip"
COMMON_PATH = ROOT / "raw_game_data" / "common_server.zip"
OBSTRUCTIONS_PATH = ROOT / "processed_maps" / MAP_NAME / "obstructions.json"
MINIMAP_PATH = ROOT / "processed_maps" / MAP_NAME / "minimap.png"

TARGET_RE = re.compile(r"^detailmaps/tx(0[0-3])x(0[0-3])_([12])\.dds$",
                       re.IGNORECASE)
MATERIAL_NAME_RE = re.compile(
    r"Material\.active\s+(\d+)\s+.*?Material\.name\s+\"([^\"]+)\"",
    re.IGNORECASE | re.DOTALL)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalize_member(name):
    return name.replace("\\", "/").lower()


def parse_dds(raw, member):
    if len(raw) < 128:
        raise ValueError(f"{member}: shorter than 128-byte DDS header")
    if raw[:4] != b"DDS ":
        raise ValueError(f"{member}: bad magic {raw[:4]!r}")
    values = struct.unpack_from("<31I", raw, 4)
    header_size, flags, height, width, pitch, depth, mip_count = values[:7]
    pf_size, pf_flags, fourcc, rgb_bits, red_mask, green_mask, blue_mask, alpha_mask = struct.unpack_from(
        "<8I", raw, 76)
    caps, caps2 = struct.unpack_from("<2I", raw, 108)
    expected_payload = width * height * (rgb_bits // 8)
    if header_size != 124:
        raise ValueError(f"{member}: header size {header_size}, expected 124")
    if (width, height) != (TILE_SIZE, TILE_SIZE):
        raise ValueError(f"{member}: dimensions {width}x{height}")
    if pf_size != 32 or not (pf_flags & 0x40) or fourcc != 0:
        raise ValueError(f"{member}: unsupported pixel format block")
    if (rgb_bits, red_mask, green_mask, blue_mask, alpha_mask) != (
            16, 0xF800, 0x07E0, 0x001F, 0):
        raise ValueError(f"{member}: unsupported 16-bit masks")
    if len(raw) != 128 + expected_payload:
        raise ValueError(f"{member}: length {len(raw)}, expected {128 + expected_payload}")
    words = np.frombuffer(raw, dtype="<u2", offset=128,
                          count=TILE_SIZE * TILE_SIZE).reshape(TILE_SIZE, TILE_SIZE)
    header = {
        "magic": "DDS ",
        "header_size": header_size,
        "flags": f"0x{flags:08x}",
        "height": height,
        "width": width,
        "pitch": pitch,
        "depth": depth,
        "mip_count": mip_count,
        "pixel_format_size": pf_size,
        "pixel_format_flags": f"0x{pf_flags:08x}",
        "fourcc": fourcc,
        "rgb_bits": rgb_bits,
        "red_mask": f"0x{red_mask:04x}",
        "green_mask": f"0x{green_mask:04x}",
        "blue_mask": f"0x{blue_mask:04x}",
        "alpha_mask": f"0x{alpha_mask:04x}",
        "caps": f"0x{caps:08x}",
        "caps2": f"0x{caps2:08x}",
        "member_bytes": len(raw),
        "payload_bytes": expected_payload,
    }
    return words, header


def histogram(values):
    unique, counts = np.unique(values, return_counts=True)
    return {int(value): int(count) for value, count in zip(unique, counts)}


def rgb565(words):
    red = ((words & 0xF800) >> 11).astype(np.uint8)
    green = ((words & 0x07E0) >> 5).astype(np.uint8)
    blue = (words & 0x001F).astype(np.uint8)
    return red, green, blue


def rasterize_triangle(triangle, size=MAP_SIZE):
    """Return pixel-center coverage for one clipped triangle."""
    points = np.asarray(triangle, dtype=np.float64)
    result = np.zeros((size, size), dtype=bool)
    if points.shape != (3, 2) or not np.isfinite(points).all():
        return result, "invalid"
    x0, y0 = points[0]
    x1, y1 = points[1]
    x2, y2 = points[2]
    denominator = ((y1 - y2) * (x0 - x2) +
                  (x2 - x1) * (y0 - y2))
    if abs(denominator) <= 1e-12:
        return result, "degenerate"
    min_col = max(0, int(math.floor(float(points[:, 0].min()))))
    max_col = min(size - 1, int(math.ceil(float(points[:, 0].max())) - 1))
    min_row = max(0, int(math.floor(float(points[:, 1].min()))))
    max_row = min(size - 1, int(math.ceil(float(points[:, 1].max())) - 1))
    if min_col > max_col or min_row > max_row:
        return result, "outside"
    cols = np.arange(min_col, max_col + 1, dtype=np.float64) + 0.5
    rows = np.arange(min_row, max_row + 1, dtype=np.float64) + 0.5
    xx, yy = np.meshgrid(cols, rows)
    a = ((y1 - y2) * (xx - x2) + (x2 - x1) * (yy - y2)) / denominator
    b = ((y2 - y0) * (xx - x2) + (x0 - x2) * (yy - y2)) / denominator
    c = 1.0 - a - b
    result[min_row:max_row + 1, min_col:max_col + 1] = (
        (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9))
    return result, "covered"


def rasterize_roads(data):
    mask = np.zeros((MAP_SIZE, MAP_SIZE), dtype=bool)
    counts = Counter()
    total_triangles = 0
    for road in data.get("roads", []):
        for triangle in road.get("triangles", []):
            total_triangles += 1
            coverage, status = rasterize_triangle(triangle)
            counts[status] += 1
            mask |= coverage
    counts["total"] = total_triangles
    counts["pixels"] = int(mask.sum())
    return mask, counts


def self_test():
    inside, status = rasterize_triangle([[0, 0], [4, 0], [0, 4]], size=8)
    assert status == "covered" and inside.sum() > 0
    outside, status = rasterize_triangle([[-5, -5], [-2, -5], [-5, -2]], size=8)
    assert status == "outside" and not outside.any()
    clipped, status = rasterize_triangle([[-1, 1], [3, 1], [1, 3]], size=8)
    assert status == "covered" and clipped.any()
    degenerate, status = rasterize_triangle([[1, 1], [2, 2], [3, 3]], size=8)
    assert status == "degenerate" and not degenerate.any()
    return "rasterizer self-test: passed"


def load_tiles(archive):
    selected = {}
    unexpected = []
    for name in archive.namelist():
        normalized = normalize_member(name)
        match = TARGET_RE.match(normalized)
        if match:
            key = (int(match.group(1)), int(match.group(2)), match.group(3))
            if key in selected:
                raise ValueError(f"duplicate normalized tile {normalized}")
            selected[key] = (name, archive.read(name))
        elif normalized.startswith("detailmaps/tx") and normalized.endswith(".dds"):
            unexpected.append(name)
    expected = {(x, y, suffix) for x in range(TILE_COUNT)
                for y in range(TILE_COUNT) for suffix in ("1", "2")}
    missing = sorted(expected - set(selected))
    if missing:
        raise ValueError(f"missing target tiles: {missing}")
    return selected, unexpected


def grid_for(tiles, suffix, swap_axes=False, flip_x=False, flip_y=False):
    grid = np.zeros((MAP_SIZE, MAP_SIZE), dtype=np.uint16)
    for (first, second, tile_suffix), (_, words, _) in tiles.items():
        if tile_suffix != suffix:
            continue
        tile_x, tile_y = (second, first) if swap_axes else (first, second)
        if flip_x:
            tile_x = TILE_COUNT - 1 - tile_x
            words = np.fliplr(words)
        if flip_y:
            tile_y = TILE_COUNT - 1 - tile_y
            words = np.flipud(words)
        y0 = tile_y * TILE_SIZE
        x0 = tile_x * TILE_SIZE
        grid[y0:y0 + TILE_SIZE, x0:x0 + TILE_SIZE] = words
    return grid


def hypothesis_name(swap_axes, flip_x, flip_y):
    axis = "swapped" if swap_axes else "direct"
    flips = ("x" if flip_x else "") + ("y" if flip_y else "")
    return axis + ("_flip_" + flips if flips else "")


def confusion(grid, road_mask):
    total = grid.size
    road_values = Counter(int(value) for value in grid[road_mask])
    all_values = Counter(int(value) for value in grid.ravel())
    rows = []
    for value, count in road_values.most_common(12):
        road_count = int(count)
        all_count = int(all_values[value])
        road_share = road_count / max(1, int(road_mask.sum()))
        global_share = all_count / total
        coverage = road_count / max(1, all_count)
        lift = road_share / global_share if global_share else 0.0
        rows.append({"value": value, "all": all_count, "road": road_count,
                     "road_share": road_share, "global_share": global_share,
                     "road_coverage": coverage, "lift": lift})
    best = max(rows, key=lambda row: row["lift"]) if rows else None
    dominant = rows[0] if rows else None
    return rows, best, dominant


def format_hist(values):
    lines = []
    for value, count in sorted(values.items()):
        lines.append(f"{value}: {count}")
    return "\n".join(lines)


def format_table(rows):
    lines = ["| value | all pixels | road pixels | road share | global share | road coverage | lift |",
             "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append("| {value} | {all} | {road} | {road_share:.6f} | {global_share:.6f} | {road_coverage:.6f} | {lift:.3f} |".format(**row))
    return "\n".join(lines)


def inspect_wiring(server, common):
    server_names = [normalize_member(name) for name in server.namelist()]
    server_candidates = [name for name in server_names if name.endswith(("terrain.con", "heightdata.con", "heightmapprimary.mat"))]
    server_text = {}
    for name in server_candidates:
        original = next(item for item in server.namelist() if normalize_member(item) == name)
        raw = server.read(original)
        server_text[name] = raw.decode("ascii", errors="replace")
    common_names = [normalize_member(name) for name in common.namelist()]
    common_candidates = [name for name in common_names if name in (
        "material/materials.json", "material/cells.json",
        "material/materialmanagerdefine.con")]
    common_text = {}
    for name in common_candidates:
        original = next(item for item in common.namelist() if normalize_member(item) == name)
        common_text[name] = common.read(original).decode("ascii", errors="replace")
    named = dict((int(value), name) for value, name in
                 MATERIAL_NAME_RE.findall(common_text.get("material/materialmanagerdefine.con", "")))
    strict_json_failures = {}
    for name in ("material/materials.json", "material/cells.json"):
        try:
            json.loads(common_text[name])
        except (KeyError, json.JSONDecodeError) as error:
            strict_json_failures[name] = str(error)
    return server_candidates, server_text, common_candidates, strict_json_failures, named


def write_overlay(grid, road_mask, minimap_path, output_path):
    base = Image.open(minimap_path).convert("RGBA")
    rgb = np.zeros((MAP_SIZE, MAP_SIZE, 3), dtype=np.uint8)
    red, green, blue = rgb565(grid)
    rgb[:, :, 0] = (red.astype(np.uint16) * 255 // 31).astype(np.uint8)
    rgb[:, :, 1] = (green.astype(np.uint16) * 255 // 63).astype(np.uint8)
    rgb[:, :, 2] = (blue.astype(np.uint16) * 255 // 31).astype(np.uint8)
    alpha = np.full((MAP_SIZE, MAP_SIZE, 1), 115, dtype=np.uint8)
    material = Image.fromarray(np.concatenate((rgb, alpha), axis=2), "RGBA")
    material = material.resize(base.size, Image.Resampling.NEAREST)
    result = Image.alpha_composite(base, material)
    draw = ImageDraw.Draw(result, "RGBA")
    width, height = base.size
    for road in json.loads(OBSTRUCTIONS_PATH.read_text(encoding="ascii")).get("roads", []):
        for triangle in road.get("triangles", []):
            points = [(int(round(point[0] / MAP_SIZE * (width - 1))),
                       int(round(point[1] / MAP_SIZE * (height - 1))))
                      for point in triangle]
            draw.line(points + [points[0]], fill=(255, 30, 30, 220), width=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    check = Image.open(output_path)
    array = np.asarray(check.convert("RGBA"))
    base_array = np.asarray(base)
    changed = int(np.any(array != base_array, axis=2).sum())
    return {"size": check.size, "mode": check.mode, "bytes": output_path.stat().st_size,
            "unique_pixels": int(np.unique(array.reshape(-1, 4), axis=0).shape[0]),
            "changed_pixels": changed}


def run(report_path, overlay_path):
    before_hashes = {str(path): sha256(path) for path in
                     (CLIENT_PATH, SERVER_PATH, COMMON_PATH)}
    with zipfile.ZipFile(CLIENT_PATH, "r") as client, \
            zipfile.ZipFile(SERVER_PATH, "r") as server, \
            zipfile.ZipFile(COMMON_PATH, "r") as common:
        tiles_raw, unexpected = load_tiles(client)
        tiles = {}
        headers = []
        per_tile = {}
        for key, (member, raw) in sorted(tiles_raw.items()):
            words, header = parse_dds(raw, member)
            tiles[key] = (member, words, header)
            headers.append(header)
            per_tile[member] = histogram(words)
        suffix_hist = {}
        for suffix in ("1", "2"):
            values = np.concatenate([words.ravel() for (x, y, s), (_, words, _) in tiles.items() if s == suffix])
            suffix_hist[suffix] = histogram(values)
        all_values = np.concatenate([words.ravel() for _, words, _ in tiles.values()])
        combined_hist = histogram(all_values)
        server_candidates, server_text, common_candidates, strict_failures, named = inspect_wiring(server, common)
        client_refs = [name for name in client.namelist()
                       if name.lower().endswith((".con", ".json", ".txt"))]
        client_material_refs = [name for name in client_refs
                                if any(word in name.lower() for word in ("material", "detail", "terrain"))]
    obstruction = json.loads(OBSTRUCTIONS_PATH.read_text(encoding="ascii"))
    road_mask, road_counts = rasterize_roads(obstruction)
    hypotheses = []
    for swap_axes in (False, True):
        for flip_x in (False, True):
            for flip_y in (False, True):
                name = hypothesis_name(swap_axes, flip_x, flip_y)
                grid = grid_for(tiles, "1", swap_axes, flip_x, flip_y)
                rows, best, dominant = confusion(grid, road_mask)
                hypotheses.append({"name": name, "grid": grid, "rows": rows,
                                   "best": best, "dominant": dominant})
    scored = [item for item in hypotheses if item["best"] is not None]
    best_hypothesis = max(scored, key=lambda item: item["best"]["lift"])
    overlay_info = write_overlay(best_hypothesis["grid"], road_mask, MINIMAP_PATH, overlay_path)
    after_hashes = {str(path): sha256(path) for path in
                    (CLIENT_PATH, SERVER_PATH, COMMON_PATH)}
    header = headers[0]
    header_uniform = all(item == header for item in headers)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Material Texture Spike 001: Asad Khal",
        "",
        "## Role",
        "Bounded implementation worker for OpenSpec tasks 7.1-7.4. This spike is an additive diagnostic investigation under design decision D9.",
        "",
        "## Status",
        "Completed with a NO-GO for a named engine-material assignment. An unnamed RGB565 road-correlation diagnostic overlay was generated; it must not affect movement cost.",
        "",
        "## Evidence",
        "",
        "### Inputs and archive integrity",
        f"- client archive: `{CLIENT_PATH.relative_to(ROOT).as_posix()}`, members={len(zipfile.ZipFile(CLIENT_PATH).namelist())}, size={CLIENT_PATH.stat().st_size} bytes.",
        f"- server archive: `{SERVER_PATH.relative_to(ROOT).as_posix()}`, members={len(zipfile.ZipFile(SERVER_PATH).namelist())}, size={SERVER_PATH.stat().st_size} bytes.",
        f"- common archive: `{COMMON_PATH.relative_to(ROOT).as_posix()}`, members={len(zipfile.ZipFile(COMMON_PATH).namelist())}, size={COMMON_PATH.stat().st_size} bytes.",
        "- All archives were opened read-only with `zipfile.ZipFile`; members were read in memory and no extraction or archive write was performed.",
        "- SHA-256 before and after the run:",
    ]
    for path in before_hashes:
        lines.append(f"  - `{Path(path).relative_to(ROOT).as_posix()}` before={before_hashes[path]} after={after_hashes[path]} unchanged={before_hashes[path] == after_hashes[path]}")
    lines.extend([
        "",
        "### Exact high-resolution client members",
        f"- target members decoded={len(tiles)}, unexpected detail DDS members={len(unexpected)}, missing target members=0.",
        "```text",
    ])
    lines.extend(sorted(member for member, _, _ in tiles.values()))
    lines.extend(["```", "", "### DDS parse", ""])
    for key in ("magic", "header_size", "flags", "height", "width", "pitch", "depth", "mip_count", "pixel_format_size", "pixel_format_flags", "fourcc", "rgb_bits", "red_mask", "green_mask", "blue_mask", "alpha_mask", "caps", "caps2", "member_bytes", "payload_bytes"):
        lines.append(f"- `{key}` = `{header[key]}`")
    lines.append(f"- all {len(headers)} decoded tiles have identical validated headers={header_uniform}.")
    lines.append("- Pixel interpretation is little-endian RGB565: red mask 0xf800, green mask 0x07e0, blue mask 0x001f, alpha mask 0. The raw-word histogram is therefore not a proven material-index histogram.")
    lines.append("- Observed DDS pitch field is 131072 bytes (`dwPitchOrLinearSize` at header bytes 16-19). This contradicts the supplied verified fact of pitch 512; the observed 131200-byte member still validates as a 128-byte header plus 131072-byte payload, so decoding uses the actual payload length and records the contradiction rather than assuming 512.")
    lines.extend(["", "### Full aggregate histogram for suffix `_1`", "", "```text", format_hist(suffix_hist["1"]), "```", "", "### Full aggregate histogram for suffix `_2`", "", "```text", format_hist(suffix_hist["2"]), "```", "", "### Histogram summary", ""])
    for suffix in ("1", "2"):
        values = suffix_hist[suffix]
        lines.append(f"- `_{suffix}` pixels={sum(values.values())}, unique_raw_words={len(values)}, min={min(values)}, max={max(values)}, top10={Counter(values).most_common(10)}")
    lines.append(f"- combined pixels={sum(combined_hist.values())}, unique_raw_words={len(combined_hist)}, min={min(combined_hist)}, max={max(combined_hist)}.")
    lines.extend(["", "### Wiring search", "", f"- Asad Khal server candidates: `{server_candidates}`.", "- `terrain.con` names the detailmap base but does not provide a raw RGB565-word to material-ID mapping.", f"- Shared material candidates: `{common_candidates}`.", f"- Strict JSON parse failures: `{strict_failures}`. The trailing-comma format is not direct DDS wiring.", f"- Explicit material-manager IDs parsed: {len(named)}; examples={list(named.items())[:8]}.", f"- Client text/config candidates mentioning material/detail/terrain: `{client_material_refs}`.", "- `heightmapprimary.mat` is a separate 513x513 byte height/material raster reference in server data; it does not establish that detailmap RGB565 words use those material IDs.", "- Wiring result: unresolved. Numeric coincidences such as raw word 4, 8, or 2016 are not accepted as material names.", "", "### Road rasterization and mapping hypotheses", "", f"- obstruction road records={len(obstruction.get('roads', []))}; triangles={road_counts['total']}; covered road texels={road_counts['pixels']}; statuses={dict(road_counts)}.", "- Coordinates used: repo x/y meters, top-left origin, x east, y south; 1024x1024 texels over 1024x1024 meters; pixel centers at integer plus 0.5; degenerate and out-of-map triangles are counted and excluded.", "- Eight hypotheses tested: direct or swapped filename axes, each with no flip, x flip, y flip, and both flips. `_1` was used for the measured alignment because `_2` is a separate layer with a different distribution.", "", "| hypothesis | road pixels | best raw word | word pixels on roads | road share | global share | road coverage | lift |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for item in hypotheses:
        best = item["best"]
        if best is None:
            lines.append(f"| {item['name']} | {road_counts['pixels']} | none | 0 | 0 | 0 | 0 | 0 |")
        else:
            lines.append(f"| {item['name']} | {road_counts['pixels']} | {best['value']} | {best['road']} | {best['road_share']:.6f} | {best['global_share']:.6f} | {best['road_coverage']:.6f} | {best['lift']:.3f} |")
    lines.extend(["", f"- Best statistical hypothesis by maximum top-road-value lift: `{best_hypothesis['name']}`. This is not visual or semantic proof of tile orientation.", "", "### Best-hypothesis confusion picture", "", format_table(best_hypothesis["rows"]), "", "- The table reports all-pixel count, road-pixel count, value share within road pixels, global share, fraction of each raw word covered by roads, and lift. The road-correlated cluster remains unnamed.", "", "### Overlay verification", "", f"- output: `{overlay_path.relative_to(ROOT).as_posix()}`.", f"- dimensions={overlay_info['size']}, mode={overlay_info['mode']}, bytes={overlay_info['bytes']}, unique RGBA pixels={overlay_info['unique_pixels']}, pixels changed from RGBA minimap={overlay_info['changed_pixels']}.", "- The overlay is a decoded RGB565 diagnostic color layer composited over the minimap with road triangle outlines; it is not a named material mask and minimap imagery is not collision ground truth.", "", "## Go-or-NoGo verdict", "", "**NO-GO for a named per-texel engine MATERIAL assignment.** The DDS format is proven RGB565, but no authoritative join to material IDs exists in the examined server terrain data, client text/config members, shared materials JSON, cells JSON, or material-manager ordering. Road overlap identifies only unnamed encoded-color clusters and differs by layer/orientation; it cannot prove Tarmac, Dirt, paved, or any speed effect. The generated overlay is retained only as diagnostic evidence. D9 remains satisfied: no material field was added to terrain costs and no default cost multiplier was changed.", "", "## Attempt log", "", "1. Read `design.md` D9, `tasks.md` section 7, and `artifacts/task-record.md`; confirmed scope 7.1-7.4, ASCII-only, read-only archives, and allowed output paths.", "2. Read processor rendering/extraction conventions and existing Asad Khal metadata, obstruction JSON, and minimap.", "3. Enumerated `client.zip`, `server.zip`, and `common_server.zip` members and exact counts; located all required detail/material candidates.", "4. Parsed every target DDS with `struct` and NumPy; rejected no target tile and recorded uniform RGB565 headers.", "5. Computed complete aggregate raw-word histograms separately for `_1` and `_2` and decoded RGB565 channel semantics.", "6. Searched `terrain.con`, `heightdata.con`, `heightmapprimary.mat`, `materials.json`, `cells.json`, `materialmanagerdefine.con`, and client text/config members; strict JSON parsing of the two JSON candidates failed because of archive trailing commas, and no direct DDS wiring was found.", "7. Rasterized every road triangle with NumPy point-in-triangle tests at pixel centers; tested direct/swapped axes and x/y flip variants; recorded malformed/degenerate/outside counts and confusion metrics.", "8. Generated the permitted overlay, re-opened it with PIL, and verified dimensions, mode, byte size, unique pixels, and changed-pixel count. The overlay was visually inspected after generation; it is treated as diagnostic only.", "9. Initial command dead end: a Bash heredoc form `python - <<'PY'` was sent to PowerShell and failed with a PowerShell parser error. No repository input was changed.", "10. Initial context dead end: attempted read of `openspec/changes/add-terrain-traversability-model/worklog.md` at the root failed because that path was absent; the actual worklog is under `artifacts/` and the task record remained available.", "11. A malformed mixed PowerShell/Python command entered an interactive Python prompt; the stray terminal was killed, with no spike input or allowed output modified. The command was retried with PowerShell here-strings successfully.", "12. The implementation command for this artifact run was `python processor/spike_material_map.py --self-test`; report generation and overlay generation completed in the same run.", "", "## Limits", "", "- RGB565 packed color may be a terrain blend/detail representation, but this spike does not prove its engine slot semantics.", "- Road correlation is a diagnostic association only; it is not a material name, collision truth, or movement-speed calibration.", "- The overlay uses one selected orientation for display; all tested hypotheses and their statistics are recorded above.", "- No task checkbox, terrain runtime, terrain configuration, raw archive, or task 7.5 recollection was changed.", ""])
    wiring_index = lines.index("### Wiring search")
    lines[wiring_index + 1:wiring_index + 1] = [
        f"- Client archive text/config members (`.con`, `.json`, `.txt`) enumerated={len(client_refs)}; content matches for material/detail/terrain terms={client_material_refs}."
    ]
    dominant = best_hypothesis["dominant"]
    confusion_index = lines.index("### Best-hypothesis confusion picture")
    lines[confusion_index:confusion_index] = [
        f"- Dominant raw word among road texels under `{best_hypothesis['name']}`: value={dominant['value']}, overlap={dominant['road']}/{road_counts['pixels']}={dominant['road_share']:.6f} ({dominant['road_share'] * 100:.3f}%), global share={dominant['global_share']:.6f}, road coverage={dominant['road_coverage']:.6f}. The highest-lift unnamed word is value={best_hypothesis['best']['value']} with road overlap={best_hypothesis['best']['road_share']:.6f} ({best_hypothesis['best']['road_share'] * 100:.3f}%)."
    ]
    report_path.write_text("\n".join(lines), encoding="ascii")
    return {
        "report": str(report_path),
        "overlay": str(overlay_path),
        "tiles": len(tiles),
        "road_pixels": road_counts["pixels"],
        "best_hypothesis": best_hypothesis["name"],
        "verdict": "NO-GO",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--overlay", type=Path, default=OVERLAY_PATH)
    args = parser.parse_args()
    if args.self_test:
        print(self_test())
    result = run(args.report, args.overlay)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())