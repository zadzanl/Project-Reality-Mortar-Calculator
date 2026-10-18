/**
 * Pure flow-field decoding, rendering, and loading helpers.
 *
 * Flow bytes are already in repository orientation: row zero is north and
 * columns increase east. Keeping this module DOM-free lets the browser
 * controller and Node tests share the same data contract.
 *
 * @module flow_core
 */

const DEFAULT_COLORS = {
  team1: [59, 130, 246],
  team2: [249, 115, 22],
  contested: [253, 224, 71]
};

const DEFAULT_FRONTIER_ALPHA = 255;
const DEFAULT_FILL_ALPHA = 51;
// Frontier line thickness in grid cells, measured inward from the reached edge.
const DEFAULT_FRONTIER_CELLS = 2;
export const FLOW_CLASSES = ['infantry', 'car', 'truck_wheeled', 'tracked', 'boat', 'helicopter'];

function responseError(response, url) {
  const error = new Error(`Failed to load flow resource ${url}: ${response.status} ${response.statusText || ''}`.trim());
  error.status = response.status;
  return error;
}

async function fetchResponse(fetchFn, url) {
  const response = await fetchFn(url);
  if (!response.ok) {
    throw responseError(response, url);
  }
  return response;
}

function isNotFound(error) {
  return error && error.status === 404;
}

/**
 * Decode one raw uint8 flow field using its per-field sidecar metadata.
 * @param {ArrayBuffer} arrayBuffer Raw row-major field bytes.
 * @param {Object} sidecar Field sidecar containing grid and quantization data.
 * @returns {{rows: number, cols: number, bytes: Uint8Array, quantumS: number, cellSizeM: number, unreachable: number}}
 */
export function decodeField(arrayBuffer, sidecar) {
  const rows = sidecar?.grid?.rows;
  const cols = sidecar?.grid?.cols;
  const quantumS = sidecar?.quantization?.quantum_s;
  const cellSizeM = sidecar?.grid?.cell_size_m;
  const unreachable = sidecar?.quantization?.unreachable ?? 255;
  if (!Number.isInteger(rows) || rows <= 0 || !Number.isInteger(cols) || cols <= 0) {
    throw new Error('Flow sidecar grid rows and cols must be positive integers');
  }
  if (!(quantumS > 0)) {
    throw new Error('Flow sidecar quantum_s must be greater than zero');
  }
  const bytes = new Uint8Array(arrayBuffer);
  const expectedLength = rows * cols;
  if (bytes.length !== expectedLength) {
    throw new Error(`Flow field byte length ${bytes.length} does not match grid ${rows}x${cols} (${expectedLength})`);
  }
  return { rows, cols, bytes, quantumS, cellSizeM, unreachable };
}

/**
 * Convert a quantized byte to seconds while preserving the unreachable sentinel.
 * @param {number} byte Quantized arrival byte.
 * @param {number} quantumS Seconds represented by one reachable byte.
 * @returns {number} Arrival seconds, or Infinity for the sentinel byte.
 */
export function fieldSeconds(byte, quantumS) {
  return byte === 255 ? Infinity : byte * quantumS;
}

/**
 * Render team frontier bands and contested cells into caller-owned RGBA bytes.
 * @param {Object|null} field1 Decoded team 1 field.
 * @param {Object|null} field2 Decoded team 2 field.
 * @param {Object} options Rendering thresholds, visibility, colors, and alphas.
 * @param {Uint8ClampedArray} out RGBA output buffer.
 * @returns {Uint8ClampedArray} The same output buffer.
 */
