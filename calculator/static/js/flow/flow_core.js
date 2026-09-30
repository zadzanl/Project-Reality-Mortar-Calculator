/**
 * Pure flow-field decoding, rendering, and loading helpers.
 *
 * Flow bytes are already in repository orientation: row zero is north and
 * columns increase east. Keeping this module DOM-free lets the browser
 * controller and Node tests share the same data contract.
 *
 * @module flow_core
 */

const DEFAULT_ALPHAS = [128, 107, 86, 66, 46];
const DEFAULT_COLORS = {
  team1: [59, 130, 246],
  team2: [249, 115, 22],
  contested: [253, 224, 71]
};

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
  const bandSeconds = options.bandSeconds ?? 60;
  const team1Visible = options.team1Visible ?? true;
  const team2Visible = options.team2Visible ?? true;
  const colors = { ...DEFAULT_COLORS, ...(options.colors || {}) };
  const alphas = options.alphas || DEFAULT_ALPHAS;
  out.fill(0);

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
    } else if (reachable1 && reachable2) {
      // Non-contested overlap belongs to the team that arrives earlier.
      if (t1 <= t2) {
        color = colors.team1;
        alpha = alphas[Math.min(Math.floor(t1 / bandSeconds), alphas.length - 1)];
      } else {
        color = colors.team2;
        alpha = alphas[Math.min(Math.floor(t2 / bandSeconds), alphas.length - 1)];
      }
    } else if (reachable1) {
      color = colors.team1;
      alpha = alphas[Math.min(Math.floor(t1 / bandSeconds), alphas.length - 1)];
    } else if (reachable2) {
      color = colors.team2;
      alpha = alphas[Math.min(Math.floor(t2 / bandSeconds), alphas.length - 1)];
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
 * Format seconds as a minute-and-second race time.
 * @param {number|null} seconds Race time in seconds.
 * @returns {string} m:ss or - for missing/unreachable values.
 */
export function formatRaceTime(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '-';
  const wholeSeconds = Math.max(0, Math.floor(seconds));
  return `${Math.floor(wholeSeconds / 60)}:${String(wholeSeconds % 60).padStart(2, '0')}`;
}

/**
 * Build a name-sorted race-time readout from the race-times document.
 * @param {Object} raceTimesDoc Race-times JSON document.
 * @param {1|2} perspectiveTeam Team shown as you.
 * @returns {Array<Object>} Relative race-time rows.
 */
export function buildRaceReadout(raceTimesDoc, perspectiveTeam) {
  if (perspectiveTeam !== 1 && perspectiveTeam !== 2) throw new Error('perspectiveTeam must be 1 or 2');
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
  const urls = flowUrls(mapName, layerId);
  const fields = { 1: { infantry: null, vehicles: null }, 2: { infantry: null, vehicles: null } };
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
