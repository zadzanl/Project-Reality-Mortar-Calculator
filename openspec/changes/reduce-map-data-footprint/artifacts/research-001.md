# Research 001 — Browser/UI map-artifact loading (scoping for `reduce-map-data-footprint`)

Read-only reconnaissance. No files were modified except this document. No subagents dispatched.

## Environment fingerprint

- **OS:** Windows (PowerShell / pwsh), host path `C:\Projects\Project_Reality-Mortar-Calculator`
- **Repo branch:** `feat/opening-flow-simulator` (HEAD `f6ba143` Merge remote-tracking branch 'origin/main' into feat/opening-flow-simulator)
- **Date of reconnaissance:** 2026-10-09 (local +07:00)
- **Working tree:** DIRTY. Uncommitted modifications relevant to this change:
  - `M calculator/static/js/app.js`
  - `M calculator/static/js/flow/flow_core.js`
  - `M calculator/static/js/flow/flow_overlay.js`
  - `M calculator/templates/index.html`
  - `M calculator/static/css/styles.css`
  - plus `?? calculator/tests/test_flow_dom.js`, `?? openspec/changes/reduce-map-data-footprint/`
  - `calculator/static/js/heightmap.js` and `calculator/server.py` are **NOT** modified.
- All file:line evidence below reflects the **current working tree** (uncommitted changes included), because the flow files were read as they exist on disk now.

---

## Q1. Does the browser load `terrain/*.bin` grids today?

**No.** There is no browser/JS code path that fetches any file under `terrain/`. The only `.bin` the browser fetches are **flow fields** under `flow/<layer>/generations/<gen>/team<N>/<class>.bin`. `terrain/*.bin` grids are consumed **only by the Python processor** (see Q3b).

Complete enumeration of every map-artifact load in `calculator/static/js/` (and the HTML entry point):

### Entry point — `calculator/templates/index.html`
- L385–386: `<script src="/static/lib/pako.min.js">` (gzip fallback lib, not a map artifact)
- L388: `<script type="module" src="/static/js/app.js">`
- No map-artifact URLs in HTML.

### `calculator/static/js/app.js` (map lifecycle)
- **L83:** `const response = await fetch('/maps/list');` — map list JSON (server-generated, not a per-map file).
- **L228:** `const minimapUrl = \`/maps/${state.currentMap}/minimap.png\`;`
- **L231:** `const img = new Image();` then **L233:** `state.terrainLayer = L.imageOverlay(minimapUrl, bounds);` — **loads `minimap.png`** via `<img>` + Leaflet `imageOverlay` (not `fetch`).
- **L265:** fallback overlay `state.terrainLayer = L.imageOverlay(canvas.toDataURL(), bounds);` — only on `img.onerror` (minimap missing).
- **L393:** `const contourUrl = \`/maps/${state.currentMap}/contourmap.png\`;`
- **L395–398:** `const testImg = new Image();` … `state.contourLayer = L.imageOverlay(contourUrl, bounds);` — **loads `contourmap.png`** via `<img>` + `imageOverlay`.
- Leaflet marker icons are `/static/lib/images/*` (L875–880, L1328–1330) — not map artifacts.

### `calculator/static/js/heightmap.js`
- **L70:** `const baseUrl = \`/maps/${mapName}/heightmap.json\`;`
- **L71–74:** candidates `[`${baseUrl}.gz`, `${baseUrl}.gzip`, baseUrl]` — **loads `heightmap.json.gz`** (preferred), `.gzip` (Android), plain `.json` (fallback).
- **L84:** `const r = await fetch(url);` (in candidate loop)
- **L104–130:** gzip decode (see Q2).
- **L130:** `heightmapData = await response.json();` (plain-JSON branch)
- **L186–187:** `const url = \`/maps/${mapName}/metadata.json\`; const response = await fetch(url);` — **loads `metadata.json`**.
- **L193:** `const metadata = await response.json();`

### `calculator/static/js/flow/flow_core.js` (all flow loads; fetch injected)
- **L233–238 `flowUrls(mapName, layerId)`:** base `=` `/maps/${mapName}/flow/${layerId}`
  - **L234:** `gamelayers: \`/maps/${mapName}/gamelayers.json\``
  - **L235:** `raceTimes: \`${base}/race_times.json\``
  - **L236:** `fieldBin: (team, cls) => \`${base}/team${team}/${cls}.bin\``
  - **L237:** `fieldSidecar: (team, cls) => \`${base}/team${team}/${cls}.json\``