export function renderBands(field1, field2, options = {}, out) {
  const field = field1 || field2;
  if (!field) {
    if (out) out.fill(0);
    return out;
  }
  if (field1 && field2 && (field1.rows !== field2.rows || field1.cols !== field2.cols)) {
    throw new Error('Flow fields must have identical rows and cols');
  }
  const size = field.rows * field.cols * 4;
  if (!(out instanceof Uint8ClampedArray) || out.length !== size) {
    throw new Error(`Flow RGBA output must contain ${size} bytes`);
  }
  const tSeconds = options.tSeconds ?? 0;
  const deltaSeconds = options.deltaSeconds ?? 30;
  const team1Visible = options.team1Visible ?? true;
  const team2Visible = options.team2Visible ?? true;
  const colors = { ...DEFAULT_COLORS, ...(options.colors || {}) };
  const fillAlpha = options.fillAlpha ?? DEFAULT_FILL_ALPHA;
  const frontierAlpha = options.frontierAlpha ?? DEFAULT_FRONTIER_ALPHA;
  const frontierCells = options.frontierCells ?? DEFAULT_FRONTIER_CELLS;
  out.fill(0);

  function isFrontier(source, index) {
    const row = Math.floor(index / source.cols);
    const col = index % source.cols;
    // The map exterior is not a frontier. Only a later or unreached in-grid
    // neighbor within frontierCells marks this reached cell as frontier.
    for (let dr = -frontierCells; dr <= frontierCells; dr += 1) {
      const r = row + dr;
      if (r < 0 || r >= source.rows) continue;
      for (let dc = -frontierCells; dc <= frontierCells; dc += 1) {
        const c = col + dc;
        if (c < 0 || c >= source.cols || (dr === 0 && dc === 0)) continue;
        if (fieldSeconds(source.bytes[r * source.cols + c], source.quantumS) > tSeconds) return true;
      }
    }
    return false;
  }

  for (let i = 0; i < field.rows * field.cols; i += 1) {
    const t1 = field1 ? fieldSeconds(field1.bytes[i], field1.quantumS) : Infinity;
    const t2 = field2 ? fieldSeconds(field2.bytes[i], field2.quantumS) : Infinity;
    const reachable1 = team1Visible && t1 <= tSeconds;
    const reachable2 = team2Visible && t2 <= tSeconds;
    let color = null;
    let alpha = 0;
    if (reachable1 && reachable2 && Math.abs(t1 - t2) <= deltaSeconds) {
      color = colors.contested;
      alpha = 160;
    } else if (reachable1 && (!reachable2 || t1 <= t2)) {
      color = colors.team1;
      alpha = isFrontier(field1, i) ? frontierAlpha : fillAlpha;
    } else if (reachable2) {
      color = colors.team2;
      alpha = isFrontier(field2, i)
        ? frontierAlpha : fillAlpha;
    }
    const offset = i * 4;
    if (color) {
      out[offset] = color[0];
      out[offset + 1] = color[1];
      out[offset + 2] = color[2];
      out[offset + 3] = alpha;
    }
  }
  return out;
}

/**
 * Validate and project control points for a selected game layer.
 * This helper is DOM-free so malformed map data can be regression-tested.
 * @param {Object|null} gameLayer Selected layer metadata.
 * @param {number} mapSize Repository map size in meters.
 * @returns {Array<Object>} Safe marker records in Leaflet coordinates.
 */
export function objectiveMarkers(gameLayer, mapSize) {
  if (!gameLayer || !Array.isArray(gameLayer.control_points) || !(mapSize > 0)) return [];
  return gameLayer.control_points.filter((point) => {
    return point && Number.isFinite(point.x) && Number.isFinite(point.y)
      && point.x >= 0 && point.x <= mapSize
      && point.y >= 0 && point.y <= mapSize
      && point.id !== undefined && point.id !== null;
  }).map((point) => ({
    cpId: point.id,
    name: String(point.name || point.id),
    team: [0, 1, 2].includes(point.team) ? point.team : null,
    unableToChangeTeam: Boolean(point.unable_to_change_team),
    x: Number(point.x),
    y: Number(point.y),
    leaflet: [mapSize - Number(point.y), Number(point.x)]
  }));
}

/**
 * Format seconds as a minute-and-second race time.
 * @param {number|null} seconds Race time in seconds.
 * @returns {string} m:ss or - for missing/unreachable values.
 */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '-';
  const wholeSeconds = Math.max(0, Math.floor(seconds));
  return `${Math.floor(wholeSeconds / 60)}:${String(wholeSeconds % 60).padStart(2, '0')}`;
}

export function formatRaceTime(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '-';
  return formatDuration(seconds) + (seconds > 600 ? ' (outside 10-minute view)' : '');
}

