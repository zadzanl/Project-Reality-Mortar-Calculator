#!/usr/bin/env python3
"""Compute opening-flow arrival-time fields across layers and vehicle classes.

ROLE: Maintainer-only CLI tool. End users never run this script.
INPUTS:
    - processed_maps/<map>/terrain/ (cost grids from build_terrain_cost.py)
    - processed_maps/<map>/gamelayers.json (control points and spawn positions)
    - processor/movement_params.json (class speed configurations)
    - calculator/static/data/vehicle_speeds.json (vehicle classification)
OUTPUTS:
    - processed_maps/<map>/flow/<mode>_<size>/race_times.json (earliest arrival seconds per flag)
    - processed_maps/<map>/flow/<mode>_<size>/team<1|2>/<class>.bin (uint8 arrival time grid)
    - processed_maps/<map>/flow/<mode>_<size>/team<1|2>/<class>.json (quantization sidecar)
HOW TO RUN:
    python processor/build_flow_fields.py              # Process all maps with inputs
    python processor/build_flow_fields.py asad_khal    # Process one map
    python processor/build_flow_fields.py --workers 4  # Parallel processing across CPU cores
DID IT WORK CHECK:
    Prints 'Finished flow fields for ...' and generates flow/ binary files.
"""
import argparse
import hashlib
import heapq
import json
import math
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from terrain_artifact import load_terrain_artifact

ROOT = Path(__file__).resolve().parent.parent
# Env override exists so tests can point the pipeline at a fixture tree;
# spawned worker processes inherit os.environ, so this works under spawn.
OUT = Path(os.environ.get("PR_FLOW_OUT", str(ROOT / "processed_maps")))
MOVEMENT_PARAMS = Path(__file__).resolve().parent / "movement_params.json"
VEHICLE_SPEEDS = ROOT / "calculator" / "static" / "data" / "vehicle_speeds.json"
EXCLUDED = {"the_falklands"}

UNREACHABLE = -1.0          # float32 field sentinel (matches terrain BLOCKED)
QUANT_UNREACHABLE = 255     # shipped uint8 sentinel
QUANT_CAP_S = 3600.0        # arrival times above this saturate (display window is 10 min)
# Bump for solver/output changes; terrain bytes are hashed separately below.
V2_PIPELINE_VERSION = "v2-4"

# Flow agent class -> terrain artifact profile.
CLASS_PROFILE = {"infantry": "infantry", "vehicles": "wheeled_vehicle"}
V2_CLASS_PROFILE = {
    "car": "car", "truck_wheeled": "truck_wheeled", "tracked": "tracked",
    "boat": None, "helicopter": None,
}
V2_STATUS = {"available", "no_source", "unsupported_data", "unsupported_model",
             "not_computed", "unreachable", "corrupt_artifact"}


# ---------------------------------------------------------------------------
# Movement parameters (pipeline inputs with provenance; design D3)
# ---------------------------------------------------------------------------

