/**
 * Leaflet shell for the opening-flow overlay (presentation only).
 *
 * All data math lives in flow_core.js (DOM-free, Node-tested). This module
 * owns the map lifecycle: one persistent canvas positioned in the overlay
 * pane, rAF-coalesced redraws, a per-layer Promise cache, and stale-load
 * guards modeled on the mapLoadToken pattern in app.js.
 *
 * ORIENTATION: flow bytes are row-0-north (the pipeline already reversed
 * rows). Canvas pixel row 0 is the top (north) edge of the overlay, so
 * bytes go into ImageData in natural row order. Do NOT copy the row flip
 * from heightmap.js; that flip exists because raw heightmaps are
 * row-0-south.
 *
 * LEAFLET NOTE: L.imageOverlay only accepts IMG elements in Leaflet 1.9.4
 * (_initImage checks tagName === 'IMG'), so the live canvas is positioned
 * in the overlay pane by a small custom L.Layer instead. Known ceiling:
 * the canvas repositions on 'move viewreset resize', not during the
 * animated zoom transition, so a fast zoom shows a brief stretch before
 * snapping back. Upgrade path: handle 'zoomanim' the way
 * ImageOverlay._animateZoom does.
 *
 * MEMORY: decoded fields are cached per map+layer (~4 MB per layer at
 * 1024x1024); the cache is dropped on map switch.
 *
 * PARTICLES: optional cosmetic advection along the field's negative
 * gradient (toward earlier arrival, i.e. back toward the spawns that
 * produced the reach). Off by default; hard-stopped on overlay hide, map
 * switch, and tab hide. Particles derive ONLY from the loaded field and
 * are never an input to any firing/physics decision.
 *
 * @module flow_overlay
 */

import {
  buildRaceReadout,
  formatRaceTime,
  loadLayerFields,
  probeFlow,
  renderBands
} from './flow_core.js';

const DEFAULT_LAYER = 'gpm_cq_64';
const MAX_TIME_SECONDS = 300;
const BAND_SECONDS = 60;
const CONTESTED_DELTA_SECONDS = 30;
const TEAM_VALUES = ['both', '1', '2'];
const CLASS_VALUES = ['infantry', 'vehicles'];
const PARTICLE_COUNT = 150;
const PARTICLE_SPEED_MS = 60; // cosmetic data-space speed, not a game value
const TRAIL_FADE_ALPHA = 0.08;

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Shorten cpname_<map>_<mode><size>_<flag> to its trailing flag name. */
function shortCpName(name, mapName) {
  let short = String(name || '').replace(/^cpname_/, '');
  if (mapName && short.startsWith(`${mapName}_`)) {
    short = short.slice(mapName.length + 1);
  }
  short = short.replace(/^[a-z]+\d+_/, '');
  return short || String(name || '');
}

/**
 * Position a live canvas in the overlay pane. L.imageOverlay cannot do
 * this in Leaflet 1.9.4 (IMG elements only), hence the custom layer.
 */
function createCanvasOverlay(canvas, bounds) {
  const CanvasLayer = L.Layer.extend({
    onAdd(map) {
      this._map = map;
      canvas.style.position = 'absolute';
      canvas.style.pointerEvents = 'none';
      canvas.style.imageRendering = 'pixelated';
      map.getPanes().overlayPane.appendChild(canvas);
      this._update();
      map.on('move viewreset resize', this._update, this);
    },
    onRemove(map) {
      map.off('move viewreset resize', this._update, this);
      canvas.remove();
      this._map = null;
    },
    _update() {
      if (!this._map) {
        return;
      }
      const nw = this._map.latLngToLayerPoint(bounds.getNorthWest());
      const se = this._map.latLngToLayerPoint(bounds.getSouthEast());
      L.DomUtil.setPosition(canvas, nw);
      canvas.style.width = `${se.x - nw.x}px`;
      canvas.style.height = `${se.y - nw.y}px`;
    }
  });
  return new CanvasLayer();
}