/**
 * Build a name-sorted race-time readout from the race-times document.
 * @param {Object} raceTimesDoc Race-times JSON document.
 * @param {1|2} perspectiveTeam Team shown as you.
 * @returns {Array<Object>} Relative race-time rows.
 */
export function buildRaceReadout(raceTimesDoc, perspectiveTeam) {
  if (perspectiveTeam !== 1 && perspectiveTeam !== 2) throw new Error('perspectiveTeam must be 1 or 2');
  if (raceTimesDoc?.format_version === '2.0') {
    const names = Object.fromEntries((raceTimesDoc.control_points || []).map((cp) => [String(cp.cp_id), cp.name]));
    return Object.entries(raceTimesDoc.race_times?.[raceTimesDoc.selectedClass] || {}).map(([cpId, times]) => {
      const youSeconds = times?.[String(perspectiveTeam)] ?? null;
      const enemySeconds = times?.[String(perspectiveTeam === 1 ? 2 : 1)] ?? null;
      return { cpId, name: String(names[cpId] || cpId), youSeconds, enemySeconds,
        deltaSeconds: youSeconds == null || enemySeconds == null ? null : youSeconds - enemySeconds };
    }).sort((a, b) => a.name.localeCompare(b.name));
  }
  return (raceTimesDoc?.control_points || []).map((point) => {
    const youSeconds = point[`team${perspectiveTeam}_seconds`] ?? null;
    const enemySeconds = point[`team${perspectiveTeam === 1 ? 2 : 1}_seconds`] ?? null;
    return {
      cpId: point.cp_id,
      name: point.name,
      youSeconds,
      enemySeconds,
      deltaSeconds: youSeconds === null || enemySeconds === null ? null : youSeconds - enemySeconds
    };
  }).sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Build root-relative URLs for one flow layer.
 * @param {string} mapName Map directory name.
 * @param {string} layerId Mode-size directory name.
 * @returns {Object} URL builders for layer resources.
 */
export function flowUrls(mapName, layerId) {
  const base = `/maps/${mapName}/flow/${layerId}`;
  return {
    gamelayers: `/maps/${mapName}/gamelayers.json`,
    raceTimes: `${base}/race_times.json`,
    fieldBin: (team, cls) => `${base}/team${team}/${cls}.bin`,
    fieldSidecar: (team, cls) => `${base}/team${team}/${cls}.json`
  };
}

function safeRelativePath(value) {
  if (typeof value !== 'string' || !value || value.startsWith('/') || value.includes('\\')) return false;
  return value.split('/').every((part) => part && part !== '.' && part !== '..');
}

function validateManifest(pointer, manifest, mapName, layerId) {
  if (pointer?.format_version !== '2.0' || pointer?.artifact !== 'flow_class_manifest'
    || !safeRelativePath(pointer.generation) || !pointer.build_id) {
    throw new Error('Invalid flow class manifest pointer');
  }
  if (manifest?.format_version !== '2.0' || manifest.build_id !== pointer.build_id
    || manifest.map !== mapName || manifest.layer !== layerId || !Array.isArray(manifest.files)) {
    throw new Error('Flow manifest identity mismatch');
  }
  for (const item of manifest.files) {
    if (!safeRelativePath(item.path) || !Number.isInteger(item.bytes) || typeof item.sha256 !== 'string') {
      throw new Error('Invalid flow manifest file entry');
    }
  }
  return pointer.build_id;
}

export async function loadLayerManifest(mapName, layerId, fetchFn) {
  const url = `/maps/${mapName}/flow/${layerId}/class_manifest.json`;
  try {
    return await (await fetchResponse(fetchFn, url)).json();
  } catch (error) {
    if (error?.status === 404) return null;
    throw error;
  }
}

async function loadV2LayerFields(mapName, layerId, fetchFn, pointer) {
  const base = `/maps/${mapName}/flow/${layerId}/${pointer.generation}`;
  const manifest = await (await fetchResponse(fetchFn, `${base}/manifest.json`)).json();
  const buildId = validateManifest(pointer, manifest, mapName, layerId);
  const fields = Object.fromEntries([1, 2].map((team) => [team,
    Object.fromEntries(FLOW_CLASSES.map((cls) => [cls, null]))]));
  const sidecars = {};
  async function loadOne(team, cls) {
    try {
      const sidecar = await (await fetchResponse(fetchFn, `${base}/team${team}/${cls}.json`)).json();
      if (sidecar.format_version !== '2.0' || sidecar.map !== mapName
        || sidecar.layer !== layerId || sidecar.build_id !== buildId) {
        throw new Error(`Flow sidecar identity mismatch for ${cls}`);
      }
      const buffer = await (await fetchResponse(fetchFn, `${base}/team${team}/${cls}.bin`)).arrayBuffer();
      const decoded = decodeField(buffer, sidecar);
      sidecars[`team${team}/${cls}`] = sidecar;
      return decoded;
    } catch (error) {
      if (error?.status === 404) return null;
      throw error;
    }
  }
  await Promise.all([1, 2].flatMap((team) => FLOW_CLASSES.map(async (cls) => {
    fields[team][cls] = await loadOne(team, cls);
  })));
  let raceTimes = null;
  try {
    raceTimes = await (await fetchResponse(fetchFn, `${base}/race_times.json`)).json();
    if (raceTimes.format_version !== '2.0' || raceTimes.map !== mapName
      || raceTimes.layer !== layerId || raceTimes.build_id !== buildId) {
      throw new Error('Flow race manifest identity mismatch');
    }
  } catch (error) {
    if (error?.status !== 404) throw error;
  }
  return { fields, raceTimes, sidecars, manifest, buildId, formatVersion: '2.0' };
}

/**
 * Probe whether a map has flow metadata, distinguishing absence from failure.
 * @param {string} mapName Map directory name.
 * @param {Function} fetchFn Injected fetch implementation.
 * @returns {Promise<Object|null>} Parsed game layers, or null on 404.
 */
export async function probeFlow(mapName, fetchFn) {
  const url = `/maps/${mapName}/gamelayers.json`;
  try {
    return await (await fetchResponse(fetchFn, url)).json();
  } catch (error) {
    if (error?.status === 404) return null;
    throw error;
  }
}

/**
 * Load all optional team/class fields and optional race times for a layer.
 * @param {string} mapName Map directory name.
 * @param {string} layerId Mode-size directory name.
 * @param {Function} fetchFn Injected fetch implementation.
 * @returns {Promise<Object>} Decoded fields, optional race-times document,
 *   and the raw sidecars (keyed 'teamN/class') for provenance display.
 */
export async function loadLayerFields(mapName, layerId, fetchFn) {
  const pointer = await loadLayerManifest(mapName, layerId, fetchFn);
  if (pointer) return loadV2LayerFields(mapName, layerId, fetchFn, pointer);
  const urls = flowUrls(mapName, layerId);
  const fields = { 1: { infantry: null, vehicles: null, car: null, truck_wheeled: null,
    tracked: null, boat: null, helicopter: null }, 2: { infantry: null, vehicles: null,
    car: null, truck_wheeled: null, tracked: null, boat: null, helicopter: null } };
  const sidecars = {};

  async function loadOne(team, cls) {
    try {
      const sidecar = await (await fetchResponse(fetchFn, urls.fieldSidecar(team, cls))).json();
      const buffer = await (await fetchResponse(fetchFn, urls.fieldBin(team, cls))).arrayBuffer();
      const decoded = decodeField(buffer, sidecar);
      sidecars[`team${team}/${cls}`] = sidecar;
      return decoded;
    } catch (error) {
      if (error?.status === 404) return null;
      throw error;
    }
  }

  const pairs = [];
  for (const team of [1, 2]) {
    for (const cls of ['infantry', 'vehicles']) {
      pairs.push(loadOne(team, cls).then((field) => { fields[team][cls] = field; }));
    }
  }
  await Promise.all(pairs);
  let raceTimes = null;
  try {
    raceTimes = await (await fetchResponse(fetchFn, urls.raceTimes)).json();
  } catch (error) {
    if (error?.status !== 404) throw error;
  }
  return { fields, raceTimes, sidecars };
}