def load_infantry_speed(path=MOVEMENT_PARAMS):
    """Sustained infantry speed: sprint/regen cycle average.

    Returns (speed_ms, provenance_string).
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = doc["fields"]
    sprint = fields["infantry_sprint_ms"]
    walk = fields["infantry_walk_ms"]
    duration = fields["sprint_duration_s"]
    regen = fields["stamina_regen_s"]
    speed = (sprint["value"] * duration["value"] + walk["value"] * regen["value"]) \
        / (duration["value"] + regen["value"])
    provenance = (
        "sustained = (sprint*sprint_duration + walk*regen)/(sprint_duration+regen) "
        "from movement_params.json; sprint: %s; walk: %s"
        % (sprint["provenance"], walk["provenance"]))
    return speed, provenance


def load_vehicle_speeds(path=None):
    path = VEHICLE_SPEEDS if path is None else path
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc["vehicles"], doc.get("source", "vehicle_speeds.json")


def load_vehicle_catalog(path=None):
    """Load the complete catalog so v2 cannot silently consume a v1 file."""
    path = VEHICLE_SPEEDS if path is None else path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def product_sources(templates, vehicles):
    """Filter selected spawner templates by positive v2 catalog evidence."""
    selected = {"car": [], "truck_wheeled": [], "tracked": [], "boat": [], "helicopter": []}
    excluded = []
    for template in templates:
        entry = vehicles.get(template)
        product = entry.get("product_id") if entry else None
        if product in selected and entry.get("eligibility") == "eligible":
            speed = entry.get("max_speed_ms")
            if product == "helicopter":
                selected[product].append((template, None))
            elif isinstance(speed, (int, float)) and math.isfinite(speed) and speed > 0:
                selected[product].append((template, float(speed)))
            else:
                excluded.append((template, "unsupported_speed"))
        else:
            excluded.append((template, entry.get("eligibility_reason", "missing_template")
                             if entry else "missing_template"))
    return selected, excluded


def grouped_speed_sources(source_entries):
    """Group same-class sources by exact modeled speed; never average missing data."""
    groups = {}
    for x, y, template, speed in source_entries:
        groups.setdefault(float(speed), []).append((x, y, template))
    return [(speed, groups[speed]) for speed in sorted(groups)]


def v2_source_groups(layer, team, vehicles):
    """Return positively evidenced selected-team sources grouped by class/speed."""
    _, vehicle_sources = layer_team_sources(layer)
    templates = [entry[2] for entry in vehicle_sources[team] if entry[2]]
    selected, excluded = product_sources(templates, vehicles)
    by_template = {template: speed for class_id in selected
                   for template, speed in selected[class_id]}
    groups = {class_id: [] for class_id in V2_CLASS_PROFILE}
    for x, y, template in vehicle_sources[team]:
        speed = by_template.get(template)
        if speed is None:
            continue
        class_id = next(class_id for class_id in selected
                        if any(template == item[0] for item in selected[class_id]))
        groups[class_id].append((x, y, template, speed))
    return {class_id: grouped_speed_sources(entries)
            for class_id, entries in groups.items()}, excluded


def pick_vehicle_speed(templates, vehicles, source):
    """Median speed of the team's spawner templates (earliest-arrival field
    should reflect a typical vehicle, not the single fastest).

    Missing templates fall back to the average of the templates that WERE
    found, per design "Error Handling". Returns (speed_ms, provenance) or
    (None, reason) when nothing usable exists.
    """
    found = []
    missing = []
    for name in templates:
        if name and name in vehicles:
            found.append((name, vehicles[name]["max_speed_ms"]))
        elif name:
            missing.append(name)
    if not found:
        return None, "no spawner template present in vehicle_speeds.json: %s" % missing
    fallback_note = ""
    if missing:
        avg = sum(s for _, s in found) / len(found)
        fallback_note = "; missing templates used found-average %.1f m/s: %s" % (avg, missing)
        found.extend((name, avg) for name in missing)
    speeds = sorted(s for _, s in found)
    median = speeds[len(speeds) // 2] if len(speeds) % 2 else \
        (speeds[len(speeds) // 2 - 1] + speeds[len(speeds) // 2]) / 2.0
    provenance = "median of %d spawner templates from %s%s" % (len(found), source, fallback_note)
    return median, provenance


# ---------------------------------------------------------------------------
# Sources from gamelayers.json (initial deployment only; design D9)
# ---------------------------------------------------------------------------

def layer_team_sources(layer):
    """Assign spawn points and vehicle spawners to teams via linked CP owner.

    A control point's template `team` is its initial owner (0/None = neutral).
    Spawners with an explicit team use it; otherwise they inherit the linked
    control point's initial owner. Neutral-linked sources are skipped.

    Returns (infantry, vehicles): dicts team -> [(x, y)] / team -> [(x, y, template)].
    """
    cp_team = {}
    for cp in layer["control_points"]:
        if cp.get("id") is not None:
            cp_team[cp["id"]] = cp.get("team")

    infantry = {1: [], 2: []}
    for sp in layer["spawn_points"]:
        team = cp_team.get(sp.get("control_point_id"))
        if team in (1, 2) and "x" in sp:
            infantry[team].append((sp["x"], sp["y"]))

    vehicles = {1: [], 2: []}
    for vs in layer["vehicle_spawners"]:
        team = vs.get("team")
        if team not in (1, 2):
            team = cp_team.get(vs.get("control_point_id"))
        if team in (1, 2) and "x" in vs:
            template = vs.get("templates", {}).get(str(team))
            vehicles[team].append((vs["x"], vs["y"], template))
    return infantry, vehicles


def _source_team(spawner, cp_team):
    team = spawner.get("team")
    return team if team in (1, 2) else cp_team


def associate_vehicle_spawners(layer, tolerance_m=150.0):
    """Join spawners to same-layer control points using explicit ID first.

    The nearest-position fallback is deterministic. Ambiguous or unlinked
    records are returned as drops instead of being assigned by guesswork.
    """
    cps = [cp for cp in layer.get("control_points", [])
           if isinstance(cp.get("x"), (int, float)) and isinstance(cp.get("y"), (int, float))]
    by_id = {cp.get("id"): cp for cp in cps if cp.get("id") is not None}
    associated = []
    dropped = []
    for spawner in layer.get("vehicle_spawners", []):
        x, y = spawner.get("x"), spawner.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            dropped.append((spawner.get("name"), "unlinked"))
            continue
        cp = by_id.get(spawner.get("control_point_id"))
        if cp is None:
            candidates = []
            for candidate in cps:
                if candidate.get("layer") is not None and spawner.get("layer") is not None \
                        and candidate.get("layer") != spawner.get("layer"):
                    continue
                distance = math.hypot(x - candidate["x"], y - candidate["y"])
                if distance <= tolerance_m:
                    candidates.append((distance, candidate))
            candidates.sort(key=lambda item: (item[0], str(item[1].get("name"))))
            if not candidates:
                dropped.append((spawner.get("name"), "unlinked"))
                continue
            if len(candidates) > 1 and math.isclose(candidates[0][0], candidates[1][0], abs_tol=0.01):
                dropped.append((spawner.get("name"), "ambiguous_cp_association"))
                continue
            cp = candidates[0][1]
        team = _source_team(spawner, cp.get("team"))
        if team not in (1, 2):
            dropped.append((spawner.get("name"), "unlinked"))
            continue
        associated.append((spawner, cp, team))
    return associated, dropped


def v2_vehicle_sources(layer, team, vehicles, tolerance_m=150.0):
    """Return main-base vehicle sources and provenance drops for one team."""
    associated, drops = associate_vehicle_spawners(layer, tolerance_m)
    selected = []
    for spawner, cp, source_team in associated:
        if source_team != team:
            continue
        # Pre-main-base fixture data has no derived key. Real extracted
        # gamelayers always carry it; accepting the old shape keeps legacy
        # processor fixtures readable without weakening the extracted policy.
        if "main_base" in cp and not cp.get("main_base"):
            drops.append((spawner.get("name"), "not_main_base"))
            continue
        templates = spawner.get("templates", {})
        template = templates.get(str(team)) or templates.get(str(cp.get("team")))
        entry = vehicles.get(template) if template else None
        product = entry.get("product_id") if entry else None
        if not entry or entry.get("eligibility") != "eligible" or product not in V2_CLASS_PROFILE:
            drops.append((spawner.get("name"), "unsupported_template"))
            continue
        speed = entry.get("max_speed_ms")
        if product != "helicopter" and not isinstance(speed, (int, float)):
            drops.append((spawner.get("name"), "unsupported_template"))
            continue
        selected.append({"name": spawner.get("name"), "template": template,
                         "x": spawner["x"], "y": spawner["y"],
                         "product_id": product, "speed": speed,
                         "classification_evidence": entry.get("eligibility_reason"),
                         "source_type": "verified_spawner"})
    return selected, drops


def serialize_dropped_sources(dropped):
    """Convert internal drop tuples to the v2 JSON provenance shape."""
    return [{"name": item[0], "reason": item[1]} for item in dropped]


def solve_helicopter_field(elevation, sources, cruise_ms, climb_rate_ms, cell_size_m, warmup_s=15.0):
    """Solve horizontal helicopter travel with a climb-only elevation penalty.

    Known ceiling: this is a horizontal terrain-following approximation; it
    has no altitude envelope, clearance, wind, landing, or obstacle model.
    """
    elevation = np.asarray(elevation, dtype=np.float32)
    rows, cols = elevation.shape
    arrival = np.full((rows, cols), np.float64("inf"), dtype=np.float64)
    heap = []
    for row, col in sources:
        if 0 <= row < rows and 0 <= col < cols and arrival[row, col] > warmup_s:
            arrival[row, col] = warmup_s
            heapq.heappush(heap, (warmup_s, row, col))
    while heap:
        time_a, row, col = heapq.heappop(heap)
        if time_a != arrival[row, col]:
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)):
            nr, nc = row + dr, col + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            distance = cell_size_m * (math.sqrt(2) if dr and dc else 1)
            climb = max(0.0, float(elevation[nr, nc] - elevation[row, col])) / climb_rate_ms
            candidate = time_a + distance / cruise_ms + climb
            if candidate < arrival[nr, nc]:
                arrival[nr, nc] = candidate
                heapq.heappush(heap, (candidate, nr, nc))
    return np.where(np.isfinite(arrival), arrival, UNREACHABLE).astype(np.float32)


# ---------------------------------------------------------------------------
# Solver (task 2.3): multi-source Dijkstra, binary heap, deterministic
# ---------------------------------------------------------------------------

def world_to_cell(x, y, rows, cols, cell_size_m):
    row = min(max(int(y / cell_size_m), 0), rows - 1)
    col = min(max(int(x / cell_size_m), 0), cols - 1)
    return row, col


def _nearest_passable(costs, row, col, max_ring=4):
    """Nudge a source off a blocked cell; sources on a ridge edge are a
    placement artifact, not a statement that the team cannot move."""
    if costs[row, col] > 0:
        return row, col
    rows, cols_n = costs.shape
    for ring in range(1, max_ring + 1):
        best = None
        for dr in range(-ring, ring + 1):
            for dc in range(-ring, ring + 1):
                if max(abs(dr), abs(dc)) != ring:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < rows and 0 <= c < cols_n and costs[r, c] > 0:
                    if best is None or costs[r, c] < costs[best]:
                        best = (r, c)
        if best is not None:
            return best
    return None


def solve_field(costs, sources, speed_ms, cell_size_m):
    """Earliest arrival seconds per cell from multiple sources.

    costs: float32 rows x cols, > 0 cost multiplier, -1 blocked.
    sources: list of (row, col) passable cells.
    Edge traversal time = distance * mean(cost_a, cost_b) / speed.

    Heap pattern adapted from the CPython heapq priority-queue recipe
    (lazy deletion: stale entries are skipped on pop, never removed).
    https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes

    Returns float32 rows x cols arrival seconds, UNREACHABLE (-1) where no
    source can arrive. Deterministic: no randomness, stable neighbor order.

    Performance notes (maintainer pipeline, 1024x1024 worst case):
    - Flat integer cell indices and plain Python lists: numpy scalar indexing
      and (time, row, col) tuple keys dominated the profile (~73 s -> ~20 s).
    - The arrival list is float64: the heap keys are float64, and storing
      arrivals as float32 would round some stored values BELOW their heap
      key, making the stale-entry skip discard a cell's best entry and
      silently cutting off propagation (regression: test_flow_field).
    """
    rows, cols_n = costs.shape
    cost = costs.ravel().astype(np.float64).tolist()
    arrival = [math.inf] * (rows * cols_n)
    heap = []
    push = heapq.heappush
    pop = heapq.heappop
    for row, col in sources:
        idx = row * cols_n + col
        arrival[idx] = 0.0
        push(heap, (0.0, idx))

    # Seconds per unit of summed cost, per neighbor direction.
    ortho = 0.5 * cell_size_m / speed_ms
    diag = ortho * math.sqrt(2.0)
    last_col = cols_n - 1
    last_row = rows - 1

    while heap:
        time_a, idx = pop(heap)
        if time_a > arrival[idx]:
            continue  # stale heap entry
        cost_a = cost[idx]
        row, col = divmod(idx, cols_n)
        # (row delta, column delta, seconds per summed cost) - 8-connected.
        for d_row, d_col, weight in (
                (0, -1, ortho), (0, 1, ortho),
                (-1, 0, ortho), (1, 0, ortho),
                (-1, -1, diag), (-1, 1, diag),
                (1, -1, diag), (1, 1, diag)):
            next_row, next_col = row + d_row, col + d_col
            if not (0 <= next_row <= last_row and 0 <= next_col <= last_col):
                continue
            delta = d_row * cols_n + d_col
            if d_row and d_col:
                side_a = row * cols_n + next_col
                side_b = next_row * cols_n + col
                if cost[side_a] <= 0 or cost[side_b] <= 0:
                    continue
            cost_b = cost[idx + delta]
            if cost_b <= 0:
                continue  # blocked
            candidate = time_a + weight * (cost_a + cost_b)
            if candidate < arrival[idx + delta]:
                arrival[idx + delta] = candidate
                push(heap, (candidate, idx + delta))

    grid = np.full((rows, cols_n), UNREACHABLE, dtype=np.float32)
    flat = grid.ravel()
    for idx, value in enumerate(arrival):
        if value != math.inf:
            flat[idx] = value
    return grid


def solve_water_field(water, sources, speed_ms, cell_size_m):
    """Solve only on confirmed water (1); candidate water and land are blocked."""
    water = np.asarray(water)
    costs = np.where(water == 1, 1.0, -1.0).astype(np.float32)
    rows, cols = costs.shape
    valid = []
    for row, col in sources:
        if 0 <= row < rows and 0 <= col < cols and water[row, col] == 1:
            valid.append((row, col))
    arrival = solve_field(costs, valid, speed_ms, cell_size_m)
    # solve_field permits corner-cutting; recompute with the explicit water rule.
    if not valid:
        return np.full((rows, cols), UNREACHABLE, dtype=np.float32)
    arrival = np.full((rows, cols), UNREACHABLE, dtype=np.float32)
    heap = [(0.0, r, c) for r, c in valid]
    for item in heap:
        arrival[item[1], item[2]] = 0.0
    heapq.heapify(heap)
    while heap:
        time_a, row, col = heapq.heappop(heap)
        if time_a != float(arrival[row, col]):
            continue
        for dr, dc, distance in ((-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
                                 (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)),
                                 (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2))):
            nr, nc = row + dr, col + dc
            if not (0 <= nr < rows and 0 <= nc < cols and water[nr, nc] == 1):
                continue
            if dr and dc and (water[row, nc] != 1 or water[nr, col] != 1):
                continue
            candidate = time_a + distance * cell_size_m / speed_ms
            if arrival[nr, nc] < 0 or candidate < arrival[nr, nc]:
                arrival[nr, nc] = candidate
                heapq.heappush(heap, (candidate, nr, nc))
    return arrival


def largest_confirmed_water_component(water):
    """Return the largest 8-connected component of confirmed water cells."""
    water = np.asarray(water)
    rows, cols = water.shape
    unseen = set(zip(*np.where(water == 1)))
    largest = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        component = [start]
        queue = [start]
        while queue:
            row, col = queue.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if not (dr or dc):
                        continue
                    item = (row + dr, col + dc)
                    if item in unseen:
                        unseen.remove(item)
                        queue.append(item)
                        component.append(item)
        if len(component) > len(largest):
            largest = component
    return largest


def synthetic_boat_source(water, anchor_positions, cell_size_m, min_area_m2):
    """Choose a labeled launch cell on the largest confirmed water body."""
    component = largest_confirmed_water_component(water)
    if not component:
        return None, "no_confirmed_water", 0
    area_m2 = len(component) * cell_size_m * cell_size_m
    if area_m2 < min_area_m2:
        return None, "water_below_min_area", len(component)
    if not anchor_positions:
        return None, "no_confirmed_water", len(component)
    anchor_cells = [world_to_cell(x, y, water.shape[0], water.shape[1], cell_size_m)
                    for x, y in anchor_positions]
    row, col = min(component, key=lambda item: min(
        math.hypot(item[0] - ar, item[1] - ac) for ar, ac in anchor_cells))
    return (row, col), None, len(component)


def prepare_sources(costs, positions, cell_size_m):
    """World (x, y) meters -> passable source cells. Returns (cells, dropped)."""
    rows, cols_n = costs.shape
    cells = []
    dropped = 0
    seen = set()
    for x, y in positions:
        row, col = world_to_cell(x, y, rows, cols_n, cell_size_m)
        spot = _nearest_passable(costs, row, col)
        if spot is None:
            dropped += 1
        elif spot not in seen:
            seen.add(spot)
            cells.append(spot)
    return cells, dropped


# ---------------------------------------------------------------------------
# Race-time sampler (task 2.4) and field serializer (task 2.5)
# ---------------------------------------------------------------------------

def sample_quantized_arrival(grid, quantum_s, x, y, cell_size_m, max_ring=3):
    """Sample shipped u1 arrival values, preserving 255 as unreachable."""
    rows, cols_n = grid.shape
    row, col = world_to_cell(x, y, rows, cols_n, cell_size_m)
    best = None
    for ring in range(0, max_ring + 1):
        for dr in range(-ring, ring + 1):
            for dc in range(-ring, ring + 1):
                if max(abs(dr), abs(dc)) != ring:
                    continue
                r, c = row + dr, col + dc
                if (0 <= r < rows and 0 <= c < cols_n
                        and int(grid[r, c]) != QUANT_UNREACHABLE):
                    value = int(grid[r, c]) * quantum_s
                    if best is None or value < best:
                        best = value
        if best is not None:
            break
    return None if best is None else round(float(best), 1)


def quantize_field(field):
    """float32 arrival seconds -> (uint8 grid, quantum seconds).

    255 = unreachable; 0..254 = round(seconds / quantum). Quantum is the
    smallest whole second step covering the capped range, so small maps get
    1 s resolution and huge fields stay within the ~1 MB budget (design D6).
    """
    reachable = field[field >= 0]
    top = float(min(reachable.max(), QUANT_CAP_S)) if reachable.size else QUANT_CAP_S
    quantum = max(1, int(math.ceil(top / 254.0)))
    out = np.full(field.shape, QUANT_UNREACHABLE, dtype=np.uint8)
    mask = field >= 0
    out[mask] = np.minimum(np.rint(np.minimum(field[mask], QUANT_CAP_S) / quantum),
                           254).astype(np.uint8)
    return out, quantum


def write_field(flow_dir, team, agent_class, field, terrain, speed_ms,
                speed_provenance, source_count, dropped_count):
    quantized, quantum = quantize_field(field)
    team_dir = flow_dir / ("team%d" % team)
    team_dir.mkdir(parents=True, exist_ok=True)
    (team_dir / (agent_class + ".bin")).write_bytes(quantized.tobytes())
    sidecar = {
        "format_version": "1.0",
        "artifact": "flow_field",
        "scenario": "initial_deployment",
        "team": team,
        "agent_class": agent_class,
        "grid": {
            "rows": int(field.shape[0]),
            "cols": int(field.shape[1]),
            "cell_size_m": terrain["cell_size_m"],
            "origin": terrain["origin"],
        },
        "quantization": {
            "dtype": "u1",
            "quantum_s": quantum,
            "cap_s": QUANT_CAP_S,
            "unreachable": QUANT_UNREACHABLE,
        },
        "speed_ms": round(speed_ms, 4),
        "speed_provenance": speed_provenance,
        "terrain_profile": CLASS_PROFILE.get(agent_class, "wheeled_vehicle"),
        "source_count": source_count,
        "sources_dropped_blocked": dropped_count,
    }
    (team_dir / (agent_class + ".json")).write_text(
        json.dumps(sidecar, indent=1) + "\n", encoding="ascii")
    return quantized, quantum


def race_times_document(layer, fields):
    """Build race-time JSON from {team: {class: (grid, quantum, cell)}}."""
    race_times = []
    for cp in layer["control_points"]:
        if "x" not in cp:
            continue
        entry = {"cp_id": cp.get("id"), "name": cp.get("name")}
        for team in (1, 2):
            samples = []
            for grid, quantum_s, cell_size_m in fields[team].values():
                value = sample_quantized_arrival(
                    grid, quantum_s, cp["x"], cp["y"], cell_size_m)
                if value is not None:
                    samples.append(value)
            entry["team%d_seconds" % team] = min(samples) if samples else None
        race_times.append(entry)
    return {
        "format_version": "1.0",
        "artifact": "race_times",
        "scenario": "initial_deployment",
        "layer": {"mode": layer["mode"], "size": layer["size"]},
        "control_points": race_times,
    }


def write_race_times(flow_dir, layer, fields):
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "race_times.json").write_text(
        json.dumps(race_times_document(layer, fields), indent=1) + "\n",
        encoding="ascii")


def class_keyed_race_document(layer, class_fields):
    """Serialize class-specific races without pooling incompatible fields."""
    values = {}
    for class_id, fields in sorted(class_fields.items()):
        values[class_id] = {}
        for cp in layer.get("control_points", []):
            if not (isinstance(cp.get("x"), (int, float)) and isinstance(cp.get("y"), (int, float))):
                continue
            cp_id = str(cp.get("id"))
            values[class_id][cp_id] = {}
            for team in (1, 2):
                samples = []
                for grid, quantum, cell_size in fields.get(team, {}).values():
                    value = sample_quantized_arrival(grid, quantum, cp["x"], cp["y"], cell_size)
                    if value is not None:
                        samples.append(value)
                values[class_id][cp_id][str(team)] = min(samples) if samples else None
    return {"format_version": "2.0", "artifact": "race_times",
            "scenario": "initially_assigned_source_assumed_available",
            "layer": "%s_%s" % (layer["mode"], layer["size"]),
            "control_points": [{"cp_id": cp.get("id"), "name": cp.get("name")}
                       for cp in layer.get("control_points", [])
                       if isinstance(cp.get("x"), (int, float))
                       and isinstance(cp.get("y"), (int, float))],
            "race_times": values}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def v2_build_id(map_name, layer_id, catalog, movement, layer, terrain_hashes=None):
    """Return an immutable identity for all inputs that affect one v2 layer."""
    inputs = {"pipeline_version": V2_PIPELINE_VERSION,
              "catalog": catalog, "movement": movement, "layer": layer,
              "terrain": terrain_hashes}
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'))
                           .encode("utf-8")).hexdigest()[:12]
    return "v2-%s-%s-%s" % (map_name, layer_id, digest)


def publish_v2_generation(flow_dir, build_id, files, manifest):
    """Install a validated immutable generation, switching the manifest last.

    ``files`` maps safe relative paths to bytes. Existing generations are not
    overwritten. A failed manifest replacement leaves the previous pointer and
    generation untouched.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", build_id):
        raise ValueError("invalid build id")
    root = Path(flow_dir).resolve()
    generation = root / "generations" / build_id
    expected_inventory = []
    for relative, content in sorted(files.items()):
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("unsafe generation path")
        expected_inventory.append({"path": relative_path.as_posix(),
                                  "sha256": hashlib.sha256(content).hexdigest(),
                                  "bytes": len(content)})
    if generation.exists():
        try:
            existing = validate_v2_generation(root, build_id)
        except Exception as exc:
            raise ValueError("immutable generation exists but is invalid: %s" % build_id) from exc
        if existing.get("files") != expected_inventory:
            raise ValueError("immutable generation content conflicts: " + build_id)
        pointer = root / "class_manifest.json"
        temporary = root / ".class_manifest.json.tmp"
        temporary.write_text(json.dumps({"format_version": "2.0",
                                         "artifact": "flow_class_manifest",
                                         "build_id": build_id,
                                         "generation": "generations/%s" % build_id},
                                        indent=1) + "\n", encoding="ascii")
        os.replace(temporary, pointer)
        return
    staging = root / "generations" / ("." + build_id + ".staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        inventory = []
        for relative, content in sorted(files.items()):
            relative_path = Path(relative)
            target = staging / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            inventory.append({"path": relative_path.as_posix(),
                              "sha256": _sha256(target),
                              "bytes": target.stat().st_size})
        manifest = dict(manifest)
        manifest.update({"format_version": "2.0", "artifact": "flow_class_manifest",
                         "build_id": build_id, "files": inventory})
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n",
                                                encoding="ascii")
        _validate_generation_manifest(staging, build_id, manifest)
        staging.rename(generation)
        pointer = root / "class_manifest.json"
        temporary = root / ".class_manifest.json.tmp"
        temporary.write_text(json.dumps({"format_version": "2.0",
                                         "artifact": "flow_class_manifest",
                                         "build_id": build_id,
                                         "generation": "generations/%s" % build_id},
                                        indent=1) + "\n", encoding="ascii")
        os.replace(temporary, pointer)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _validate_generation_manifest(generation, build_id, manifest):
    """Validate one immutable generation before it becomes active."""
    if manifest.get("format_version") != "2.0" or manifest.get("build_id") != build_id:
        raise ValueError("generation identity mismatch")
    for item in manifest.get("files", []):
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe generation path")
        path = generation / relative
        if not path.is_file() or path.stat().st_size != int(item["bytes"]):
            raise ValueError("generation file length mismatch")
        if _sha256(path) != item["sha256"]:
            raise ValueError("generation file hash mismatch")


