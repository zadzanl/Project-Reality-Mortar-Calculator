import assert from 'node:assert';
import {
  buildRaceReadout,
  decodeField,
  fieldSeconds,
  flowUrls,
  formatRaceTime,
  formatDuration,
  loadLayerFields,
  loadLayerManifest,
  objectiveMarkers,
  probeFlow,
  renderBands
} from '../static/js/flow/flow_core.js';
import { bridgeProvenanceLabel } from '../static/js/flow/flow_overlay.js';

function response(status, body, binary = false) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? 'Not Found' : 'Error',
    async json() { return body; },
    async arrayBuffer() { return binary ? body : new TextEncoder().encode(body).buffer; }
  };
}

function field(bytes, quantumS = 15, rows = 1, cols = 4) {
  return decodeField(Uint8Array.from(bytes).buffer, {
    grid: { rows, cols, cell_size_m: 4 },
    quantization: { quantum_s: quantumS, unreachable: 255 }
  });
}

export async function runFlowOverlayTests() {
  const decoded = field([0, 1, 2, 255], 15, 2, 2);
  assert.deepStrictEqual([decoded.rows, decoded.cols, decoded.quantumS], [2, 2, 15]);
  assert.strictEqual(fieldSeconds(2, 15), 30);
  assert.strictEqual(fieldSeconds(255, 15), Infinity);
  assert.throws(() => decodeField(new ArrayBuffer(3), {
    grid: { rows: 2, cols: 2 },
    quantization: { quantum_s: 15 }
  }), /byte length/);

  const flat = field([0, 1, 2, 3, 4, 5, 6, 255], 15, 2, 4);
  const out = new Uint8ClampedArray(32);
  // 8-connectivity: cell 0 borders the later cell 5 diagonally, so no corner gaps.
  renderBands(flat, null, { tSeconds: 60, frontierCells: 1 }, out);
  assert.deepStrictEqual(Array.from(out).filter((_, i) => i % 4 === 3), [255, 255, 255, 255, 255, 0, 0, 0]);
  // Default frontier thickness is 2 cells inward from the reached edge.
  const line = field([0, 1, 2, 3, 4, 5, 6], 15, 1, 7);
  const lineOut = new Uint8ClampedArray(28);
  renderBands(line, null, { tSeconds: 45 }, lineOut);
  assert.deepStrictEqual(Array.from(lineOut).filter((_, i) => i % 4 === 3), [51, 51, 255, 255, 0, 0, 0]);
  renderBands(flat, null, { tSeconds: 120, team1Visible: false }, out);
  assert.deepStrictEqual(Array.from(out), new Array(32).fill(0));
  renderBands(flat, null, { tSeconds: 120 }, out);
  assert.strictEqual(out[4 * 4 + 3], 51);
  assert.strictEqual(out[7 * 4 + 3], 0);

  const team1 = field([0, 4, 8, 10], 15, 1, 4);
  const team2 = field([1, 5, 20, 9], 15, 1, 4);
  renderBands(team1, team2, {
    tSeconds: 300,
    deltaSeconds: 30,
    colors: { team1: [1, 2, 3], team2: [4, 5, 6], contested: [7, 8, 9] }
  }, new Uint8ClampedArray(16));
  const contestedOut = new Uint8ClampedArray(16);
  renderBands(team1, team2, {
    tSeconds: 300,
    deltaSeconds: 30,
    colors: { team1: [1, 2, 3], team2: [4, 5, 6], contested: [7, 8, 9] }
  }, contestedOut);
  assert.deepStrictEqual(Array.from(contestedOut), [7, 8, 9, 160, 7, 8, 9, 160, 1, 2, 3, 51, 7, 8, 9, 160]);

  const markers = objectiveMarkers({ control_points: [
    { id: 1, name: '<North>', team: 1, x: 10, y: 20 },
    { id: 2, name: 'Neutral', team: 0, x: 10, y: 20 },
    { id: 3, name: 'bad', team: 2, x: 999, y: 20 },
    { id: 4, name: 'nan', x: Number.NaN, y: 20 },
    { id: 5, name: 'null', x: null, y: 20 },
    { id: 6, name: 'string', x: '10', y: 20 }
  ] }, 100);
  assert.strictEqual(markers.length, 2);
  assert.deepStrictEqual(markers[0].leaflet, [80, 10]);
  assert.strictEqual(markers[0].name, '<North>');

  // Row zero is north and must remain the first RGBA row; no browser Y flip belongs here.
  const corners = field([1, 2, 3, 4], 1, 2, 2);
  const cornerOut = new Uint8ClampedArray(16);
  renderBands(corners, null, { tSeconds: 10, colors: { team1: [10, 20, 30] } }, cornerOut);
  assert.deepStrictEqual(Array.from(cornerOut).filter((_, i) => i % 4 === 3), [51, 51, 51, 51]);
  assert.strictEqual(cornerOut[0], 10);
  assert.strictEqual(cornerOut[12], 10);

  assert.strictEqual(formatRaceTime(0), '0:00');
  assert.strictEqual(formatRaceTime(155), '2:35');
  assert.strictEqual(formatRaceTime(null), '-');
  assert.strictEqual(formatRaceTime(601), '10:01 (outside 10-minute view)');
  assert.strictEqual(formatRaceTime(600), '10:00');
  assert.strictEqual(formatDuration(601), '10:01');
  assert.strictEqual(bridgeProvenanceLabel({ unverified: true, unrouted_count: 2 }),
    'Candidate deck route; unverified. 2 detected bridge geometry item(s) not routed. ');
  assert.strictEqual(bridgeProvenanceLabel({}), '');
  const race = { control_points: [
    { cp_id: 2, name: 'Zulu', team1_seconds: null, team2_seconds: 20 },
    { cp_id: 1, name: 'Alpha', team1_seconds: 30, team2_seconds: 10 }
  ] };
  assert.deepStrictEqual(buildRaceReadout(race, 1), [
    { cpId: 1, name: 'Alpha', youSeconds: 30, enemySeconds: 10, deltaSeconds: 20 },
    { cpId: 2, name: 'Zulu', youSeconds: null, enemySeconds: 20, deltaSeconds: null }
  ]);
  assert.strictEqual(buildRaceReadout(race, 2)[0].deltaSeconds, -20);
  const v2Race = { format_version: '2.0', selectedClass: 'infantry',
    control_points: [{ cp_id: 7, name: 'Village' }],
    race_times: { infantry: { '7': { '1': 601, '2': null } } } };
  assert.deepStrictEqual(buildRaceReadout(v2Race, 1), [
    { cpId: '7', name: 'Village', youSeconds: 601, enemySeconds: null, deltaSeconds: null }
  ]);
  assert.strictEqual(buildRaceReadout({ ...v2Race, control_points: undefined }, 1)[0].name, '7');

  assert.deepStrictEqual(flowUrls('adak', 'gpm_cq_64').fieldBin(1, 'infantry'), '/maps/adak/flow/gpm_cq_64/team1/infantry.bin');
  const calls = [];
  const docs = new Map();
  const sidecar = { grid: { rows: 1, cols: 1, cell_size_m: 4 }, quantization: { quantum_s: 1, unreachable: 255 } };
  docs.set('/maps/demo/gamelayers.json', response(200, { layers: [] }));
  docs.set('/maps/demo/flow/layer/team1/infantry.json', response(200, sidecar));
  docs.set('/maps/demo/flow/layer/team1/infantry.bin', response(200, Uint8Array.from([0]).buffer, true));
  const fetchFn = async (url) => {
    calls.push(url);
    return docs.get(url) || response(404, null);
  };
  assert.deepStrictEqual(await probeFlow('demo', fetchFn), { layers: [] });
  assert.strictEqual(await probeFlow('missing', fetchFn), null);
  const loaded = await loadLayerFields('demo', 'layer', fetchFn);
  assert.strictEqual(loaded.fields[1].infantry.bytes[0], 0);
  assert.strictEqual(loaded.fields[1].vehicles, null);
  assert.strictEqual(loaded.raceTimes, null);
  await assert.rejects(() => probeFlow('broken', async () => response(500, null)), /500/);
  await assert.rejects(() => loadLayerFields('broken', 'layer', async (url) => {
    if (url.endsWith('infantry.json')) return response(500, null);
    return response(404, null);
  }), /500/);

  const v2Sidecar = {
    format_version: '2.0', map: 'v2demo', layer: 'gpm_cq_64', build_id: 'build-1',
    grid: { rows: 1, cols: 1, cell_size_m: 4 }, quantization: { quantum_s: 1, unreachable: 255 }
  };
  const v2Pointer = { format_version: '2.0', artifact: 'flow_class_manifest', build_id: 'build-1', generation: 'generations/build-1' };
  const v2Manifest = {
    format_version: '2.0', artifact: 'flow_class_manifest', map: 'v2demo', layer: 'gpm_cq_64', build_id: 'build-1',
    files: [{ path: 'team1/infantry.bin', bytes: 1, sha256: 'fixture' }]
  };
  const v2Docs = new Map([
    ['/maps/v2demo/flow/gpm_cq_64/class_manifest.json', response(200, v2Pointer)],
    ['/maps/v2demo/flow/gpm_cq_64/generations/build-1/manifest.json', response(200, v2Manifest)],
    ['/maps/v2demo/flow/gpm_cq_64/generations/build-1/team1/infantry.json', response(200, v2Sidecar)],
    ['/maps/v2demo/flow/gpm_cq_64/generations/build-1/team1/infantry.bin', response(200, Uint8Array.from([0]).buffer, true)]
  ]);
  const v2Fetch = async (url) => v2Docs.get(url) || response(404, null);
  assert.deepStrictEqual(await loadLayerManifest('v2demo', 'gpm_cq_64', v2Fetch), v2Pointer);
  const v2Loaded = await loadLayerFields('v2demo', 'gpm_cq_64', v2Fetch);
  assert.strictEqual(v2Loaded.formatVersion, '2.0');
  assert.strictEqual(v2Loaded.buildId, 'build-1');
  assert.strictEqual(v2Loaded.fields[1].infantry.bytes[0], 0);
  await assert.rejects(() => loadLayerFields('v2demo', 'gpm_cq_64', async (url) => {
    if (url.endsWith('/manifest.json')) return response(200, { ...v2Manifest, map: 'wrong' });
    return v2Fetch(url);
  }), /identity mismatch/);
  assert.ok(calls.length > 0);
}
