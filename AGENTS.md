# AGENTS.md - Project Reality Mortar Calculator

What is this: A firing solutions calculator for mortars in Project Reality: BF2. Takes into account height deltas automatically. Support Project Reality: BF2 v1.9 (March 2026)

## Efficient Engineering Mode (Required)

Be an efficient senior engineer, but never careless. After understanding the request and tracing the affected flow, stop at the first option that works:

1. Does this actually need to be built? If no, do not build it (YAGNI: You Ain't Gonna Need It).
2. Is the user solving the right problem, or patching a symptom while the real bug laughs from two files over?
3. Is there already something in this codebase that does this? Because you'd be amazed how often there is. Check whether an existing repository pattern or helper exists. Use the standard library, platform, or an installed dependency. Do not install new dependencies without asking.
4. Do the user's ideas, strategies, or code account for blind spots, weak assumptions, and structural flaws?
5. Is this overengineered for what's actually needed? Write the smallest correct, readable change.
6. Is this request safe, boring, and exactly what a committee of middle managers would approve and if so, is there a sharper version hiding underneath?

Prefer deletion, boring solutions, no new dependencies, no unrequested abstractions, and the fewest line changes possible. Fix bugs at their shared root cause after checking all callers.

This never permits skipping retrieval, trust-boundary validation, data-loss prevention, security, accessibility, requested work, or the orchestration and verification workflow below.

Leave one smallest runnable regression check for non-trivial logic; document a deliberate known ceiling with a file header comment and its upgrade path.

### Working With a Multiple Developer Seniority and Discipline

This repository are maintained by multiple maintainers. Some of them are senior, but most of them are junior. Some of them comes from system , embedded, or data engineering. Always adjust the communication, planning, and report to be understandable by any developer, regardless of seniority or backgrounds. 

The engineering bar is unchanged: correct, tested, no new dependencies without asking — but *how* work is planned and handed over changes. **Prefer the option a thorough junior developer can run, debug, and explain, over the option a senior would find elegant**. Generalizable rules are valid beyond the persistence change:

- **Delete machinery instead of engineering around it.** Fewer moving parts beats clever parts; the simplest correct, readable change is the target. Before building an abstraction, ask whether a step can simply be removed.
- **Reach for the framework's documented pattern before inventing one.** Copy the official tutorial shape (e.g., FastAPI's SQL-databases pattern) so a stuck developer can google an answer that maps 1:1 onto this repo.
- **One prerequisite, not two.** Don't make a developer install and learn two tools when one already-installed tool does the job.
- **Every setup step needs one visible "did it work?" check.** A README must be runnable top-to-bottom on a fresh machine; each step should end in an obvious verification (`pip check` prints `No broken requirements found.`, `/health` returns `{"status":"OK"}`).
- **Fail with an actionable message, not an opaque stack trace.** A two-line guard (`if not DATABASE_URL: raise RuntimeError("create a .env with ...")`) beats a config framework and beats a raw `ArgumentError`.
- **Record the reasoning and who agreed.** For all non-trivial decisions, keep the tradeoff and the perspectives considered in the change artifacts so the next person doesn't redo the analysis.

## Standard Working Method

1. Clarify the requested outcome and inspect the affected files before editing.
2. Check `openspec/changes/` for an active change affecting your area.
3. For non-trivial work, retrieve context first; keep exploration, planning, implementation, and review as bounded, non-overlapping steps. Confirm material changes to behaviour, scope, architecture, data, cost, or risk before implementing.
4. Use OpenSpec to propose, implement, and archive material changes. Keep implementation small, reversible, and directly traceable to approved requirements.
5. Verify each change with focused checks, then broader relevant checks when practical. Report exactly what was and was not verified. Never use unverified positive claims.

---

## Project-Specific Instructions

### Read These Files FIRST (in this order)

1. **`PRD.md`** - WHAT to build: all requirements, exact formulas and numbers. **If documents disagree, PRD.md is always correct.**
2. **`openspec/project.md`** - HOW to build: tools, naming, code style, Project Reality game rules.
3. **`openspec/AGENTS.md`** - WHEN to write proposals (new features only; skip for bug fixes).

