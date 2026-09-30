import assert from 'node:assert';
import {
  buildRaceReadout,
  decodeField,
  fieldSeconds,
  flowUrls,
  formatRaceTime,
  loadLayerFields,
  probeFlow,
  renderBands
} from '../static/js/flow/flow_core.js';

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
  renderBands(flat, null, { tSeconds: 60 }, out);
  assert.deepStrictEqual(Array.from(out).filter((_, i) => i % 4 === 3), [128, 128, 128, 128, 107, 0, 0, 0]);
  renderBands(flat, null, { tSeconds: 120, team1Visible: false }, out);
  assert.deepStrictEqual(Array.from(out), new Array(32).fill(0));
  renderBands(flat, null, { tSeconds: 120 }, out);
  assert.strictEqual(out[4 * 4 + 3], 107);
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
  assert.deepStrictEqual(Array.from(contestedOut), [7, 8, 9, 160, 7, 8, 9, 160, 1, 2, 3, 86, 7, 8, 9, 160]);

  // Row zero is north and must remain the first RGBA row; no browser Y flip belongs here.
  const corners = field([1, 2, 3, 4], 1, 2, 2);
  const cornerOut = new Uint8ClampedArray(16);
  renderBands(corners, null, { tSeconds: 10, colors: { team1: [10, 20, 30] } }, cornerOut);
  assert.deepStrictEqual(Array.from(cornerOut).filter((_, i) => i % 4 === 3), [128, 128, 128, 128]);
  assert.strictEqual(cornerOut[0], 10);
  assert.strictEqual(cornerOut[12], 10);

  assert.strictEqual(formatRaceTime(0), '0:00');
  assert.strictEqual(formatRaceTime(155), '2:35');
  assert.strictEqual(formatRaceTime(null), '-');
  const race = { control_points: [
    { cp_id: 2, name: 'Zulu', team1_seconds: null, team2_seconds: 20 },
    { cp_id: 1, name: 'Alpha', team1_seconds: 30, team2_seconds: 10 }
  ] };
  assert.deepStrictEqual(buildRaceReadout(race, 1), [
    { cpId: 1, name: 'Alpha', youSeconds: 30, enemySeconds: 10, deltaSeconds: 20 },
    { cpId: 2, name: 'Zulu', youSeconds: null, enemySeconds: 20, deltaSeconds: null }
  ]);
  assert.strictEqual(buildRaceReadout(race, 2)[0].deltaSeconds, -20);

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
  assert.ok(calls.length > 0);
}
