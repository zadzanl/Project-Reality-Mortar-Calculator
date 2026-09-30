#!/usr/bin/env python3
"""Compute opening-flow arrival-time fields (design D1, D4, D9, D10).

Loads per-map terrain cost grids built by build_terrain_cost.py (the
add-terrain-traversability-model change owns cost-grid construction; see
design.md "Implementation Deviations") and spawn/spawner positions from
gamelayers.json, then runs multi-source Dijkstra per layer/team/agent-class
and ships quantized arrival-time grids plus race_times.json under
processed_maps/<map>/flow/. Maintainer-side only; the browser only
thresholds the shipped grids (no physics in JavaScript).

Output layout per map (browser loader contract):
  flow/<mode>_<size>/race_times.json     per control point: you-vs-enemy seconds
  flow/<mode>_<size>/team<1|2>/<class>.bin   uint8 rows*cols, 255 = unreachable
  flow/<mode>_<size>/team<1|2>/<class>.json  sidecar: grid, quantization,
                                             speed + provenance, scenario field

<class> is "infantry" (terrain profile infantry) or "vehicles" (terrain
profile wheeled_vehicle). Sidecars carry no timestamps: identical inputs
must produce byte-for-byte identical artifacts.

Usage:
  python processor/build_flow_fields.py              # all maps with inputs
  python processor/build_flow_fields.py asad_khal    # one map
  python processor/build_flow_fields.py --workers 4  # parallel across maps
    python processor/build_flow_fields.py --race-times-only  # rebuild race times from bins

Parallelism is across maps with processes, not threads: the solver is a
CPU-bound pure-Python heap loop, so the GIL would pin threads to one core
(docs.python.org/3.11/library/threading.html). Per-map outputs are disjoint
and byte-identical regardless of worker count; only wall time changes. With
--workers > 1, per-layer log lines from worker processes may interleave with
the parent's progress lines, and Ctrl-C waits for in-flight solves to finish
(ProcessPoolExecutor shutdown semantics).
"""
import argparse
import heapq
import json
import math
import os
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
QUANT_CAP_S = 3600.0        # arrival times above this saturate (display is 5 min)

# Flow agent class -> terrain artifact profile.
CLASS_PROFILE = {"infantry": "infantry", "vehicles": "wheeled_vehicle"}


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


def load_vehicle_speeds(path=VEHICLE_SPEEDS):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc["vehicles"], doc.get("source", "vehicle_speeds.json")


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
        # (flat offset, seconds per summed cost, valid?) - 8-connected.
        for delta, weight, valid in (
                (-1, ortho, col > 0),
                (1, ortho, col < last_col),
                (-cols_n, ortho, row > 0),
                (cols_n, ortho, row < last_row),
                (-cols_n - 1, diag, row > 0 and col > 0),
                (-cols_n + 1, diag, row > 0 and col < last_col),
                (cols_n - 1, diag, row < last_row and col > 0),
                (cols_n + 1, diag, row < last_row and col < last_col)):
            if not valid:
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
        "terrain_profile": CLASS_PROFILE[agent_class],
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
    vehicles, vehicle_source = load_vehicle_speeds()
    print("Infantry sustained speed: %.3f m/s (%s)" % (infantry_speed, infantry_prov))

    processed = 0
    failures = []
    if args.workers == 1 or len(names) < 2:
        for index, name in enumerate(names, 1):
            print("[%d/%d] Processing %s..." % (index, len(names), name))
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
            futures = {pool.submit(process_map, name, infantry_speed,
                                   infantry_prov, vehicles, vehicle_source): name
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