Before coding: read the relevant PRD.md section, check style rules in project.md, and check `openspec/changes/` for conflicting in-progress work.

### Critical Numbers and Formulas (copy exactly, never change)

- **Gravity:** 14.86 meters per second squared (NOT 9.8 - that is Earth gravity; 14.86 is Project Reality game gravity)
- **Projectile speed:** 148.64 meters per second
- **Maximum range:** 1500 meters
- **Coordinates:** origin (0, 0) at the top-left corner (Northwest). X = left to right (West to East), Y = top to bottom (North to South), Z = elevation (up/down).
- **Height:** `elevation_m = (pixel_value / 65535.0) * height_scale` - `pixel_value` is 0 to 65535 from the heightmap, `height_scale` is the max map height from terrain.con (usually 100 to 1000 meters). Never change 65535.

### Version 1 Scope

**Build these:**

1. One mortar + one target (multiple mortars come in later versions)
2. Three coordinate dropdowns: column (A through M), row (1 through 13), keypad (1-9)
3. Flask server that only serves files (HTML, CSS, JavaScript, JSON) - all math runs in the browser
4. Leaflet.js vendored in the project folder - no CDN/internet links
5. Heightmaps as JSON (not PNG), keeping full 16-bit precision (0 to 65535)
6. Bilinear interpolation - average the 4 surrounding pixels when reading height between pixels
7. High-angle calculation in Mils, shown in both Mils and Degrees
8. Fully offline - no external websites or APIs

**Do NOT build (save for V2+):** multiple mortars/targets; working save/load (placeholder buttons that do nothing are OK); 3D trajectory view (2D map only).

### Android Build

- Source of truth: `calculator/templates/` and `calculator/static/`. Never edit `www/` - `build-android.bat` deletes and regenerates it from `calculator/`.
- After UI/code changes, run `build-android.bat` (or `npx cap sync android`) to copy `www/` into `android/app/src/main/assets/public/`.

### Map Processing (Maintainer Only)

End users never run these scripts - pre-processed maps ship in the repository.

- **Phase 1 - `collect_maps.py`** (PC with the game installed): find server.zip files, verify checksums, copy to `/raw_map_data/`, create manifest.json, set up Git LFS for big files, upload to GitHub.
- **Phase 2 - `process_maps.ipynb`** (Google Colab or local Jupyter, game not required): read server.zip files from `/raw_map_data/`, extract heightmaps, convert to JSON in `/processed_maps/`, auto-upload to GitHub (needs git name, email, token).
- Keep the phases separate: collection code only in `collect_maps.py`, conversion code only in `process_maps.ipynb`, no direct dependency of Phase 2 on Phase 1. Never modify files in `/raw_map_data/`.
- **Excluded map:** `the_falklands` - its 8km x 8km play area has airfields and a helicopter carrier far outside the boundary, making it non-standard. Do not process it through the normal pipeline without special instructions.
- **Terrain orientation:** Heightmap JSON retains raw BF2 row order (south first). `build_terrain_cost.py` reverses rows once before deriving terrain; artifact row 0 is north, matching minimap images and repository-space roads. Never flip the renderer or rewrite source heightmaps to compensate.
- **Processor test safety:** Exclude `processor/tests/test_update_manifest.py` when running pytest; it overwrites a raw manifest checksum at import time. Safe command: `python -m pytest processor/tests/ --ignore=processor/tests/test_update_manifest.py`.

### Proposal vs. Just Fix It

- **Write a proposal first** when adding something new (save/load buttons, 3D view, database) or changing how something works (coordinate system, map library, physics numbers - but never change the physics numbers).
- **Just fix it (no proposal)** for bugs (wrong math, broken click handler), code cleanup (comments, naming, formatting), and text/doc updates (typos, README, PRD.md instructions).

**CRITICAL: Keep AGENTS.md and relevant tracking documents updated as the project evolves. AGENTS.md is the first file any new worker, AI agent or contributor will read.** Any updates must be kept concise, standalone (all information stored here, requiring no external information), and easily understood by an intern.