/**
 * Create the flow overlay controller. The returned API is driven by
 * initFlowControls (DOM) and by app.js map lifecycle calls.
 */
export function createFlowController() {
  const ctrl = {
    leafletMap: null,
    mapName: null,
    mapSize: 0,
    gamelayers: null,
    available: false,
    visible: false,
    layerId: null,
    teamSel: 'both',
    classSel: 'infantry',
    tSeconds: MAX_TIME_SECONDS,
    data: null,
    emptyLayers: new Set(),
    particlesOn: false,
    particleSys: null,
    loadToken: 0,
    canvas: null,
    ctx: null,
    imageData: null,
    overlayLayer: null,
    renderScheduled: false,
    cache: new Map()
  };

  return {
    attachMap: (map, mapName, mapSize) => attachMap(ctrl, map, mapName, mapSize),
    detach: () => detach(ctrl),
    setVisible: (visible) => setVisible(ctrl, visible),
    setLayer: (layerId) => {
      if (ctrl.layerId !== layerId) {
        ctrl.layerId = layerId;
        reload(ctrl);
      }
    },
    setTeam: (sel) => {
      if (TEAM_VALUES.includes(sel) && ctrl.teamSel !== sel) {
        ctrl.teamSel = sel;
        updateReadout(ctrl);
        scheduleRender(ctrl);
        if (ctrl.particleSys) {
          spawnParticles(ctrl, ctrl.particleSys);
        }
      }
    },
    setClass: (cls) => {
      if (CLASS_VALUES.includes(cls) && ctrl.classSel !== cls) {
        ctrl.classSel = cls;
        updateOptionStates(ctrl);
        updateProvenance(ctrl);
        scheduleRender(ctrl);
        if (ctrl.particleSys) {
          spawnParticles(ctrl, ctrl.particleSys);
        }
      }
    },
    setTime: (seconds) => {
      ctrl.tSeconds = Math.max(0, Math.min(MAX_TIME_SECONDS, seconds));
      scheduleRender(ctrl);
    },
    setParticles: (enabled) => {
      ctrl.particlesOn = Boolean(enabled);
      if (ctrl.particlesOn) {
        startParticles(ctrl);
      } else {
        stopParticles(ctrl);
      }
    },
    state: ctrl
  };
}

/** Wire the flow control block in index.html to the controller. */
export function initFlowControls(flow) {
  const toggle = el('flow-layer-toggle');
  if (!toggle) {
    return;
  }
  toggle.addEventListener('change', (event) => flow.setVisible(event.target.checked));
  const layerSelect = el('flow-layer-select');
  if (layerSelect) {
    layerSelect.addEventListener('change', (event) => flow.setLayer(event.target.value));
  }
  const teamSelect = el('flow-team-select');
  if (teamSelect) {
    teamSelect.addEventListener('change', (event) => flow.setTeam(event.target.value));
  }
  const classSelect = el('flow-class-select');
  if (classSelect) {
    classSelect.addEventListener('change', (event) => flow.setClass(event.target.value));
  }
  const slider = el('flow-time-slider');
  if (slider) {
    slider.addEventListener('input', (event) => {
      const seconds = Number(event.target.value);
      const label = el('flow-time-label');
      if (label) {
        label.textContent = formatRaceTime(seconds);
      }
      flow.setTime(seconds);
    });
  }
  const particlesToggle = el('flow-particles-toggle');
  if (particlesToggle) {
    particlesToggle.addEventListener('change', (event) => flow.setParticles(event.target.checked));
  }
}