def validate_v2_generation(flow_dir, build_id=None):
    """Validate the active immutable generation before a reader consumes it."""
    root = Path(flow_dir).resolve()
    pointer = json.loads((root / "class_manifest.json").read_text(encoding="ascii"))
    if pointer.get("format_version") != "2.0" or pointer.get("artifact") != "flow_class_manifest":
        raise ValueError("unsupported class manifest version")
    selected = build_id or pointer.get("build_id")
    if selected != pointer.get("build_id") or pointer.get("generation") != "generations/%s" % selected:
        raise ValueError("class manifest identity mismatch")
    manifest_path = root / pointer["generation"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    _validate_generation_manifest(manifest_path.parent, selected, manifest)
    return manifest


def load_shipped_fields(flow_dir):
    """Load present bin/sidecar pairs without invoking the solver."""
    fields = {1: {}, 2: {}}
    for team in (1, 2):
        team_dir = flow_dir / ("team%d" % team)
        for agent_class in CLASS_PROFILE:
            bin_path = team_dir / (agent_class + ".bin")
            sidecar_path = team_dir / (agent_class + ".json")
            if not bin_path.exists() and not sidecar_path.exists():
                continue
            if not bin_path.exists() or not sidecar_path.exists():
                raise ValueError("incomplete field pair: %s" % (team_dir / agent_class))
            try:
                sidecar = json.loads(sidecar_path.read_text(encoding="ascii"))
                grid_info = sidecar["grid"]
                rows, cols_n = int(grid_info["rows"]), int(grid_info["cols"])
                quantization = sidecar["quantization"]
                quantum_s = float(quantization["quantum_s"])
                cell_size_m = float(grid_info["cell_size_m"])
            except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
                raise ValueError(
                    "corrupt flow sidecar for map/layer/file %s: %s"
                    % (flow_dir, exc)) from exc
            data = np.frombuffer(bin_path.read_bytes(), dtype=np.uint8)
            if data.size != rows * cols_n:
                raise ValueError(
                    "bin size does not match sidecar for map/layer/file %s" % bin_path)
            fields[team][agent_class] = (
                data.reshape((rows, cols_n)), quantum_s,
                cell_size_m)
    return fields


def regenerate_map_race_times(map_name):
    map_dir = OUT / map_name
    gamelayers_path = map_dir / "gamelayers.json"
    flow_root = map_dir / "flow"
    if not gamelayers_path.exists() or not flow_root.exists():
        print("  SKIP: no flow inputs")
        return False
    layers = json.loads(gamelayers_path.read_text(encoding="utf-8"))["layers"]
    rewritten = 0
    for layer in layers:
        flow_dir = flow_root / ("%s_%s" % (layer["mode"], layer["size"]))
        fields = load_shipped_fields(flow_dir)
        if not any(fields[team] for team in (1, 2)):
            continue
        write_race_times(flow_dir, layer, fields)
        rewritten += 1
    print("  %d race-time files rewritten" % rewritten)
    return True


# ---------------------------------------------------------------------------
# Per-map driver
# ---------------------------------------------------------------------------

def process_map(map_name, infantry_speed, infantry_prov, vehicles, vehicle_source):
    map_dir = OUT / map_name
    gamelayers_path = map_dir / "gamelayers.json"
    terrain_dir = map_dir / "terrain"
    if not gamelayers_path.exists():
        print("  SKIP: no gamelayers.json")
        return False
    if not terrain_dir.exists():
        print("  SKIP: no terrain artifacts (run build_terrain_cost.py first)")
        return False

    layers = json.loads(gamelayers_path.read_text(encoding="utf-8"))["layers"]
    terrain = {cls: load_terrain_artifact(terrain_dir, profile=profile)
               for cls, profile in CLASS_PROFILE.items()}

    fields_written = 0
    for layer in layers:
        mode_size = "%s_%s" % (layer["mode"], layer["size"])
        flow_dir = map_dir / "flow" / mode_size
        inf_sources, veh_sources = layer_team_sources(layer)
        team_fields = {}

        for team in (1, 2):
            team_fields[team] = {}
            # Infantry field.
            cells, dropped = prepare_sources(
                terrain["infantry"]["costs"], inf_sources[team],
                terrain["infantry"]["cell_size_m"])
            if cells:
                field = solve_field(terrain["infantry"]["costs"], cells,
                                    infantry_speed, terrain["infantry"]["cell_size_m"])
                quantized, quantum = write_field(
                    flow_dir, team, "infantry", field, terrain["infantry"],
                    infantry_speed, infantry_prov, len(cells), dropped)
                team_fields[team]["infantry"] = (
                    quantized, quantum, terrain["infantry"]["cell_size_m"])
                fields_written += 1
            # Vehicle field.
            if veh_sources[team]:
                templates = [t for _, _, t in veh_sources[team]]
                speed, prov = pick_vehicle_speed(templates, vehicles, vehicle_source)
                if speed is None:
                    print("  %s team%d vehicles: %s" % (mode_size, team, prov))
                else:
                    cells, dropped = prepare_sources(
                        terrain["vehicles"]["costs"],
                        [(x, y) for x, y, _ in veh_sources[team]],
                        terrain["vehicles"]["cell_size_m"])
                    if cells:
                        field = solve_field(terrain["vehicles"]["costs"], cells,
                                            speed, terrain["vehicles"]["cell_size_m"])
                        quantized, quantum = write_field(
                            flow_dir, team, "vehicles", field,
                            terrain["vehicles"], speed, prov,
                            len(cells), dropped)
                        team_fields[team]["vehicles"] = (
                            quantized, quantum, terrain["vehicles"]["cell_size_m"])
                        fields_written += 1

        if not any(team_fields[t] for t in (1, 2)):
            continue  # no initial-deployment sources in this layer

        write_race_times(flow_dir, layer, team_fields)

    print("  %d layers, %d fields written" % (len(layers), fields_written))
    return True


def _write_v2_field(root, team, class_id, field, terrain, speed, provenance,
                    source_count, dropped_count, map_name, layer_id, build_id,
):
    write_field(root, team, class_id, field, terrain, speed, provenance,
                source_count, dropped_count)
    sidecar_path = root / ("team%d" % team) / (class_id + ".json")
    sidecar = json.loads(sidecar_path.read_text(encoding="ascii"))
    sidecar.update({"format_version": "2.0", "map": map_name,
                    "layer": layer_id, "build_id": build_id,
                    "status": "available"})
    sidecar_path.write_text(json.dumps(sidecar, indent=1) + "\n", encoding="ascii")


def process_map_v2(map_name, infantry_speed, infantry_prov, catalog):
    """Generate a v2 class set and publish it atomically."""
    if catalog.get("format_version") != "2.0":
        raise ValueError("v2 generation requires vehicle_speeds.json format_version 2.0")
    map_dir = OUT / map_name
    layers = json.loads((map_dir / "gamelayers.json").read_text(encoding="utf-8"))["layers"]
    terrain_dir = map_dir / "terrain"
    terrain = {"infantry": load_terrain_artifact(terrain_dir, profile="infantry"),
               "land": load_terrain_artifact(terrain_dir, profile="wheeled_vehicle")}
    # Include masks, costs, diagnostics and provenance, not only configuration:
    terrain_hashes = {path.relative_to(terrain_dir).as_posix(): _sha256(path)
                      for path in sorted(terrain_dir.rglob("*")) if path.is_file()}
    elevation = terrain["land"]["diagnostics"].get("elevation_mean")
    # Older test/legacy artifacts can still build the non-helicopter classes.
    # A real v2 regeneration must have elevation_mean for helicopter fields.
    movement = json.loads(MOVEMENT_PARAMS.read_text(encoding="ascii"))
    helicopter = movement["helicopter"]
    boat_config = movement["boat"]
    for layer in layers:
        layer_id = "%s_%s" % (layer["mode"], layer["size"])
        build_id = v2_build_id(map_name, layer_id, catalog, movement, layer, terrain_hashes)
        work = map_dir / "flow" / ("." + build_id + ".payload")
        shutil.rmtree(work, ignore_errors=True)
        class_fields = {class_id: {1: {}, 2: {}}
                for class_id in ("infantry", "car", "truck_wheeled", "tracked", "boat", "helicopter")}
        statuses = {class_id: {"1": "no_source", "2": "no_source"}
                    for class_id in class_fields}
        inf_sources, _ = layer_team_sources(layer)
        for team in (1, 2):
            cells, dropped = prepare_sources(terrain["infantry"]["costs"], inf_sources[team],
                                             terrain["infantry"]["cell_size_m"])
            if cells:
                field = solve_field(terrain["infantry"]["costs"], cells, infantry_speed,
                                    terrain["infantry"]["cell_size_m"])
                _write_v2_field(work, team, "infantry", field, terrain["infantry"],
                                infantry_speed, infantry_prov, len(cells), dropped,
                                map_name, layer_id, build_id)
                quantized, quantum = quantize_field(field)
                class_fields["infantry"][team]["infantry"] = (quantized, quantum,
                                                               terrain["infantry"]["cell_size_m"])
                statuses["infantry"][str(team)] = "available"
        provenance = {class_id: {"1": {}, "2": {}} for class_id in class_fields}
        for team in (1, 2):
            selected, dropped = v2_vehicle_sources(layer, team, catalog["vehicles"])
            dropped = serialize_dropped_sources(dropped)
            grouped = {class_id: [] for class_id in V2_CLASS_PROFILE}
            for source in selected:
                grouped[source["product_id"]].append(source)
            for class_id, entries in grouped.items():
                source_type = "verified_spawner"
                if class_id == "boat" and not entries:
                    anchors = layer_team_sources(layer)[0][team]
                    cell, reason, component_size = synthetic_boat_source(
                        terrain["land"]["water"], anchors, terrain["land"]["cell_size_m"],
                        float(boat_config["min_water_area_m2"]))
                    if cell is None:
                        statuses[class_id][str(team)] = reason
                        provenance[class_id][str(team)] = {"source_spawners": [],
                            "dropped_sources": dropped, "status": reason}
                        continue
                    entries = [{"name": "synthetic_water_launch", "template": None,
                                "x": cell[1] * terrain["land"]["cell_size_m"],
                                "y": cell[0] * terrain["land"]["cell_size_m"],
                                "product_id": "boat", "speed": 9.0,
                                "classification_evidence": "largest_confirmed_water_component",
                                "source_type": "synthetic_water_launch"}]
                    source_type = "synthetic_water_launch"
                    synthetic_component_size = component_size
                if not entries:
                    statuses[class_id][str(team)] = "no_source"
                    provenance[class_id][str(team)] = {"source_spawners": [],
                        "dropped_sources": dropped, "status": "no_source"}
                    continue
                if class_id == "helicopter" and elevation is None:
                    statuses[class_id][str(team)] = "unsupported_data"
                    provenance[class_id][str(team)] = {"source_spawners": entries,
                        "dropped_sources": dropped, "status": "unsupported_data"}
                    continue
                speed = (float(entries[0]["speed"]) if class_id != "helicopter"
                         else float(helicopter["cruise_ms"]))
                positions = [(item["x"], item["y"]) for item in entries]
                if class_id == "boat":
                    cells = [world_to_cell(x, y, terrain["land"]["rows"], terrain["land"]["cols"],
                                            terrain["land"]["cell_size_m"]) for x, y in positions]
                    valid = [cell for cell in cells if terrain["land"]["water"][cell] == 1]
                    if not valid:
                        statuses[class_id][str(team)] = "off_confirmed_water"
                        continue
                    field = solve_water_field(terrain["land"]["water"], valid, speed,
                                              terrain["land"]["cell_size_m"])
                elif class_id == "helicopter":
                    cells, dropped_count = prepare_sources(
                        np.ones_like(elevation, dtype=np.float32), positions,
                        terrain["land"]["cell_size_m"])
                    field = solve_helicopter_field(elevation, cells,
                        float(helicopter["cruise_ms"]), float(helicopter["climb_rate_ms"]),
                        terrain["land"]["cell_size_m"], float(helicopter["warmup_s"]))
                else:
                    cells, dropped_count = prepare_sources(terrain["land"]["costs"], positions,
                                                            terrain["land"]["cell_size_m"])
                    field = solve_field(terrain["land"]["costs"], cells, speed,
                                        terrain["land"]["cell_size_m"])
                prov = {"source_spawners": entries, "dropped_sources": dropped,
                        "source_type": source_type, "speed_provenance": {
                            "calibrated": False, "text": "v2 catalog estimate; uncalibrated"}}
                if class_id == "boat" and source_type == "synthetic_water_launch":
                    prov["synthetic_rule"] = "largest confirmed water component; nearest to team's initial spawn"
                    prov["water_component_cells"] = synthetic_component_size
                if class_id == "helicopter":
                    prov["model_parameters"] = helicopter
                _write_v2_field(work, team, class_id, field, terrain["land"], speed,
                                json.dumps(prov, sort_keys=True), len(entries), 0,
                                map_name, layer_id, build_id)
                sidecar_path = work / ("team%d" % team) / (class_id + ".json")
                sidecar = json.loads(sidecar_path.read_text(encoding="ascii"))
                sidecar.update(prov)
                sidecar_path.write_text(json.dumps(sidecar, indent=1) + "\n", encoding="ascii")
                quantized, quantum = quantize_field(field)
                class_fields[class_id][team][class_id] = (quantized, quantum,
                                                           terrain["land"]["cell_size_m"])
                statuses[class_id][str(team)] = "available"
                provenance[class_id][str(team)] = prov
        race = class_keyed_race_document(layer, class_fields)
        race.update({"map": map_name, "build_id": build_id,
                     "statuses": statuses, "provenance": provenance})
        work.mkdir(parents=True, exist_ok=True)
        (work / "race_times.json").write_text(json.dumps(race, indent=1) + "\n", encoding="ascii")
        files = {str(path.relative_to(work)): path.read_bytes()
                 for path in sorted(work.rglob("*")) if path.is_file()}
        publish_v2_generation(map_dir / "flow" / layer_id, build_id, files,
                              {"map": map_name, "layer": layer_id,
                               "availability": statuses})
        validate_v2_generation(map_dir / "flow" / layer_id, build_id)
        shutil.rmtree(work, ignore_errors=True)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Compute opening-flow arrival-time fields.")
    parser.add_argument("names", nargs="*",
                        help="maps to process (default: all with gamelayers.json)")
    parser.add_argument("--workers", type=int, default=1,
                        help="parallel map workers (processes, not threads); "
                             "1 = sequential, no pool (default)")
    parser.add_argument("--race-times-only", action="store_true",
                        help="rebuild race_times.json from shipped bins; "
                            "no Dijkstra, no terrain")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    names = args.names
    if not names:
        names = sorted(p.name for p in OUT.iterdir()
                       if p.is_dir() and p.name not in EXCLUDED
                       and (p / "gamelayers.json").exists())
    if args.race_times_only:
        processed = 0
        failures = []
        for index, name in enumerate(names, 1):
            print("[%d/%d] Regenerating %s..." % (index, len(names), name))
            try:
                processed += int(regenerate_map_race_times(name))
            except Exception as exc:
                failures.append((name, exc))
                print("  ERROR: %s: %s" % (type(exc).__name__, exc))
        print()
        print("Summary: %d/%d maps processed." % (processed, len(names)))
        if failures:
            print("Failures:")
            for name, exc in failures:
                print("  %s: %s: %s" % (name, type(exc).__name__, exc))
        return 0 if processed == len(names) and not failures else 1

    # Load configs in the parent: config failures are actionable before any
    # worker spawns, and the small vehicles dict pickles cheaply per task.
    infantry_speed, infantry_prov = load_infantry_speed()
    catalog = load_vehicle_catalog()
    vehicles, vehicle_source = catalog["vehicles"], catalog.get("source", "vehicle_speeds.json")
    print("Infantry sustained speed: %.3f m/s (%s)" % (infantry_speed, infantry_prov))

    processed = 0
    failures = []
    if args.workers == 1 or len(names) < 2:
        for index, name in enumerate(names, 1):
            print("[%d/%d] Processing %s..." % (index, len(names), name))
            if catalog.get("format_version") == "2.0":
                processed += int(process_map_v2(name, infantry_speed, infantry_prov, catalog))
            else:
                processed += int(process_map(name, infantry_speed, infantry_prov,
                                             vehicles, vehicle_source))
    else:
        # One top-level task per map (process_map is module-level and its
        # arguments are small picklable values; no grids cross processes).
        # as_completed + per-future try/except: one map's failure is recorded
        # without aborting the others (docs.python.org concurrent.futures
        # pattern).
        done = 0
        with ProcessPoolExecutor(max_workers=min(args.workers, len(names))) as pool:
            worker = process_map_v2 if catalog.get("format_version") == "2.0" else process_map
            worker_args = (infantry_speed, infantry_prov, catalog) if worker is process_map_v2 else (infantry_speed, infantry_prov, vehicles, vehicle_source)
            futures = {pool.submit(worker, name, *worker_args): name
                       for name in names}
            for future in as_completed(futures):
                name = futures[future]
                done += 1
                try:
                    ok = future.result()
                except Exception as exc:
                    failures.append((name, exc))
                    print("[%d/%d] %s: ERROR %s: %s"
                          % (done, len(names), name, type(exc).__name__, exc))
                    continue
                processed += int(ok)
                print("[%d/%d] %s: %s" % (done, len(names), name,
                                          "OK" if ok else "SKIP"))
    print()
    print("Summary: %d/%d maps processed." % (processed, len(names)))
    if failures:
        print("Failures:")
        for name, exc in sorted(failures):
            print("  %s: %s: %s" % (name, type(exc).__name__, exc))
    return 0 if processed == len(names) and not failures else 1


if __name__ == "__main__":
    sys.exit(main())
