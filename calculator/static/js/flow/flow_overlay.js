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
  formatDuration,
  formatRaceTime,
  loadLayerFields,
  objectiveMarkers,
  probeFlow,
  renderBands,
  FLOW_CLASSES
} from './flow_core.js';

const DEFAULT_LAYER = 'gpm_cq_64';
const MAX_TIME_SECONDS = 600;
const CONTESTED_DELTA_SECONDS = 30;
const TEAM_VALUES = ['both', '1', '2'];
const CLASS_VALUES = FLOW_CLASSES;
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
    active: false,
    sizeCompatible: true,
    layerId: null,
    teamSel: 'both',
    classSel: 'infantry',
    tSeconds: MAX_TIME_SECONDS,
    data: null,
    emptyLayers: new Set(),
    particlesOn: false,
    particleSys: null,
    loadToken: 0,
    probeToken: 0,
    canvas: null,
    ctx: null,
    imageData: null,
    overlayLayer: null,
    objectiveGroup: null,
    renderId: 0,
    motionQuery: null,
    lifecycleHandler: null,
    cache: new Map()
  };

  return {
    attachMap: (map, mapName, mapSize, originalSize = mapSize) => attachMap(ctrl, map, mapName, mapSize, originalSize),
    detach: () => detach(ctrl),
    setActive: (active) => {
      ctrl.active = Boolean(active);
      reconcileVisibility(ctrl);
    },
    setVisible: (visible) => setVisible(ctrl, visible),
    setLayer: (layerId) => {
      if (ctrl.layerId !== layerId) {
        ctrl.layerId = layerId;
        refreshObjectives(ctrl);
        clearNotice();
        clearReadout();
        reload(ctrl);
      }
    },
    setTeam: (sel) => {
      if (TEAM_VALUES.includes(sel) && ctrl.teamSel !== sel) {
        ctrl.teamSel = sel;
        stopParticles(ctrl);
        updateReadout(ctrl);
        updateProvenance(ctrl);
        scheduleRender(ctrl);
        startParticles(ctrl);
      }
    },
    setClass: (cls) => {
      if (CLASS_VALUES.includes(cls) && ctrl.classSel !== cls) {
        ctrl.classSel = cls;
        stopParticles(ctrl);
        ctrl.loadToken += 1;
        ctrl.data = null;
        removeOverlay(ctrl);
        clearReadout();
        updateOptionStates(ctrl);
        updateProvenance(ctrl);
        reload(ctrl);
      }
    },
    setTime: (seconds) => {
      ctrl.tSeconds = Math.max(0, Math.min(MAX_TIME_SECONDS, seconds));
      scheduleRender(ctrl);
    },
    setParticles: (enabled) => {
      ctrl.particlesOn = Boolean(enabled);
      updateMotionStatus(ctrl);
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

async function attachMap(ctrl, map, mapName, mapSize, originalSize) {
  detach(ctrl);
  ctrl.leafletMap = map;
  ctrl.mapSize = mapSize;
  ctrl.sizeCompatible = mapSize === originalSize;
  ctrl.motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)') || null;
  ctrl.lifecycleHandler = () => {
    stopParticles(ctrl);
    startParticles(ctrl);
    updateMotionStatus(ctrl);
  };
  ctrl.motionQuery?.addEventListener?.('change', ctrl.lifecycleHandler);
  document.addEventListener('visibilitychange', ctrl.lifecycleHandler);
  updateMotionStatus(ctrl);
  if (ctrl.mapName !== mapName) {
    ctrl.cache.clear();
    ctrl.emptyLayers.clear();
    ctrl.gamelayers = null;
  }
  ctrl.mapName = mapName;
  const token = ++ctrl.probeToken;
  let gamelayers = null;
  try {
    gamelayers = await probeFlow(mapName, fetch);
  } catch (error) {
    if (token !== ctrl.probeToken) {
      return;
    }
    console.error('Flow availability probe failed:', error);
  }
  if (token !== ctrl.probeToken) {
    return;
  }
  ctrl.gamelayers = gamelayers;
  ctrl.available = Boolean(
    gamelayers && Array.isArray(gamelayers.layers) && gamelayers.layers.length > 0);
  ctrl.data = null;
  const ids = gamelayers?.layers?.map((layer) => `${layer.mode}_${layer.size}`) || [];
  if (!ids.includes(ctrl.layerId)) ctrl.layerId = pickDefaultLayer(ctrl);
  syncControls(ctrl);
  reconcileVisibility(ctrl);
}

function detach(ctrl) {
  ctrl.loadToken += 1;
  ctrl.probeToken += 1;
  cancelRender(ctrl);
  ctrl.motionQuery?.removeEventListener?.('change', ctrl.lifecycleHandler);
  document.removeEventListener('visibilitychange', ctrl.lifecycleHandler);
  stopParticles(ctrl);
  removeOverlay(ctrl);
  removeObjectives(ctrl);
  ctrl.leafletMap = null;
  ctrl.data = null;
  ctrl.available = false;
  clearReadout();
}

function pickDefaultLayer(ctrl) {
  if (!ctrl.available) {
    return null;
  }
  const ids = ctrl.gamelayers.layers.map((layer) => `${layer.mode}_${layer.size}`);
  return ids.includes(DEFAULT_LAYER) ? DEFAULT_LAYER : ids[0];
}

function setVisible(ctrl, visible) {
  ctrl.visible = Boolean(visible);
  const options = el('flow-options');
  if (options) {
    options.style.display = visible ? '' : 'none';
  }
  reconcileVisibility(ctrl);
}

function isShowing(ctrl) {
  return ctrl.active && ctrl.visible && ctrl.available && ctrl.sizeCompatible && ctrl.leafletMap;
}

function reconcileVisibility(ctrl) {
  refreshObjectives(ctrl);
  if (!isShowing(ctrl)) {
    ctrl.loadToken += 1;
    cancelRender(ctrl);
    stopParticles(ctrl);
    removeOverlay(ctrl);
    clearReadout();
    removeObjectives(ctrl);
    if (!ctrl.sizeCompatible) showNotice('Flow is disabled: restore Auto map size to match artifact coordinates.');
    return;
  }
  if (ctrl.data) {
    scheduleRender(ctrl);
    startParticles(ctrl);
  } else reload(ctrl);
}

async function reload(ctrl) {
  const token = ++ctrl.loadToken;
  ctrl.data = null;
  cancelRender(ctrl);
  removeOverlay(ctrl);
  stopParticles(ctrl);
  clearReadout();
  if (!isShowing(ctrl) || !ctrl.layerId) return;
  const key = `${ctrl.mapName}/${ctrl.layerId}/${ctrl.classSel}`;
  if (!ctrl.cache.has(key)) {
    ctrl.cache.set(key, loadLayerFields(ctrl.mapName, ctrl.layerId, fetch));
  }
  try {
    const data = await ctrl.cache.get(key);
    if (token !== ctrl.loadToken || !isShowing(ctrl)) {
      return;
    }
    const fields = Object.values(data.fields).flatMap((classes) => Object.values(classes)).filter(Boolean);
    if (fields.some((field) => !Number.isFinite(field.cellSizeM)
      || Math.abs(field.cols * field.cellSizeM - ctrl.mapSize) > 0.01
      || Math.abs(field.rows * field.cellSizeM - ctrl.mapSize) > 0.01)) {
      ctrl.sizeCompatible = false;
      reconcileVisibility(ctrl);
      return;
    }
    ctrl.data = data;
    updateOptionStates(ctrl);
    const hasAnyField = [1, 2].some((team) => data.fields[team][ctrl.classSel]);
    if (!hasAnyField) {
      ctrl.emptyLayers.add(ctrl.layerId);
      removeOverlay(ctrl);
      clearReadout();
      showNotice(emptyStateMessage(ctrl));
      updateReadout(ctrl);
      return;
    }
    clearNotice();
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
  if (ctrl.renderId || !isShowing(ctrl)) {
    return;
  }
  const token = ctrl.loadToken;
  ctrl.renderId = requestAnimationFrame(() => {
    ctrl.renderId = 0;
    if (token !== ctrl.loadToken) return;
    renderNow(ctrl);
  });
}

function cancelRender(ctrl) {
  cancelAnimationFrame(ctrl.renderId);
  ctrl.renderId = 0;
}

function clearReadout() {
  const box = el('flow-race-readout');
  if (box) box.textContent = '';
  const label = el('flow-scope-label');
  if (label) label.title = '';
  const provenance = el('flow-provenance');
  if (provenance) provenance.textContent = '';
}

function renderNow(ctrl) {
  if (!isShowing(ctrl) || !ctrl.data) {
    return;
  }
  const f1 = ctrl.teamSel === '2' ? null : ctrl.data.fields[1][ctrl.classSel];
  const f2 = ctrl.teamSel === '1' ? null : ctrl.data.fields[2][ctrl.classSel];
  if (!f1 && !f2) {
    removeOverlay(ctrl);
    showNotice(emptyStateMessage(ctrl));
    return;
  }
  clearNotice();
  const field = f1 || f2;
  ensureCanvas(ctrl, field.rows, field.cols);
  renderBands(f1, f2, {
    tSeconds: ctrl.tSeconds,
    deltaSeconds: CONTESTED_DELTA_SECONDS,
    team1Visible: Boolean(f1),
    team2Visible: Boolean(f2)
  }, ctrl.imageData.data);
  ctrl.ctx.putImageData(ctrl.imageData, 0, 0);
  ensureOverlay(ctrl, field);
}

function selectedGameLayer(ctrl) {
  return ctrl.gamelayers?.layers?.find((layer) => `${layer.mode}_${layer.size}` === ctrl.layerId) || null;
}

function refreshObjectives(ctrl) {
  removeObjectives(ctrl);
  if (!isShowing(ctrl) || !ctrl.layerId) return;
  const records = objectiveMarkers(selectedGameLayer(ctrl), ctrl.mapSize);
  if (!records.length) return;
  ctrl.objectiveGroup = L.layerGroup();
  records.forEach((record) => {
    const teamClass = record.team === 1 ? 'team1' : record.team === 2 ? 'team2' : record.team === 0 ? 'neutral' : 'unknown';
    const label = escapeHtml(shortCpName(record.name, ctrl.mapName));
    const icon = L.divIcon({
      className: `flow-objective flow-objective--${teamClass}`,
      html: `<span aria-hidden="true">${record.team || '?'}</span>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
    const marker = L.marker(record.leaflet, {
      icon,
      bubblingMouseEvents: false,
      keyboard: true,
      title: `${shortCpName(record.name, ctrl.mapName)} (control point ${record.cpId})`,
      alt: `${shortCpName(record.name, ctrl.mapName)} (control point ${record.cpId})`
    });
    marker.bindTooltip(label, { direction: 'top', offset: [0, -10] });
    // Keep exact coordinates; a popup and persistent list expose every overlap.
    const coincident = records.filter((other) => other.x === record.x && other.y === record.y);
    marker.bindPopup(coincident.map((other) => `${escapeHtml(shortCpName(other.name, ctrl.mapName))} (CP ${escapeHtml(other.cpId)})`).join('<br>'));
    marker.on('click', (event) => {
      if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
    });
    marker.addTo(ctrl.objectiveGroup);
  });
  ctrl.objectiveGroup.addTo(ctrl.leafletMap);
  const list = el('flow-objectives');
  if (list) list.innerHTML = records.map((record) => `<li>${escapeHtml(shortCpName(record.name, ctrl.mapName))} (CP ${escapeHtml(record.cpId)}, ${record.team === null ? 'unknown team' : record.team === 0 ? 'neutral' : `team ${record.team}`})</li>`).join('');
}

function removeObjectives(ctrl) {
  if (ctrl.objectiveGroup && ctrl.leafletMap) {
    ctrl.leafletMap.removeLayer(ctrl.objectiveGroup);
  }
  ctrl.objectiveGroup = null;
  const list = el('flow-objectives');
  if (list) list.textContent = '';
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
    options.style.display = ctrl.visible ? '' : 'none';
  }
  const layerSelect = el('flow-layer-select');
  if (layerSelect) {
    layerSelect.innerHTML = '';
    for (const layer of ctrl.gamelayers.layers) {
      const id = `${layer.mode}_${layer.size}`;
      const option = document.createElement('option');
      option.value = id;
      option.textContent = `${layer.mode} ${layer.size}`;
      layerSelect.appendChild(option);
    }
    layerSelect.value = ctrl.layerId;
  }
  const teamSelect = el('flow-team-select');
  if (teamSelect) {
    enableAllOptions(teamSelect);
    teamSelect.value = ctrl.teamSel;
  }
  const classSelect = el('flow-class-select');
  if (classSelect) {
    enableAllOptions(classSelect);
    classSelect.value = ctrl.classSel;
  }
  const slider = el('flow-time-slider');
  if (slider) {
    slider.value = String(ctrl.tSeconds);
  }
  const timeLabel = el('flow-time-label');
  if (timeLabel) {
    timeLabel.textContent = formatRaceTime(ctrl.tSeconds);
  }
  const scopeLabel = el('flow-scope-label');
  if (scopeLabel) {
    scopeLabel.title = '';
  }
  const particlesToggle = el('flow-particles-toggle');
  if (particlesToggle) {
    particlesToggle.checked = ctrl.particlesOn;
  }
  updateMotionStatus(ctrl);
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
  const reasonLine = el('flow-class-reason');
  const statusText = {
    available: 'Available',
    no_source: 'No selected source',
    unsupported_data: 'Unsupported source data',
    unsupported_model: 'Unsupported vehicle model',
    not_computed: 'Not computed for this layer',
    unreachable: 'No reachable route for this class',
    no_confirmed_water: 'No confirmed water on this map',
    water_below_min_area: 'Confirmed water is below the minimum launch area',
    off_confirmed_water: 'Source is not on confirmed water',
    corrupt_artifact: 'Flow data failed validation'
  };
  if (classSelect) {
    for (const option of classSelect.options) {
      const base = option.value === 'infantry' ? 'Infantry (walk/sprint)'
        : { car: 'Car', truck_wheeled: 'Truck (wheeled)', tracked: 'Tracked', boat: 'Boat', helicopter: 'Helicopter' }[option.value];
      const statuses = ctrl.data.manifest?.availability?.[option.value];
      const reasons = ctrl.data.formatVersion === '2.0' && statuses
        ? [...new Set(Object.values(statuses).map((status) => statusText[status] || 'Unavailable'))]
        : ['Not computed for this layer'];
      const reason = reasons.join('; ');
      const available = has(1, option.value) || has(2, option.value);
      option.disabled = false;
      option.title = reason;
      option.textContent = `${base || option.value} — ${available ? 'Available' : reason}`;
      if (option.value === ctrl.classSel && reasonLine) reasonLine.textContent = available ? '' : reason;
    }
  }
  if (reasonLine && classSelect?.selectedOptions[0] &&
      (has(1, ctrl.classSel) || has(2, ctrl.classSel))) reasonLine.textContent = '';
  const teamSelect = el('flow-team-select');
  if (teamSelect) {
    for (const option of teamSelect.options) {
      option.disabled = option.value !== 'both' && !has(Number(option.value), ctrl.classSel);
    }
  }
}

export function bridgeProvenanceLabel(bridge = {}) {
  const candidate = bridge.unverified ? 'Candidate deck route; unverified. ' : '';
  const unrouted = Number(bridge.unrouted_count || 0);
  const detected = unrouted > 0
    ? `${unrouted} detected bridge geometry item(s) not routed. ` : '';
  return `${candidate}${detected}`;
}

function updateMotionStatus(ctrl) {
  const status = el('flow-motion-status');
  if (status) {
    status.textContent = ctrl.motionQuery?.matches
      ? 'Your system requests reduced motion; particle animation is disabled. Static flow remains available.' : '';
  }
}

function updateProvenance(ctrl) {
  const label = el('flow-scope-label');
  if (!label) {
    return;
  }
  const sidecars = (ctrl.data && ctrl.data.sidecars) || {};
  const preferredTeam = ctrl.teamSel === '2' ? 2 : 1;
  const sidecar = sidecars[`team${preferredTeam}/${ctrl.classSel}`];
  const block = el('flow-provenance');
  if (block) {
    if (!sidecar) {
      block.textContent = '';
    } else {
      const sources = Array.isArray(sidecar.source_spawners)
        ? sidecar.source_spawners.length : sidecar.source_count;
      const synthetic = sidecar.source_type === 'synthetic_water_launch'
        || sidecar.source_spawners?.some((source) => source.source_type === 'synthetic_water_launch');
      const warning = sidecar.speed_provenance?.text || sidecar.speed_provenance || '';
      const bridgeWarning = bridgeProvenanceLabel(sidecar.bridge);
      block.textContent = `Sources: ${sources || 0}. ${bridgeWarning}${synthetic ? 'Estimated boat launch point; ' : ''}${warning}`;
    }
  }
  const speedProvenance = sidecar?.speed_provenance?.text
    || sidecar?.speed_provenance
    || '';
  label.title = sidecar
    ? `Speed ${sidecar.speed_ms} m/s (${sidecar.terrain_profile}) - ${speedProvenance}`
    : '';
}

function emptyStateMessage(ctrl) {
  const className = {
    infantry: 'Infantry',
    car: 'Car',
    truck_wheeled: 'Truck',
    tracked: 'Tracked',
    boat: 'Boat',
    helicopter: 'Helicopter'
  }[ctrl.classSel] || ctrl.classSel;
  const status = ctrl.data?.manifest?.availability?.[ctrl.classSel];
  const reason = status ? [...new Set(Object.values(status))].join(', ') : 'not computed for this layer';
  return `${className} flow is unavailable for ${ctrl.layerId || 'this layer'} (${ctrl.teamSel === 'both' ? 'both teams' : `Team ${ctrl.teamSel}`}); reason: ${reason}.`;
}

function updateReadout(ctrl) {
  const box = el('flow-race-readout');
  if (!box) {
    return;
  }
  const doc = ctrl.data && ctrl.data.raceTimes;
  if (!doc || (doc.format_version !== '2.0'
    && (!Array.isArray(doc.control_points) || doc.control_points.length === 0))) {
    box.innerHTML = '<small>No race data for this layer.</small>';
    return;
  }
  const rows = buildRaceReadout(doc.format_version === '2.0'
    ? { ...doc, selectedClass: ctrl.classSel } : doc, 1);
  box.innerHTML = `${doc.format_version === '2.0' ? '' : '<small>Legacy pooled minimum across classes (not selected-class times).</small>'}` + rows.map((row) => {
    let edge = '';
    if (row.deltaSeconds === 0) {
      edge = ' (even)';
    } else if (row.deltaSeconds !== null) {
      const faster = row.deltaSeconds < 0 ? 'T1' : 'T2';
      edge = ` (${faster} earlier by ${formatDuration(Math.abs(row.deltaSeconds))})`;
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
  if (!sys.running || ctrl.particleSys !== sys || !canAnimate(ctrl)) {
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

function canAnimate(ctrl) {
  return isShowing(ctrl) && ctrl.particlesOn && !document.hidden
    && !ctrl.motionQuery?.matches && particleFields(ctrl).length > 0;
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
  if (ctrl.particleSys || !canAnimate(ctrl)) return;
  const sys = {
    canvas: document.createElement('canvas'),
    ctx: null,
    layer: null,
    rafId: 0,
    list: [],
    running: true,
    lastTs: 0,
    resizeHandler: null,
    clearHandler: null
  };
  sys.ctx = sys.canvas.getContext('2d');
  ctrl.particleSys = sys;
  sys.layer = createParticleLayer(sys);
  sys.layer.addTo(ctrl.leafletMap);
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
  if (sys.layer && ctrl.leafletMap) {
    ctrl.leafletMap.removeLayer(sys.layer);
  }
  sys.canvas.remove();
  sys.list = [];
  ctrl.particleSys = null;
}