async function attachMap(ctrl, map, mapName, mapSize) {
  detach(ctrl);
  ctrl.leafletMap = map;
  ctrl.mapSize = mapSize;
  if (ctrl.mapName !== mapName) {
    ctrl.cache.clear();
    ctrl.emptyLayers.clear();
    ctrl.gamelayers = null;
  }
  ctrl.mapName = mapName;
  const token = ++ctrl.loadToken;
  let gamelayers = null;
  try {
    gamelayers = await probeFlow(mapName, fetch);
  } catch (error) {
    if (token !== ctrl.loadToken) {
      return;
    }
    console.error('Flow availability probe failed:', error);
  }
  if (token !== ctrl.loadToken) {
    return;
  }
  ctrl.gamelayers = gamelayers;
  ctrl.available = Boolean(
    gamelayers && Array.isArray(gamelayers.layers) && gamelayers.layers.length > 0);
  // A fresh map starts with the overlay off, matching the contour layer.
  ctrl.visible = false;
  ctrl.data = null;
  ctrl.layerId = pickDefaultLayer(ctrl);
  syncControls(ctrl);
}

function detach(ctrl) {
  ctrl.loadToken += 1;
  ctrl.renderScheduled = false;
  stopParticles(ctrl);
  removeOverlay(ctrl);
  ctrl.leafletMap = null;
  ctrl.data = null;
}

function pickDefaultLayer(ctrl) {
  if (!ctrl.available) {
    return null;
  }
  const ids = ctrl.gamelayers.layers.map((layer) => `${layer.mode}_${layer.size}`);
  return ids.includes(DEFAULT_LAYER) ? DEFAULT_LAYER : ids[0];
}

function setVisible(ctrl, visible) {
  ctrl.visible = visible;
  const options = el('flow-options');
  if (options) {
    options.style.display = visible ? '' : 'none';
  }
  if (!visible) {
    ctrl.loadToken += 1;
    stopParticles(ctrl);
    removeOverlay(ctrl);
    return;
  }
  reload(ctrl);
}

async function reload(ctrl) {
  if (!ctrl.visible || !ctrl.available || !ctrl.layerId || !ctrl.leafletMap) {
    return;
  }
  const token = ++ctrl.loadToken;
  const key = `${ctrl.mapName}/${ctrl.layerId}`;
  if (!ctrl.cache.has(key)) {
    ctrl.cache.set(key, loadLayerFields(ctrl.mapName, ctrl.layerId, fetch));
  }
  try {
    const data = await ctrl.cache.get(key);
    if (token !== ctrl.loadToken) {
      return;
    }
    ctrl.data = data;
    const hasAnyField = [1, 2].some(
      (team) => CLASS_VALUES.some((cls) => data.fields[team][cls]));
    if (!hasAnyField) {
      ctrl.emptyLayers.add(ctrl.layerId);
      disableLayerOption(ctrl.layerId);
      removeOverlay(ctrl);
      showNotice('Flow is not computed for this layer.');
      updateReadout(ctrl);
      return;
    }
    clearNotice();
    updateOptionStates(ctrl);
    updateProvenance(ctrl);
    updateReadout(ctrl);
    scheduleRender(ctrl);
    if (ctrl.particlesOn) {
      if (ctrl.particleSys) {
        spawnParticles(ctrl, ctrl.particleSys);
      } else {
        startParticles(ctrl);
      }
    }
  } catch (error) {
    if (token !== ctrl.loadToken) {
      return;
    }
    ctrl.cache.delete(key);
    console.error('Flow layer load failed:', error);
    showNotice('Flow data failed to load for this layer.');
  }
}

function scheduleRender(ctrl) {
  if (ctrl.renderScheduled) {
    return;
  }
  ctrl.renderScheduled = true;
  requestAnimationFrame(() => {
    ctrl.renderScheduled = false;
    renderNow(ctrl);
  });
}

function renderNow(ctrl) {
  if (!ctrl.visible || !ctrl.leafletMap || !ctrl.data) {
    return;
  }
  const f1 = ctrl.teamSel === '2' ? null : ctrl.data.fields[1][ctrl.classSel];
  const f2 = ctrl.teamSel === '1' ? null : ctrl.data.fields[2][ctrl.classSel];
  if (!f1 && !f2) {
    removeOverlay(ctrl);
    showNotice('No field for this team and class in this layer.');
    return;
  }
  clearNotice();
  const field = f1 || f2;
  ensureCanvas(ctrl, field.rows, field.cols);
  renderBands(f1, f2, {
    tSeconds: ctrl.tSeconds,
    deltaSeconds: CONTESTED_DELTA_SECONDS,
    bandSeconds: BAND_SECONDS,
    team1Visible: Boolean(f1),
    team2Visible: Boolean(f2)
  }, ctrl.imageData.data);
  ctrl.ctx.putImageData(ctrl.imageData, 0, 0);
  ensureOverlay(ctrl, field);
}