- **L264:** `const url = \`/maps/${mapName}/flow/${layerId}/class_manifest.json\`;` (v2 pointer)
- **L275:** `${base}/manifest.json` where `base = /maps/${mapName}/flow/${layerId}/${pointer.generation}`
- **L282:** `${base}/team${team}/${cls}.json` (sidecar)
- **L287:** `${base}/team${team}/${cls}.bin` (raw uint8 flow field → `arrayBuffer()`)
- **L301:** `${base}/race_times.json`
- **L319:** `const url = \`/maps/${mapName}/gamelayers.json\`;` (`probeFlow`)
- **L347:** legacy path `urls.fieldSidecar(team, cls)` (same as L237)
- **L367:** legacy path `urls.raceTimes` (same as L235)
- Note: `decodeField` (L47) reads flow bytes as `Uint8Array`; flow bins are already uint8 and are **not** in scope for quantization.

### `calculator/static/js/flow/flow_overlay.js` (Leaflet shell)
- **L39–44:** imports `loadLayerFields`, `probeFlow` from `./flow_core.js`.
- **L261:** `gamelayers = await probeFlow(mapName, fetch);` — passes **global `fetch`** into flow_core.
- **L345:** `ctrl.cache.set(key, loadLayerFields(ctrl.mapName, ctrl.layerId, fetch));` — passes **global `fetch`**.
- No direct `fetch`/URL of its own; all network goes through `flow_core.js`.

### Summary of per-map files the browser actually requests
1. `heightmap.json.gz` (+ `.gzip` / `.json` fallbacks) — `heightmap.js`
2. `metadata.json` — `heightmap.js`
3. `minimap.png` — `app.js`
4. `contourmap.png` — `app.js`
5. `gamelayers.json` — `flow_core.js`
6. `flow/<layer>/class_manifest.json` — `flow_core.js`
7. `flow/<layer>/<generation>/manifest.json` — `flow_core.js`
8. `flow/<layer>/<generation>/team<N>/<class>.json` (sidecar) — `flow_core.js`
9. `flow/<layer>/<generation>/team<N>/<class>.bin` — `flow_core.js`
10. `flow/<layer>/<generation>/race_times.json` — `flow_core.js`
11. `flow/<layer>/team<N>/<class>.{json,bin}` and `flow/<layer>/race_times.json` (legacy layout) — `flow_core.js`
12. `/maps/list` (server route, not a file under a map folder) — `app.js`

**`obstructions.json` and `terrain/*.bin` are absent from this list.**

### Map-folder artifact inventory (names/sizes only — `processed_maps/test_bootcamp`)
Top level: `contourmap.png` (125,972 B), `gamelayers.json` (701,516 B), `heightmap.json.gz` (159,396 B), `metadata.json` (445 B), `minimap.png` (1,850,455 B), `obstructions.json` (7,862,849 B).
`terrain/`: `sidecar.json` + `elevation_mean.bin`, `road_mask.bin`, `roughness_m_mean.bin`, `slope_deg_max.bin`, `slope_deg_mean.bin`, `static_multiplier.bin`, `vegetation_dense.bin`, `water.bin`, `edge_grade_max.bin`, `edge_rise_m_max.bin`, plus `infantry/{cost.bin,classes.bin,sidecar.json}` and `wheeled_vehicle/{cost.bin,classes.bin,sidecar.json}`.
`flow/<layer>/class_manifest.json` + `flow/<layer>/generations/<gen>/{manifest.json, race_times.json, team1/*, team2/*}`.

---

## Q2. How `heightmap.js` decodes `heightmap.json.gz` (the pattern to reuse)

Mechanism: `fetch` → `response.blob()` → **native `DecompressionStream('gzip')`** with a **`window.pako.inflate` fallback** → `JSON.parse`. The server does **not** send `Content-Encoding` (see Q4), so the browser decompresses manually.

Verbatim (`calculator/static/js/heightmap.js` L104–130):

```js
if (resolvedUrl.endsWith('.gz') || resolvedUrl.endsWith('.gzip')) {
  // Decompress gzipped response
  const blob = await response.blob();

  try {
    if ('DecompressionStream' in window) {
      const ds = new DecompressionStream('gzip');
      const decompressedStream = blob.stream().pipeThrough(ds);
      const decompressedBlob = await new Response(decompressedStream).blob();
      const text = await decompressedBlob.text();
      heightmapData = JSON.parse(text);
    } else {
      throw new Error('DecompressionStream not supported');
    }
  } catch (err) {
    console.warn('DecompressionStream failed or not supported, falling back to pako:', err);
    if (window.pako) {
      const arrayBuffer = await blob.arrayBuffer();
      const decompressed = window.pako.inflate(new Uint8Array(arrayBuffer), { to: 'string' });
      heightmapData = JSON.parse(decompressed);
    } else {
      throw new Error('GZIP decompression failed: DecompressionStream not supported and pako not found');
    }
  }
} else {
  // Plain JSON
  heightmapData = await response.json();
}
```

