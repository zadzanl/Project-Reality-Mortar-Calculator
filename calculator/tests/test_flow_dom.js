// Ceiling: this tiny DOM/Leaflet fixture checks controller state and option text,
// not layout or painted pixels. Upgrade with browser assertions if visual QA is needed.
import assert from 'node:assert/strict';
import { createFlowController } from '../static/js/flow/flow_overlay.js';

const statuses = {
  available: 'Available',
  no_source: 'No selected source',
  unsupported_data: 'Unsupported source data',
  unsupported_model: 'Unsupported vehicle model',
  not_computed: 'Not computed for this layer',
  unreachable: 'No reachable route for this class',
  corrupt_artifact: 'Flow data failed validation'
};
const classes = ['infantry', 'car', 'truck_wheeled', 'tracked', 'boat', 'helicopter'];

function element(value = '') {
  return { value, textContent: '', innerHTML: '', title: '', style: {}, disabled: false,
    appendChild(child) { this.options.push(child); }, options: [] };
}

function response(body, status = 200) {
  return { ok: status === 200, status, statusText: 'Not Found',
    async json() { return body; }, async arrayBuffer() { return body; } };
}

export async function runFlowDomTests() {
  const old = { document: globalThis.document, window: globalThis.window,
    fetch: globalThis.fetch, requestAnimationFrame: globalThis.requestAnimationFrame,
    cancelAnimationFrame: globalThis.cancelAnimationFrame };
  const nodes = new Map();
  for (const id of ['flow-controls', 'flow-layer-toggle', 'flow-options', 'flow-layer-select',
    'flow-team-select', 'flow-class-select', 'flow-class-reason', 'flow-time-slider',
    'flow-time-label', 'flow-scope-label', 'flow-provenance', 'flow-particles-toggle', 'flow-motion-status',
    'flow-notice', 'flow-race-readout', 'flow-objectives']) nodes.set(id, element());
  const classSelect = nodes.get('flow-class-select');
  classSelect.options = classes.map(element);
  nodes.get('flow-team-select').options = ['both', '1', '2'].map(element);
  Object.defineProperty(classSelect, 'selectedOptions', {
    get() { return this.options.filter((option) => option.value === this.value); }
  });
  globalThis.document = { getElementById: (id) => nodes.get(id) || null,
    createElement: () => element(), addEventListener() {}, removeEventListener() {} };
  globalThis.window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) };
  globalThis.requestAnimationFrame = () => 1; // Rendering is outside this DOM-state check.
  globalThis.cancelAnimationFrame = () => {};
  const base = '/maps/fixture/flow/gpm_cq_64';
  const generation = `${base}/generations/build-1`;
  let availability;
  globalThis.fetch = async (url) => {
    if (url === '/maps/fixture/gamelayers.json') return response({ layers: [{ mode: 'gpm_cq', size: 64, control_points: [] }] });
    if (url === `${base}/class_manifest.json`) return response({ format_version: '2.0', artifact: 'flow_class_manifest', build_id: 'build-1', generation: 'generations/build-1' });
    if (url === `${generation}/manifest.json`) return response({ format_version: '2.0', artifact: 'flow_class_manifest', map: 'fixture', layer: 'gpm_cq_64', build_id: 'build-1', files: [], availability });
    if (url === `${generation}/team1/infantry.json`) return response({ format_version: '2.0', map: 'fixture', layer: 'gpm_cq_64', build_id: 'build-1', grid: { rows: 1, cols: 1, cell_size_m: 4 }, quantization: { quantum_s: 1, unreachable: 255 } });
    if (url === `${generation}/team1/infantry.bin`) return response(Uint8Array.of(0).buffer);
    return response(null, 404);
  };
  try {
    for (const status of Object.keys(statuses).filter((value) => value !== 'available')) {
      availability = Object.fromEntries(classes.map((cls) => [cls,
        { '1': cls === 'infantry' ? 'available' : status, '2': cls === 'infantry' ? 'no_source' : status }]));
      const flow = createFlowController();
      await flow.attachMap({}, 'fixture', 4);
      flow.setActive(true);
      flow.setVisible(true);
      // The public API starts an async load; wait for the controller's data, not a timer.
      for (let i = 0; !flow.state.data && i < 100; i++) await new Promise((resolve) => setImmediate(resolve));
      assert.ok(flow.state.data, `v2 load for ${status}`);
      assert.equal(flow.state.data.formatVersion, '2.0');
      assert.equal(classSelect.options[0].disabled, false);
      assert.ok(classSelect.options[0].title.includes('Available'));
      for (const option of classSelect.options.slice(1)) {
        assert.equal(option.disabled, false, `${status}: ${option.value}`);
        assert.equal(option.title, statuses[status], `${status}: ${option.value} title`);
        assert.ok(option.textContent.includes(statuses[status]), `${status}: ${option.value} label`);
      }
      classSelect.value = 'car'; // Browser select updates before its change handler calls setClass.
      nodes.get('flow-provenance').textContent = 'stale candidate warning';
      nodes.get('flow-scope-label').title = 'stale provenance';
      flow.setClass('car');
      assert.equal(nodes.get('flow-provenance').textContent, '');
      assert.equal(nodes.get('flow-scope-label').title, '');
      for (let i = 0; !flow.state.data && i < 100; i++) await new Promise((resolve) => setImmediate(resolve));
      assert.equal(nodes.get('flow-class-reason').textContent, statuses[status], `${status}: selected reason`);
      flow.setVisible(false);
      assert.equal(nodes.get('flow-provenance').textContent, '');
      assert.equal(nodes.get('flow-scope-label').title, '');
      nodes.get('flow-provenance').textContent = 'stale candidate warning';
      nodes.get('flow-scope-label').title = 'stale provenance';
      flow.setLayer('gpm_cq_32');
      flow.setVisible(true);
      for (let i = 0; i < 100; i++) await new Promise((resolve) => setImmediate(resolve));
      assert.equal(nodes.get('flow-provenance').textContent, '');
      assert.equal(nodes.get('flow-scope-label').title, '');
      flow.detach();
    }
  } finally {
    Object.assign(globalThis, old);
  }
}