function ensureCanvas(ctrl, rows, cols) {
  if (ctrl.canvas && ctrl.canvas.width === cols && ctrl.canvas.height === rows) {
    return;
  }
  removeOverlay(ctrl);
  ctrl.canvas = document.createElement('canvas');
  ctrl.canvas.width = cols;
  ctrl.canvas.height = rows;
  ctrl.ctx = ctrl.canvas.getContext('2d');
  ctrl.imageData = ctrl.ctx.createImageData(cols, rows);
}

function ensureOverlay(ctrl, field) {
  if (ctrl.overlayLayer) {
    return;
  }
  const cell = field.cellSizeM || ctrl.mapSize / field.cols;
  // Row 0 is north: leafletLat = mapSize - repoY (same convention as app.js).
  const south = ctrl.mapSize - field.rows * cell;
  const east = field.cols * cell;
  const bounds = L.latLngBounds([[south, 0], [ctrl.mapSize, east]]);
  ctrl.overlayLayer = createCanvasOverlay(ctrl.canvas, bounds);
  ctrl.overlayLayer.addTo(ctrl.leafletMap);
}

function removeOverlay(ctrl) {
  if (ctrl.overlayLayer) {
    ctrl.overlayLayer.remove();
    ctrl.overlayLayer = null;
  }
}

function enableAllOptions(select) {
  for (const option of select.options) {
    option.disabled = false;
  }
}

function syncControls(ctrl) {
  const block = el('flow-controls');
  if (block) {
    block.style.display = ctrl.available ? '' : 'none';
  }
  if (!ctrl.available) {
    return;
  }
  const toggle = el('flow-layer-toggle');
  if (toggle) {
    toggle.checked = ctrl.visible;
  }
  const options = el('flow-options');
  if (options) {
    options.style.display = 'none';
  }
  const layerSelect = el('flow-layer-select');
  if (layerSelect) {
    layerSelect.innerHTML = '';
    for (const layer of ctrl.gamelayers.layers) {
      const id = `${layer.mode}_${layer.size}`;
      const option = document.createElement('option');
      option.value = id;
      option.textContent = `${layer.mode} ${layer.size}`;
      option.disabled = ctrl.emptyLayers.has(id);
      layerSelect.appendChild(option);
    }
    layerSelect.value = ctrl.layerId;
  }
  const teamSelect = el('flow-team-select');
  if (teamSelect) {
    enableAllOptions(teamSelect);
    teamSelect.value = 'both';
  }
  ctrl.teamSel = 'both';
  const classSelect = el('flow-class-select');
  if (classSelect) {
    enableAllOptions(classSelect);
    classSelect.value = 'infantry';
  }
  ctrl.classSel = 'infantry';
  const slider = el('flow-time-slider');
  if (slider) {
    slider.value = String(MAX_TIME_SECONDS);
  }
  ctrl.tSeconds = MAX_TIME_SECONDS;
  const timeLabel = el('flow-time-label');
  if (timeLabel) {
    timeLabel.textContent = formatRaceTime(MAX_TIME_SECONDS);
  }
  const scopeLabel = el('flow-scope-label');
  if (scopeLabel) {
    scopeLabel.title = '';
  }
  ctrl.particlesOn = false;
  const particlesToggle = el('flow-particles-toggle');
  if (particlesToggle) {
    particlesToggle.checked = false;
  }
  clearNotice();
  const readout = el('flow-race-readout');
  if (readout) {
    readout.innerHTML = '';
  }
}

