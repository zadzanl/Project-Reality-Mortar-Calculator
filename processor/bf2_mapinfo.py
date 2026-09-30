"""Read authoritative world dimensions from a BF2 server.zip.

The primary heightmap uses one sample at each world edge, so its horizontal
spacing is ``map_size / (resolution - 1)``. The primary Y scale is meters per
16-bit height unit; multiplying it by 65535 gives the maximum elevation used
by the repository height sampler.
"""
import re
import zipfile
from pathlib import Path

NUMBER = r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?"
SIZE_RE = re.compile(r"heightmapcluster\.setheightmapsize\s+(\d+)", re.I)
PRIMARY_RE = re.compile(r"rem\s+---\s*primary\s*---(.*?)(?=rem\s+---|\Z)", re.I | re.S)
PRIMARY_SIZE_RE = re.compile(r"heightmap\.setsize\s+(\d+)\s+(\d+)", re.I)
SCALE_RE = re.compile(r"heightmap\.setscale\s+(%s)/(%s)/(%s)" % (NUMBER, NUMBER, NUMBER), re.I)
SEA_RE = re.compile(r"heightmapcluster\.setseawaterlevel\s+(%s)" % NUMBER, re.I)


def _read_heightdata(server_zip):
    with zipfile.ZipFile(server_zip) as archive:
        name = next((item for item in archive.namelist()
                     if item.replace("\\", "/").lower().endswith("heightdata.con")), None)
        return archive.read(name).decode("utf-8", errors="replace") if name else ""


def parse_heightdata(text):
    """Return map_size, height_scale, resolution, and sea_level_m if present."""
    result = {"map_size": None, "height_scale": None,
              "heightmap_resolution": None, "sea_level_m": None}
    match = SIZE_RE.search(text or "")
    if match:
        result["map_size"] = int(match.group(1))
    primary = PRIMARY_RE.search(text or "")
    primary_text = primary.group(1) if primary else text or ""
    match = PRIMARY_SIZE_RE.search(primary_text)
    if match and match.group(1) == match.group(2):
        result["heightmap_resolution"] = int(match.group(1))
    match = SCALE_RE.search(primary_text)
    if match:
        result["height_scale"] = float(match.group(2)) * 65535.0
    match = SEA_RE.search(text or "")
    if match:
        result["sea_level_m"] = float(match.group(1))
    return result


def read_mapinfo(server_zip):
    """Read authoritative map information from a server.zip path."""
    return parse_heightdata(_read_heightdata(Path(server_zip)))