Supporting facts:
- `pako.min.js` is vendored at `calculator/static/lib/pako.min.js` and loaded in `index.html` L385–386.
- Candidate URL selection (`heightmap.js` L70–102) tries `.gz`, then `.gzip`, then plain, and only falls back on HTTP 404 (other statuses throw).

**Important for this change:** this decode path is the only in-repo precedent for `.json.gz` in the browser, and it is currently wired **only** to `heightmap.json.gz`. No other module imports or reuses it.

---

## Q3. Does ANY browser code read `obstructions.json`?

**No.** A repo-wide search of `*.js`, `*.html`, `*.css`, `*.bat`, `*.json` (excluding `processed_maps/`, `www/`, `android/`, `node_modules/`, `__pycache__/`) for `obstruction` returned **zero** matches. The string `obstruction` does not appear in `app.js`, `heightmap.js`, `flow_core.js`, `flow_overlay.js`, `ballistics.js`, `coordinates.js`, `index.html`, or `server.py`.

Therefore, for task 2.2 ("update all obstructions readers … any UI path found in 1.1"), the UI path count is **zero** — there is no browser reader to update for `obstructions.json.gz`.

### Q3b. Who actually reads/writes `obstructions.json` (processor side)
- **Writer:** `processor/extract_obstructions.py` **L206–208** — `destination = OUT / name / "obstructions.json"`; `destination.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")`. Output document keys: `map_name`, `format_version` ("1.0"), `roads`, `statics`, `vegetation`, `counts`.
- **Reader:** `processor/build_terrain_cost.py` **L592** — `obstructions = json.loads(obstructions_path.read_text(encoding="utf-8"))`; consumes `roads`, `statics`, `vegetation` (L593–595). Also writes a provenance string at **L516**: `"obstructions": "processed_maps/%s/obstructions.json" % map_name`.
- **Reader (QA):** `processor/render_obstruction_qa.py` **L31** — `json.loads((directory / "obstructions.json").read_text(encoding="utf-8"))`.
- **Reader (spike):** `processor/spike_material_map.py` **L37** — `OBSTRUCTIONS_PATH = ROOT / "processed_maps" / MAP_NAME / "obstructions.json"`.
- **Tests:** `processor/tests/test_terrain_cost.py` L190, L253 write fixtures named `obstructions.json`.

### Who reads `terrain/*.bin` (processor side, not browser)
- `processor/terrain_artifact.py` **L17–65** — `load_terrain_artifact()`; validates `sidecar.get("format_version") != "1.0"` (L21); `read_grid()` (L37) decodes `<f4` for `cost.bin`/diagnostics and `u1` for `classes.bin`, `road_mask.bin`, `water.bin`.
- `processor/build_flow_fields.py` **L862, L938–939** — `load_terrain_artifact(terrain_dir, profile=...)`.
- `processor/render_terrain_qa.py` **L21** — `load_terrain_artifact(directory / "terrain", profile)`.

**Consequence:** the "reader changes" for both `obstructions.json.gz` and quantized `terrain/*.bin` are **Python-processor-only** plus the server MIME route. No JS reader change is required unless the change later decides to surface obstructions/terrain in the UI.

---

## Q4. How the Flask server serves these files (Content-Encoding?)

`calculator/server.py` (Flask, `send_from_directory`). **No `Content-Encoding` header is set anywhere in the file** (searched: zero matches). The browser therefore receives raw gzip bytes for `.json.gz` and must decompress manually — exactly what `heightmap.js` does.

Routes and lines:
- **L79:** `@app.route('/maps/<map_name>/<path:filename>')` → `serve_map_data`. Sanitizes path segments (`secure_filename`), enforces resolved-path containment under `PROCESSED_MAPS_DIR`, then serves.
- **L133–139:** `if safe_filename.endswith('.json.gz'):` → `send_from_directory(..., mimetype='application/json', as_attachment=False)`. **No `Content-Encoding`.**
- **L141–142:** `elif safe_filename.endswith('.json'):` → `send_from_directory(..., mimetype='application/json')`.
- **L144:** `else:` → `send_from_directory(resolved_map_dir, safe_filename)` (covers `.png`, `.bin`, etc.).
- **L147–154:** `@app.route('/processed_maps/<map_name>/<path:filename>')` — backwards-compat alias that calls the same `serve_map_data`.
- **L156:** `@app.route('/maps/list')` → scans `PROCESSED_MAPS_DIR` for dirs containing `metadata.json`.
- `PROCESSED_MAPS_DIR = PROJECT_ROOT / 'processed_maps'` (L52).