function updateOptionStates(ctrl) {
  if (!ctrl.data) {
    return;
  }
  const has = (team, cls) => Boolean(ctrl.data.fields[team] && ctrl.data.fields[team][cls]);
  const classSelect = el('flow-class-select');
  if (classSelect) {
    for (const option of classSelect.options) {
      option.disabled = !has(1, option.value) && !has(2, option.value);
    }
    const selected = classSelect.selectedOptions[0];
    if (selected && selected.disabled) {
      const first = Array.from(classSelect.options).find((option) => !option.disabled);
      if (first) {
        classSelect.value = first.value;
        ctrl.classSel = first.value;
      }
    }
  }
  const teamSelect = el('flow-team-select');
  if (teamSelect) {
    for (const option of teamSelect.options) {
      option.disabled = option.value !== 'both' && !has(Number(option.value), ctrl.classSel);
    }
    const selected = teamSelect.selectedOptions[0];
    if (selected && selected.disabled) {
      teamSelect.value = 'both';
      ctrl.teamSel = 'both';
    }
  }
}

function updateProvenance(ctrl) {
  const label = el('flow-scope-label');
  if (!label) {
    return;
  }
  const sidecars = (ctrl.data && ctrl.data.sidecars) || {};
  const preferredTeam = ctrl.teamSel === '2' ? 2 : 1;
  const sidecar = sidecars[`team${preferredTeam}/${ctrl.classSel}`] || Object.values(sidecars)[0];
  label.title = sidecar
    ? `Speed ${sidecar.speed_ms} m/s (${sidecar.terrain_profile}) - ${sidecar.speed_provenance}`
    : '';
}

function updateReadout(ctrl) {
  const box = el('flow-race-readout');
  if (!box) {
    return;
  }
  const doc = ctrl.data && ctrl.data.raceTimes;
  if (!doc || !Array.isArray(doc.control_points) || doc.control_points.length === 0) {
    box.innerHTML = '<small>No race data for this layer.</small>';
    return;
  }
  const rows = buildRaceReadout(doc, 1);
  box.innerHTML = rows.map((row) => {
    let edge = '';
    if (row.deltaSeconds === 0) {
      edge = ' (even)';
    } else if (row.deltaSeconds !== null) {
      const faster = row.deltaSeconds < 0 ? 'T1' : 'T2';
      edge = ` (${faster} earlier by ${formatRaceTime(Math.abs(row.deltaSeconds))})`;
    }
    return `<div><small>${escapeHtml(shortCpName(row.name, ctrl.mapName))}: `
      + `T1 ${formatRaceTime(row.youSeconds)}, T2 ${formatRaceTime(row.enemySeconds)}`
      + `${edge}</small></div>`;
  }).join('');
}

function disableLayerOption(layerId) {
  const select = el('flow-layer-select');
  if (!select) {
    return;
  }
  for (const option of select.options) {
    if (option.value === layerId) {
      option.disabled = true;
    }
  }
}

function showNotice(message) {
  const notice = el('flow-notice');
  if (!notice) {
    return;
  }
  notice.style.display = '';
  if (notice.firstElementChild) {
    notice.firstElementChild.textContent = message;
  }
}

function clearNotice() {
  const notice = el('flow-notice');
  if (notice) {
    notice.style.display = 'none';
  }
}

// ---------------------------------------------------------------------------
// Particle advection (presentation only; off by default)
// ---------------------------------------------------------------------------

/** Fields the particles ride on, per the current team/class selection. */
function particleFields(ctrl) {
  if (!ctrl.data) {
    return [];
  }
  const teams = ctrl.teamSel === 'both' ? [1, 2] : [Number(ctrl.teamSel)];
  return teams
    .map((team) => ({ team, field: ctrl.data.fields[team][ctrl.classSel] }))
    .filter((entry) => entry.field);
}

/** Central-difference gradient direction (negative: toward earlier arrival). */
function gradientAt(field, row, col) {
  const { rows, cols, bytes, quantumS, cellSizeM } = field;
  if (row < 1 || col < 1 || row >= rows - 1 || col >= cols - 1) {
    return null;
  }
  const center = bytes[row * cols + col];
  const left = bytes[row * cols + col - 1];
  const right = bytes[row * cols + col + 1];
  const up = bytes[(row - 1) * cols + col];
  const down = bytes[(row + 1) * cols + col];
  if ([center, left, right, up, down].includes(255)) {
    return null;
  }
  const gx = (right - left) * quantumS / (2 * cellSizeM);
  const gy = (down - up) * quantumS / (2 * cellSizeM);
  const mag = Math.hypot(gx, gy);
  if (mag < 1e-9) {
    // Flat cell (near sources): drift in a random direction.
    const angle = Math.random() * Math.PI * 2;
    return [Math.cos(angle), Math.sin(angle)];
  }
  return [-gx / mag, -gy / mag];
}

function respawnParticle(ctrl, particle, fields) {
  const entry = fields[Math.floor(Math.random() * fields.length)];
  particle.team = entry.team;
  const { field } = entry;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const row = Math.floor(Math.random() * field.rows);
    const col = Math.floor(Math.random() * field.cols);
    const value = field.bytes[row * field.cols + col];
    if (value !== 255 && value * field.quantumS <= ctrl.tSeconds) {
      particle.x = (col + 0.5) * field.cellSizeM;
      particle.y = (row + 0.5) * field.cellSizeM;
      particle.age = 0;
      particle.maxAge = 3 + Math.random() * 5;
      return;
    }
  }
  // Field mostly unreachable at this t: park offscreen and retry soon.
  particle.x = -1e9;
  particle.y = -1e9;
  particle.age = 0;
  particle.maxAge = 0.5;
}

function spawnParticles(ctrl, sys) {
  const fields = particleFields(ctrl);
  sys.list = [];
  if (!fields.length) {
    return;
  }
  for (let i = 0; i < PARTICLE_COUNT; i += 1) {
    const particle = {};
    respawnParticle(ctrl, particle, fields);
    sys.list.push(particle);
  }
}

function stepParticle(ctrl, sys, particle, fields, dt) {
  const entry = fields.find((candidate) => candidate.team === particle.team) || fields[0];
  const { field } = entry;
  particle.age += dt;
  if (particle.age > particle.maxAge || particle.x < -1e8) {
    respawnParticle(ctrl, particle, fields);
    return;
  }
  const direction = gradientAt(field, Math.floor(particle.y / field.cellSizeM),
    Math.floor(particle.x / field.cellSizeM));
  if (!direction) {
    respawnParticle(ctrl, particle, fields);
    return;
  }
  const jitter = 20; // cosmetic data-space noise, m/s
  const nx = particle.x + (direction[0] * PARTICLE_SPEED_MS + (Math.random() - 0.5) * jitter) * dt;
  const ny = particle.y + (direction[1] * PARTICLE_SPEED_MS + (Math.random() - 0.5) * jitter) * dt;
  const map = ctrl.leafletMap;
  // Repo world meters -> Leaflet container point ([lat,lng] = [mapSize - y, x]).
  const from = map.latLngToContainerPoint([ctrl.mapSize - particle.y, particle.x]);
  const to = map.latLngToContainerPoint([ctrl.mapSize - ny, nx]);
  const w = sys.canvas.width;
  const h = sys.canvas.height;
  if (to.x < 0 || to.y < 0 || to.x > w || to.y > h) {
    respawnParticle(ctrl, particle, fields);
    return;
  }
  sys.ctx.strokeStyle = entry.team === 1 ? 'rgba(59,130,246,0.9)' : 'rgba(249,115,22,0.9)';
  sys.ctx.lineWidth = 1.5;
  sys.ctx.beginPath();
  sys.ctx.moveTo(from.x, from.y);
  sys.ctx.lineTo(to.x, to.y);
  sys.ctx.stroke();
  particle.x = nx;
  particle.y = ny;
}