This matches commit `70b935d feat(server): serve nested map artifacts` (the `/maps/<map>/<path:filename>` route with nested-path support). So `.json.gz` is already served correctly as `application/json` without `Content-Encoding`; a new `obstructions.json.gz` needs **no server change** to be served (it will hit L133).

Caveat: `secure_filename` is applied per segment. Fine for `obstructions.json.gz`, `terrain/*.bin`, and `flow/<gen>/team1/*.bin`.

---

## Q5. URL paths → `processed_maps/`, and `www/` mirroring for Android

### Desktop (Flask)
- `/maps/<map>/<path>` → `processed_maps/<map>/<path>` (server.py L79–144).
- `/processed_maps/<map>/<path>` → same files (back-compat, L147–154).
- `/maps/list` → enumerated from `processed_maps/*/metadata.json` (L156–176).

### Android (Capacitor, `webDir: "www"`)
`capacitor.config.json`: `webDir: "www"`, `server.androidScheme: "https"`. `build-android.bat` regenerates `www/` each build:
- `xcopy /E /I /Y calculator\static www\static`; `copy calculator\templates\index.html www\`; **`xcopy /E /I /Y processed_maps www\processed_maps`**; `copy mapsList.json www\`.
- Renames every `*.gz` under `www/processed_maps` → `*.gzip` (aapt strips `.gz`): `for /r www\processed_maps %%F in (*.gz) do ren "%%F" "%%~nF.gzip"`.
- Rewrites paths in **only two files**: `www/static/js/app.js` (`'/maps/list'` → `'mapsList.json'`; `` `/maps/${` `` → `` `processed_maps/${` ``; `'/static/lib/images/` → `'static/lib/images/`) and `www/static/js/heightmap.js` (`` `/maps/${mapName}/` `` → `` `processed_maps/${mapName}/` ``; `/maps/[mapName]/` → `processed_maps/[mapName]/`).
- `build-android.sh` mirrors the same logic (L77–78 copy, L85–86 `.gz`→`.gzip`, L111–115 rewrites).

**So `www/` mirrors `processed_maps/` 1:1** (all files, including `terrain/*.bin` and `obstructions.json`), plus a `.gz`→`.gzip` rename. `www/` currently exists on disk with `processed_maps/`, `static/`, `index.html`, `mapsList.json`.

**Gap found (pre-existing, not caused by this change):** neither build script rewrites the `/maps/${...}` URLs inside `flow/flow_core.js`. On Android the flow overlay's `/maps/...` URLs are not remapped to `processed_maps/...`, unlike `app.js`/`heightmap.js`. This is a latent Android-flow issue to be aware of, and it also means a *new* browser reader for `obstructions.json.gz`/`terrain` would need its own rewrite entry (and the `.gz`→`.gzip` rename) if it were ever added.

### Android `.gz`→`.gzip` interaction with a new `obstructions.json.gz`
The rename loop turns `obstructions.json.gz` into `obstructions.json.gzip` in `www/`. Since no browser code reads it today, this only matters if a reader is added later; any such reader must try `.gz` **and** `.gzip` (as `heightmap.js` does at L71–74).

---

## Intersection with the in-flight `add-opening-flow-simulator` work (uncommitted)

The dirty files that this change's readers *might* touch are `app.js`, `flow_core.js`, `flow_overlay.js`, `index.html` (all modified by the flow work). However:
- The two artifacts in scope (`obstructions.json.gz`, quantized `terrain/*.bin`) have **no JS reader**, so there is **no mandatory edit** to those dirty files for this change.
- `heightmap.js` (the gzip-decode pattern source) is **clean** (unmodified).
- `server.py` is **clean** and already serves `.json.gz` correctly.
- Risk: if the flow work adds/renames map artifacts or edits `flow_core.js` URL builders concurrently, a later `build-android.bat` run (task 5.2) regenerates `www/` wholesale — safe — but rebasing flow changes onto a changed `processed_maps/` layout needs a re-verify.

---

## Worklog (what was searched/read)

- `git rev-parse`/`git log`/`git status --short` — branch, HEAD, dirty tree.
- Listed `calculator/static/js` (6 files: app.js, ballistics.js, coordinates.js, heightmap.js, flow/flow_core.js, flow/flow_overlay.js) and full `calculator/` source inventory.
- Grepped `calculator/static/js`, `calculator/templates`, `calculator/server.py` for `fetch(`, `.json`, `.bin`, `.gz`, `.png`, `processed_maps`, `obstructions`, `terrain`, `DecompressionStream`, `pako`, `inflate`.
- Read `heightmap.js` in full (decode mechanism, URL candidates, metadata loader).
- Read `server.py` in full (routes, MIME, containment; confirmed no `Content-Encoding`).
- Read `flow_core.js` in full (URL builders, v2 + legacy load paths, `decodeField`).
- Read `flow_overlay.js` L1–60 and L240–360 (imports, `probeFlow`/`loadLayerFields` with global `fetch`).
- Read `index.html` in full (script/asset tags).
- Grepped `app.js` and `flow_overlay.js` for artifact URLs; read `app.js` L224–270 and L388–405 (PNG overlay creation).
- Read `build-android.bat` in full; grepped `build-android.sh`; listed `www/` top level.
- Listed `processed_maps/test_bootcamp` (recursive, names only) and top-level with sizes; read small `metadata.json` (445 B); measured `obstructions.json` sizes across all maps (listing only, never opened).
- Grepped `processor/*.py` for `obstructions.json`, `read_grid`, `terrain_cost`, `load_terrain_artifact`; read `build_terrain_cost.py` L585–615, `extract_obstructions.py` L190–215, `render_obstruction_qa.py` L20–40.
- Read the change docs `design.md` and `tasks.md` to align (design Open Question #1 is this sub-goal).

**Dead ends / non-findings:**
- No service worker, no `XMLHttpRequest`, no `new Worker`, no dynamic `import()` of artifact paths.
- `vehicle_speeds.json` (under `calculator/static/data/`, modified in the working tree) is **not** fetched by any JS; it is a **processor** input (`processor/build_flow_fields.py` L57, L100–103; `processor/extract_vehicle_speeds.py` L25). Not a browser artifact.
- Initial `git status` and a directory listing were scrambled once by terminal output interleaving from a concurrent process; re-ran cleanly. All reported values are from the clean runs.

## Measurement note / discrepancy
Design.md states "single files up to 182 MB; 5.16 GB of JSON total". This reconnaissance measured **84 `obstructions.json` files totaling 5,345,742,801 bytes (~5.35 GB decimal / ~4.98 GiB)**, largest `fields_of_kassel` at 191,505,130 bytes (~191.5 MB). The counts/sizes differ slightly from design.md — likely captured at a different time or map set. Flagged for the change author; does not alter the direction of D1.

## Unknowns
1. Whether the flow-simulation work will (in the future) surface obstructions/terrain in the UI. If yes, a browser reader for `obstructions.json.gz` would be needed and must reuse the `heightmap.js` `DecompressionStream`/`pako` pattern; today it does not.
2. Whether the Android flow-overlay URL gap (`flow_core.js` `/maps/` not rewritten by `build-android.bat`/`.sh`) is intended or a known bug — out of scope here but adjacent.
3. `metadata.json` (browser) also carries `format_version: "1.0"` — separate from the terrain sidecar `format_version`. Confirm no consumer keys off the browser metadata version when terrain bumps to "1.2" (heightmap.js only validates `map_size` and `height_scale`, L193–198).

## Risks
- **False "no reader" confidence:** the conclusion that no JS reads `obstructions.json`/`terrain/*.bin` is based on current working-tree JS + build scripts. A future UI feature would invalidate it; re-run the `obstruction`/`terrain/` grep before finalizing task 2.2/3.3.
- **Android mirror:** `www/processed_maps` mirrors all new/removed artifacts automatically, but the `.gz`→`.gzip` rename and the two-file path rewrite mean any *new* JS reader must handle `.gzip` and be added to the rewrite list in both `build-android.bat` and `build-android.sh`.
- **Server route relies on extension:** `obstructions.json.gz` is served by the generic L133 branch; if the change ships a different extension (e.g. `.json.gzip`) on desktop, the `application/json` MIME branch would not match and it would fall to the generic branch (L144). Keep the `.json.gz` name on desktop.
- **Terminal output interleaving** from a concurrent process during recon; mitigated by re-running affected commands.