function particleTick(ctrl, sys, timestamp) {
  if (!sys.running) {
    return;
  }
  const dt = Math.min(0.05, (timestamp - (sys.lastTs || timestamp)) / 1000);
  sys.lastTs = timestamp;
  const map = ctrl.leafletMap;
  if (!map) {
    stopParticles(ctrl);
    return;
  }
  // Keep the viewport-sized canvas aligned with the visible map area.
  L.DomUtil.setPosition(sys.canvas, map.containerPointToLayerPoint([0, 0]));
  // Fade existing trails toward transparent (destination-out keeps the
  // canvas transparent instead of darkening the map beneath).
  sys.ctx.globalCompositeOperation = 'destination-out';
  sys.ctx.fillStyle = `rgba(0,0,0,${TRAIL_FADE_ALPHA})`;
  sys.ctx.fillRect(0, 0, sys.canvas.width, sys.canvas.height);
  sys.ctx.globalCompositeOperation = 'source-over';
  const fields = particleFields(ctrl);
  if (fields.length) {
    for (const particle of sys.list) {
      stepParticle(ctrl, sys, particle, fields, dt);
    }
  }
  sys.rafId = requestAnimationFrame((next) => particleTick(ctrl, sys, next));
}

function createParticleLayer(sys) {
  const ParticleLayer = L.Layer.extend({
    onAdd(map) {
      const size = map.getSize();
      sys.canvas.width = size.x;
      sys.canvas.height = size.y;
      sys.canvas.style.position = 'absolute';
      sys.canvas.style.pointerEvents = 'none';
      map.getPanes().overlayPane.appendChild(sys.canvas);
      sys.resizeHandler = () => {
        const next = map.getSize();
        sys.canvas.width = next.x;
        sys.canvas.height = next.y;
      };
      sys.clearHandler = () => {
        sys.ctx.clearRect(0, 0, sys.canvas.width, sys.canvas.height);
      };
      map.on('resize', sys.resizeHandler);
      map.on('movestart', sys.clearHandler);
    },
    onRemove(map) {
      map.off('resize', sys.resizeHandler);
      map.off('movestart', sys.clearHandler);
      sys.canvas.remove();
    }
  });
  return new ParticleLayer();
}

function startParticles(ctrl) {
  if (ctrl.particleSys) {
    return;
  }
  if (!ctrl.visible || !ctrl.leafletMap || !ctrl.data || !particleFields(ctrl).length) {
    ctrl.particlesOn = false;
    const toggle = el('flow-particles-toggle');
    if (toggle) {
      toggle.checked = false;
    }
    return;
  }
  const sys = {
    canvas: document.createElement('canvas'),
    ctx: null,
    layer: null,
    rafId: 0,
    list: [],
    running: true,
    lastTs: 0,
    resizeHandler: null,
    clearHandler: null,
    visibilityHandler: null
  };
  sys.ctx = sys.canvas.getContext('2d');
  ctrl.particleSys = sys;
  sys.layer = createParticleLayer(sys);
  sys.layer.addTo(ctrl.leafletMap);
  sys.visibilityHandler = () => {
    if (document.hidden) {
      cancelAnimationFrame(sys.rafId);
      sys.rafId = 0;
      sys.lastTs = 0;
    } else if (sys.running && !sys.rafId) {
      sys.rafId = requestAnimationFrame((ts) => particleTick(ctrl, sys, ts));
    }
  };
  document.addEventListener('visibilitychange', sys.visibilityHandler);
  spawnParticles(ctrl, sys);
  sys.rafId = requestAnimationFrame((ts) => particleTick(ctrl, sys, ts));
}

function stopParticles(ctrl) {
  const sys = ctrl.particleSys;
  if (!sys) {
    return;
  }
  sys.running = false;
  cancelAnimationFrame(sys.rafId);
  sys.rafId = 0;
  document.removeEventListener('visibilitychange', sys.visibilityHandler);
  if (sys.layer && ctrl.leafletMap) {
    ctrl.leafletMap.removeLayer(sys.layer);
  }
  sys.canvas.remove();
  sys.list = [];
  ctrl.particleSys = null;
}
