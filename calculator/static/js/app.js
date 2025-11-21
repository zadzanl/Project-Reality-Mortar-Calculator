/**
 * Project Reality Mortar Calculator - Main Application
 * Orchestrates UI, map display, and calculation modules
 */

import { calculateFiringSolution, PR_PHYSICS } from './ballistics.js';
import { gridToXY, formatGridReference, xyToGrid, gridRefToXY, calculateGridScale, getRowLabelCenterX } from './coordinates.js';
import { loadMapData } from './heightmap.js';

// ====================================
// APPLICATION STATE
// ====================================

const state = {
  currentMap: null,
  mapData: null,
  leafletMap: null,
  mortarMarker: null,
  targetMarker: null,
  pathLine: null,
  // Store precise marker coordinates (not rounded to grid)
  mortarPreciseXY: null,  // { x: number, y: number } in meters
  targetPreciseXY: null   // { x: number, y: number } in meters
};

// Overlay layers
state.gridGroup = null;
state.gridLabelGroup = null;
state.rangeCircle = null;

// ====================================
// INITIALIZATION
// ====================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('PR Mortar Calculator initializing...');
  
  // Fix Leaflet icon paths
  fixLeafletIconPaths();
  
  // Load available maps
  await loadAvailableMaps();
  
  // Set up event listeners
  setupEventListeners();
  
  console.log('Application ready');
});

// ====================================
// MAP LOADING
// ====================================

async function loadAvailableMaps() {
  const dropdown = document.getElementById('map-dropdown');
  const loadBtn = document.getElementById('load-map-btn');
  
  try {
    const response = await fetch('/maps/list');
    const data = await response.json();
    
    if (data.maps && data.maps.length > 0) {
      dropdown.innerHTML = '<option value="">Select a map...</option>';
      
      data.maps.forEach(map => {
        const option = document.createElement('option');
        option.value = map.path;
        option.textContent = formatMapName(map.name);
        dropdown.appendChild(option);
      });
      
      dropdown.disabled = false;
      
      // Restore last selected map if available
      const lastMap = localStorage.getItem('pr_last_map');
      if (lastMap) {
        dropdown.value = lastMap;
        document.getElementById('load-map-btn').disabled = !dropdown.value;
      }
      console.log(`Loaded ${data.maps.length} maps`);
    } else {
      dropdown.innerHTML = '<option value="">No maps available</option>';
      console.warn('No maps found in processed_maps directory');
    }
  } catch (error) {
    console.error('Failed to load maps:', error);
    dropdown.innerHTML = '<option value="">Error loading maps</option>';
  }
}

async function loadSelectedMap() {
  const dropdown = document.getElementById('map-dropdown');
  const mapName = dropdown.value;
  
  if (!mapName) {
    alert('Please select a map');
    return;
  }
  
  try {
    // Show loading state
    document.getElementById('map-loading').innerHTML = '<p>Loading map data...</p>';
    
    // Load map data
    state.mapData = await loadMapData(mapName);
    state.currentMap = mapName;
    
    // Store original map size for override reset
    state.originalMapSize = state.mapData.metadata.map_size;
    
    // Reset map size override dropdown to auto
    document.getElementById('map-size-override').value = 'auto';
    
    // Reset precise coordinates
    state.mortarPreciseXY = null;
    state.targetPreciseXY = null;
    
    console.log('Map loaded:', mapName);
    console.log('Map metadata:', state.mapData.metadata);
    
    // Initialize Leaflet map
    initializeLeafletMap();
    
    // Enable calculate button
    document.getElementById('calculate-btn').disabled = false;

    // Remember last selected map for convenience
    try { localStorage.setItem('pr_last_map', mapName); } catch (e) { /* ignore */ }
    
    // Update grid displays
    updateGridDisplays();
    
    // Reset results to initial state
    resetResults();
    
    // Hide loading message
    document.getElementById('map-loading').style.display = 'none';
    
  } catch (error) {
    console.error('Failed to load map:', error);
    alert(`Failed to load map: ${error.message}`);
    document.getElementById('map-loading').innerHTML = '<p>Error loading map. Please try again.</p>';
  }
}

// ====================================
// LEAFLET MAP INITIALIZATION
// ====================================

function initializeLeafletMap() {
  const mapContainer = document.getElementById('map');
  const metadata = state.mapData.metadata;
  
  // Remove existing map if any
  if (state.leafletMap) {
    state.leafletMap.remove();
    // Clear all marker and layer references
    state.mortarMarker = null;
    state.targetMarker = null;
    state.pathLine = null;
    state.gridGroup = null;
    state.gridLabelGroup = null;
    state.rangeCircle = null;
  }
  
  // Create Leaflet map with Simple CRS (non-geographic coordinates)
  state.leafletMap = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -2,
    maxZoom: 2,
    attributionControl: false
  });
  
  // Calculate bounds for the map
  const mapSize = metadata.map_size;
  const bounds = [[0, 0], [mapSize, mapSize]];
  
  // Add a simple background (will be replaced with actual map imagery in future)
  const imageUrl = `/maps/${state.currentMap}/minimap.png`;
  
  // Try to load minimap, fallback to colored rectangle
  const img = new Image();
  img.onload = () => {
    L.imageOverlay(imageUrl, bounds).addTo(state.leafletMap);
  };
  img.onerror = () => {
    // Fallback: Draw a simple colored rectangle
    console.warn('Minimap not found, using placeholder');
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#d4c4a0';
    ctx.fillRect(0, 0, 512, 512);
    
    // Add grid pattern
    ctx.strokeStyle = '#a89070';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 13; i++) {
      const pos = (i / 13) * 512;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, 512);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(512, pos);
      ctx.stroke();
    }
    
    L.imageOverlay(canvas.toDataURL(), bounds).addTo(state.leafletMap);
    // Add an overlay label to indicate minimap not available
    const overlay = L.control({ position: 'topright' });
    overlay.onAdd = function () {
      const div = L.DomUtil.create('div', 'minimap-overlay');
      div.innerHTML = `<div class="minimap-overlay__content">No minimap available<br/><strong>${formatMapName(state.currentMap || '')}</strong></div>`;
      return div;
    };
    overlay.addTo(state.leafletMap);
  };
  img.src = imageUrl;
  
  // Set view to map center
  state.leafletMap.fitBounds(bounds);
  
  // Add grid overlay
  addGridOverlay();
  
  // Set initial grid visibility (both lines and labels hidden by default)
  if (state.gridGroup) {
    state.gridGroup.remove();
  }
  if (state.gridLabelGroup) {
    state.gridLabelGroup.remove();
  }
  
  // Place initial markers
  placeMarkers();

  // Add click handler for placing markers (default: set target, SHIFT-click sets mortar)
  state.leafletMap.on('click', (e) => {
    handleMapClick(e);
  });
  
  console.log('Leaflet map initialized');
}

/**
 * Clear any existing grid overlays (lines and labels).
 */
function clearGridOverlay() {
  if (state.gridGroup) {
    state.gridGroup.clearLayers();
    state.gridGroup.remove();
    state.gridGroup = null;
  }
  if (state.gridLabelGroup) {
    state.gridLabelGroup.clearLayers();
    state.gridLabelGroup.remove();
    state.gridLabelGroup = null;
  }
}

/**
 * Apply map size override from dropdown
 */
function applyMapSizeOverride() {
  if (!state.mapData || !state.leafletMap) {
    return;
  }
  
  const overrideSelect = document.getElementById('map-size-override');
  const overrideValue = overrideSelect.value;
  
  if (overrideValue === 'auto') {
    // Restore original map size from loaded data
    // The original is stored when we first load the map
    if (state.originalMapSize) {
      state.mapData.metadata.map_size = state.originalMapSize;
      state.mapData.metadata.grid_scale = state.originalMapSize / 13;
    }
  } else {
    // Apply manual override
    const newMapSize = parseInt(overrideValue, 10);
    state.mapData.metadata.map_size = newMapSize;
    state.mapData.metadata.grid_scale = newMapSize / 13;
  }
  
  // Reinitialize the map with new scale
  initializeLeafletMap();
  
  console.log(`Map size: ${state.mapData.metadata.map_size}m, Grid scale: ${state.mapData.metadata.grid_scale.toFixed(1)}m`);
}

/**
 * Toggle visibility of grid lines and labels
 */
function toggleGridLabels(show) {
  if (!state.leafletMap) {
    return;
  }
  
  if (show) {
    if (state.gridGroup) {
      state.gridGroup.addTo(state.leafletMap);
    }
    if (state.gridLabelGroup) {
      state.gridLabelGroup.addTo(state.leafletMap);
    }
  } else {
    if (state.gridGroup) {
      state.gridGroup.remove();
    }
    if (state.gridLabelGroup) {
      state.gridLabelGroup.remove();
    }
  }
}

/**
 * Add grid lines and labels to the Leaflet map using map metadata
 */
function addGridOverlay() {
  const metadata = state.mapData.metadata;
  const mapSize = metadata.map_size;
  const gridScale = metadata.grid_scale;

  // Remove existing overlay if any
  clearGridOverlay();

  // Create a new layer group
  state.gridGroup = L.layerGroup().addTo(state.leafletMap);
  state.gridLabelGroup = L.layerGroup().addTo(state.leafletMap);

  // Draw vertical and horizontal grid lines
  for (let i = 0; i <= 13; i++) {
    const x = i * gridScale;
    const y = i * gridScale;

    // Vertical line: from top (0,x) to bottom (mapSize,x)
    const vLine = L.polyline([[0, x], [mapSize, x]], {
      color: '#999',
      weight: 1,
      opacity: 0.6
    }).addTo(state.gridGroup);

    // Horizontal line: from left (y,0) to right (y,mapSize)
    const hLine = L.polyline([[y, 0], [y, mapSize]], {
      color: '#999',
      weight: 1,
      opacity: 0.6
    }).addTo(state.gridGroup);
  }

  // Add column labels (A-M) at top center of each square
  const columns = ['A','B','C','D','E','F','G','H','I','J','K','L','M'];
  for (let col = 0; col < 13; col++) {
    const centerX = (col + 0.5) * gridScale;
    const centerY = gridScale * 0.15; // position near top
    const label = L.marker([centerY, centerX], {
      icon: L.divIcon({
        className: 'grid-label grid-label--column',
        html: `<div>${columns[col]}</div>`,
        iconSize: [40, 18]
      })
    }).addTo(state.gridLabelGroup);
  }

  // Add row labels (1-13) at right center of each row
  // Row 1 is at the bottom (row index 0), Row 13 is at the top (row index 12)
  for (let row = 0; row < 13; row++) {
    const centerX = getRowLabelCenterX(mapSize, gridScale); // position near right
    const centerY = (row + 0.5) * gridScale;
    const rowNumber = 13 - row; // 1 at bottom, 1 at bottom
    const label = L.marker([centerY, centerX], {
      icon: L.divIcon({
        className: 'grid-label grid-label--row',
        html: `<div>${rowNumber}</div>`,
        iconSize: [24, 18]
      })
    }).addTo(state.gridLabelGroup);
  }
}

/**
 * Handle map click events to place mortar/target markers.
 * Default click: set target marker. Shift+click: set mortar marker.
 */
function handleMapClick(e) {
  const latlng = e.latlng;
  const x = latlng.lng;
  const y = latlng.lat;
  const metadata = state.mapData.metadata;

  // Decide which marker to place
  if (e.originalEvent && e.originalEvent.shiftKey) {
    // Place mortar
    if (!state.mortarMarker) {
      state.mortarMarker = L.marker([y, x], {
        icon: createCustomIcon('blue'),
        draggable: true
      }).addTo(state.leafletMap);
      setupMarkerEvents(state.mortarMarker, 'mortar');
    } else {
      state.mortarMarker.setLatLng([y, x]);
    }

    // Store PRECISE coordinates (NOT rounded to grid)
    state.mortarPreciseXY = { x, y };

    // Update dropdowns to show NEAREST keypad (for display/communication only)
    try {
      const grid = xyToGrid(x, y, metadata.grid_scale);
      document.getElementById('mortar-column').value = grid.column;
      document.getElementById('mortar-row').value = grid.row;
      document.getElementById('mortar-keypad').value = grid.keypad;
      updateGridDisplays();
    } catch (err) {
      console.warn('Marker placed out of bounds or conversion error:', err);
    }
  } else {
    // Default: place target
    if (!state.targetMarker) {
      state.targetMarker = L.marker([y, x], {
        icon: createCustomIcon('red'),
        draggable: true
      }).addTo(state.leafletMap);
      setupMarkerEvents(state.targetMarker, 'target');
    } else {
      state.targetMarker.setLatLng([y, x]);
    }

    // Store PRECISE coordinates (NOT rounded to grid)
    state.targetPreciseXY = { x, y };

    // Update dropdowns to show NEAREST keypad (for display/communication only)
    try {
      const grid = xyToGrid(x, y, metadata.grid_scale);
      document.getElementById('target-column').value = grid.column;
      document.getElementById('target-row').value = grid.row;
      document.getElementById('target-keypad').value = grid.keypad;
      updateGridDisplays();
    } catch (err) {
      console.warn('Marker placed out of bounds or conversion error:', err);
    }
  }

  // Update path line and range circle without forcing marker positions
  updatePathLine();
  if (state.mortarMarker) {
    updateRangeCircle(state.mortarMarker.getLatLng());
  }
}

// ====================================
// MARKER MANAGEMENT
// ====================================

function placeMarkers() {
  const metadata = state.mapData.metadata;
  
  // Get current grid selections
  const mortarColumn = document.getElementById('mortar-column').value;
  const mortarRow = parseInt(document.getElementById('mortar-row').value);
  const mortarKeypad = parseInt(document.getElementById('mortar-keypad').value);
  
  const targetColumn = document.getElementById('target-column').value;
  const targetRow = parseInt(document.getElementById('target-row').value);
  const targetKeypad = parseInt(document.getElementById('target-keypad').value);
  
  // Convert to XY coordinates (these snap to keypad centers when user changes dropdown)
  const mortarXY = gridToXY(mortarColumn, mortarRow, mortarKeypad, metadata.grid_scale);
  const targetXY = gridToXY(targetColumn, targetRow, targetKeypad, metadata.grid_scale);
  
  // Store precise coordinates (will be keypad centers when set from dropdown)
  state.mortarPreciseXY = { x: mortarXY.x, y: mortarXY.y };
  state.targetPreciseXY = { x: targetXY.x, y: targetXY.y };
  
  // Convert to Leaflet coordinates (Y-inverted for Leaflet)
  const mortarLatLng = [mortarXY.y, mortarXY.x];
  const targetLatLng = [targetXY.y, targetXY.x];
  
  // Create blue marker for mortar
  if (state.mortarMarker) {
    // Only update position if not currently being dragged
    if (!state.mortarMarker.dragging || !state.mortarMarker.dragging._draggable._moving) {
      state.mortarMarker.setLatLng(mortarLatLng);
    }
  } else {
    state.mortarMarker = L.marker(mortarLatLng, {
      icon: createCustomIcon('blue'),
      draggable: true
    }).addTo(state.leafletMap);
    setupMarkerEvents(state.mortarMarker, 'mortar');
  }
  
  // Create red marker for target
  if (state.targetMarker) {
    // Only update position if not currently being dragged
    if (!state.targetMarker.dragging || !state.targetMarker.dragging._draggable._moving) {
      state.targetMarker.setLatLng(targetLatLng);
    }
  } else {
    state.targetMarker = L.marker(targetLatLng, {
      icon: createCustomIcon('red'),
      draggable: true
    }).addTo(state.leafletMap);
    setupMarkerEvents(state.targetMarker, 'target');
  }
  
  // Draw line between markers
  updatePathLine();

  // Update range circle (show MAX range from mortar)
  updateRangeCircle(mortarLatLng);
}

/**
 * Setup drag and tooltip behavior for a marker
 */
function setupMarkerEvents(marker, type) {
  const metadata = state.mapData.metadata;

  if (!marker) return;

  // Update path line during drag (real-time feedback)
  marker.on('drag', (e) => {
    updatePathLine();
    if (type === 'mortar' && state.mortarMarker) {
      updateRangeCircle(state.mortarMarker.getLatLng());
    }
  });

  // Update grid coordinates after drag ends
  marker.on('dragend', (e) => {
    const latlng = e.target.getLatLng();
    const x = latlng.lng;
    const y = latlng.lat;
    try {
      // Store PRECISE position (NOT snapped to grid)
      if (type === 'mortar') {
        state.mortarPreciseXY = { x, y };
      } else {
        state.targetPreciseXY = { x, y };
      }
      
      // Update dropdown to show NEAREST keypad (for display only)
      const grid = xyToGrid(x, y, metadata.grid_scale);

      if (type === 'mortar') {
        document.getElementById('mortar-column').value = grid.column;
        document.getElementById('mortar-row').value = grid.row;
        document.getElementById('mortar-keypad').value = grid.keypad;
      } else {
        document.getElementById('target-column').value = grid.column;
        document.getElementById('target-row').value = grid.row;
        document.getElementById('target-keypad').value = grid.keypad;
      }

      updateGridDisplays();

      // Update elevation display for this marker
      try {
        const elev = state.mapData.getElevationAt(x, y);
        if (type === 'mortar') {
          document.getElementById('mortar-elevation-display').textContent = `${elev.toFixed(1)}m`;
        } else {
          document.getElementById('target-elevation-display').textContent = `${elev.toFixed(1)}m`;
        }
      } catch (err) {
        // ignore elevation update errors
      }

      // Final update of path line and range circle
      updatePathLine();
      if (type === 'mortar' && state.mortarMarker) {
        updateRangeCircle(state.mortarMarker.getLatLng());
      }
      
      // Auto-calculate firing solution after drag
      autoCalculateFiringSolution();
    } catch (err) {
      console.warn('Marker drag error:', err);
    }
  });

  // Tooltip update on each move (optional)
  marker.on('move', (e) => {
    const latlng = e.latlng || e.target.getLatLng();
    const x = latlng.lng;
    const y = latlng.lat;
    try {
      const grid = xyToGrid(x, y, metadata.grid_scale);
      const elev = state.mapData.getElevationAt(x, y);
      marker.bindTooltip(`${grid.column}${grid.row}-${grid.keypad} ${elev.toFixed(1)}m`, { permanent: false }).openTooltip();
    } catch (err) {
      // ignore
    }
  });
}

/**
 * Update the path line between mortar and target markers
 */
function updatePathLine() {
  if (!state.mortarMarker || !state.targetMarker || !state.leafletMap) {
    return;
  }

  const mortarLatLng = state.mortarMarker.getLatLng();
  const targetLatLng = state.targetMarker.getLatLng();

  if (state.pathLine) {
    state.pathLine.setLatLngs([mortarLatLng, targetLatLng]);
  } else {
    state.pathLine = L.polyline([mortarLatLng, targetLatLng], {
      color: '#00bcd4',
      weight: 2,
      opacity: 0.7,
      dashArray: '5, 10'
    }).addTo(state.leafletMap);
  }
}

/**
 * Create or update the range circle centered on mortar marker
 */
function updateRangeCircle(centerLatLng) {
  if (!centerLatLng) return;

  // Remove existing circle if present
  if (state.rangeCircle) {
    state.rangeCircle.setLatLng(centerLatLng);
    state.rangeCircle.setRadius(PR_PHYSICS.MAX_RANGE);
    return;
  }

  state.rangeCircle = L.circle(centerLatLng, {
    radius: PR_PHYSICS.MAX_RANGE,
    color: '#00bcd4',
    weight: 2,
    fillColor: '#00bcd4',
    fillOpacity: 0.05,
    className: 'range-circle'
  }).addTo(state.leafletMap);
}

function createCustomIcon(color) {
  const iconUrl = color === 'blue' 
    ? '/static/lib/images/marker-icon.png'
    : '/static/lib/images/marker-icon.png';
  
  return L.icon({
    iconUrl: iconUrl,
    shadowUrl: '/static/lib/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
    className: color === 'blue' ? 'mortar-marker' : 'target-marker'
  });
}

// ====================================
// CALCULATION
// ====================================

/**
 * Automatically calculate firing solution if both markers are placed
 */
function autoCalculateFiringSolution() {
  // Only auto-calculate if both markers exist and map is loaded
  if (!state.mapData || !state.mortarMarker || !state.targetMarker) {
    // Reset to initial state if markers missing
    resetResults();
    return;
  }
  
  try {
    performCalculation();
  } catch (err) {
    console.warn('Auto-calculation failed:', err);
    resetResults();
  }
}

/**
 * Reset results display to initial state
 */
function resetResults() {
  document.getElementById('result-distance').textContent = '--';
  document.getElementById('result-azimuth').textContent = '--';
  document.getElementById('result-height-delta').textContent = '--';
  document.getElementById('result-elevation-mils').textContent = '----';
  document.getElementById('result-elevation-degrees').textContent = '--';
  document.getElementById('result-tof').textContent = '--';
  
  const statusElement = document.getElementById('result-status');
  statusElement.textContent = 'Place markers and calculate';
  statusElement.className = 'calculator__result-status calculator__result-status--ready';
}

function performCalculation() {
  if (!state.mapData) {
    alert('Please load a map first');
    return;
  }
  
  const metadata = state.mapData.metadata;
  
  // Use PRECISE marker coordinates (not rounded to grid)
  // If precise coordinates not set, fall back to grid conversion
  let mortarXY, targetXY;
  
  if (state.mortarPreciseXY) {
    // Use precise coordinates from marker position
    mortarXY = state.mortarPreciseXY;
  } else {
    // Fallback: convert from grid reference (happens on initial load)
    const mortarColumn = document.getElementById('mortar-column').value;
    const mortarRow = parseInt(document.getElementById('mortar-row').value);
    const mortarKeypad = parseInt(document.getElementById('mortar-keypad').value);
    mortarXY = gridToXY(mortarColumn, mortarRow, mortarKeypad, metadata.grid_scale);
    state.mortarPreciseXY = { x: mortarXY.x, y: mortarXY.y };
  }
  
  if (state.targetPreciseXY) {
    // Use precise coordinates from marker position
    targetXY = state.targetPreciseXY;
  } else {
    // Fallback: convert from grid reference (happens on initial load)
    const targetColumn = document.getElementById('target-column').value;
    const targetRow = parseInt(document.getElementById('target-row').value);
    const targetKeypad = parseInt(document.getElementById('target-keypad').value);
    targetXY = gridToXY(targetColumn, targetRow, targetKeypad, metadata.grid_scale);
    state.targetPreciseXY = { x: targetXY.x, y: targetXY.y };
  }
  
  // Use the helper returned by loadMapData: getElevationAt(x, y)
  if (typeof state.mapData.getElevationAt !== 'function') {
    console.error('getElevationAt not available on mapData');
    alert('Elevation data not available for this map');
    return;
  }
  const mortarZ = state.mapData.getElevationAt(mortarXY.x, mortarXY.y);
  const targetZ = state.mapData.getElevationAt(targetXY.x, targetXY.y);
  
  // Update elevation displays
  document.getElementById('mortar-elevation-display').textContent = `${mortarZ.toFixed(1)}m`;
  document.getElementById('target-elevation-display').textContent = `${targetZ.toFixed(1)}m`;
  
  // Calculate firing solution
  const mortar = { x: mortarXY.x, y: mortarXY.y, z: mortarZ };
  const target = { x: targetXY.x, y: targetXY.y, z: targetZ };
  
  const solution = calculateFiringSolution(mortar, target);
  
  // Update path line to reflect current positions
  updatePathLine();
  
  // Display results
  displayResults(solution);
  
  console.log('Calculation complete:', solution);
}

function displayResults(solution) {
  // Distance
  document.getElementById('result-distance').textContent = `${solution.distance.toFixed(1)}m`;
  
  // Azimuth
  document.getElementById('result-azimuth').textContent = `${solution.azimuth.toFixed(1)}°`;
  
  // Height delta
  const deltaSign = solution.heightDelta >= 0 ? '+' : '';
  document.getElementById('result-height-delta').textContent = `${deltaSign}${solution.heightDelta.toFixed(1)}m`;
  
  // Elevation (primary: mils, secondary: degrees)
  document.getElementById('result-elevation-mils').textContent = solution.elevationMils !== null ? solution.elevationMils.toFixed(0) : '--';
  document.getElementById('result-elevation-degrees').textContent = solution.elevationDegrees !== null ? solution.elevationDegrees.toFixed(1) : '--';
  
  // Time of flight
  document.getElementById('result-tof').textContent = `${solution.timeOfFlight.toFixed(1)}s`;
  
  // Status
  const statusElement = document.getElementById('result-status');
  statusElement.textContent = solution.message || solution.status;
  
  // Update status styling
  statusElement.className = 'calculator__result-status';
  if (solution.status === 'OK') {
    statusElement.classList.add('calculator__result-status--ok');
  } else if (solution.status === 'EXTREME_ELEVATION') {
    statusElement.classList.add('calculator__result-status--warning');
  } else {
    statusElement.classList.add('calculator__result-status--error');
  }

  // Highlight target if outside range
  if (state.targetMarker) {
    const mortarPos = state.mortarMarker.getLatLng();
    const targetPos = state.targetMarker.getLatLng();
    const distance = Math.sqrt(Math.pow(targetPos.lng - mortarPos.lng, 2) + Math.pow(targetPos.lat - mortarPos.lat, 2));
    if (distance > PR_PHYSICS.MAX_RANGE) {
      state.targetMarker.getElement()?.classList.add('marker--out-of-range');
    } else {
      state.targetMarker.getElement()?.classList.remove('marker--out-of-range');
    }
  }
}

// ====================================
// EVENT LISTENERS
// ====================================

function setupEventListeners() {
  // Map selection
  document.getElementById('map-dropdown').addEventListener('change', () => {
    const selected = document.getElementById('map-dropdown').value;
    document.getElementById('load-map-btn').disabled = !selected;
    try { localStorage.setItem('pr_last_map', selected); } catch (e) { /* ignore */ }
  });
  
  document.getElementById('load-map-btn').addEventListener('click', loadSelectedMap);
  
  // Coordinate inputs - update displays
  const inputIds = [
    'mortar-column', 'mortar-row', 'mortar-keypad',
    'target-column', 'target-row', 'target-keypad'
  ];
  
  inputIds.forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
      updateGridDisplays();
      if (state.leafletMap) {
        placeMarkers();
        // Auto-calculate after dropdown change
        autoCalculateFiringSolution();
      }
    });
    // Pressing Enter while focused on any dropdown triggers calculation
    document.getElementById(id).addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        performCalculation();
      }
    });
  });
  
  // Calculate button
  document.getElementById('calculate-btn').addEventListener('click', performCalculation);
  
  // Grid labels toggle
  document.getElementById('grid-labels-toggle').addEventListener('change', (e) => {
    toggleGridLabels(e.target.checked);
  });
  
  // Dark mode toggle
  document.getElementById('dark-mode-toggle').addEventListener('change', (e) => {
    toggleTheme(e.target.checked);
  });
  
  // Map size override
  document.getElementById('map-size-override').addEventListener('change', () => {
    applyMapSizeOverride();
  });
}

function updateGridDisplays() {
  // Mortar grid display
  const mortarColumn = document.getElementById('mortar-column').value;
  const mortarRow = document.getElementById('mortar-row').value;
  const mortarKeypad = document.getElementById('mortar-keypad').value;
  document.getElementById('mortar-grid-display').textContent = 
    formatGridReference(mortarColumn, mortarRow, mortarKeypad);
  
  // Target grid display
  const targetColumn = document.getElementById('target-column').value;
  const targetRow = document.getElementById('target-row').value;
  const targetKeypad = document.getElementById('target-keypad').value;
  document.getElementById('target-grid-display').textContent = 
    formatGridReference(targetColumn, targetRow, targetKeypad);
}

// ====================================
// THEME MANAGEMENT
// ====================================

/**
 * Toggle between light and dark themes
 * @param {boolean} enableDark - True for dark mode, false for light mode
 */
function toggleTheme(enableDark) {
  try {
    if (enableDark) {
      // Set on both html and body so head initialization and runtime toggles align
      document.documentElement.classList.add('dark-mode');
      document.body.classList.add('dark-mode');
      localStorage.setItem('pr_theme_mode', 'dark');
      console.log('Theme: dark');
    } else {
      document.documentElement.classList.remove('dark-mode');
      document.body.classList.remove('dark-mode');
      localStorage.setItem('pr_theme_mode', 'light');
      console.log('Theme: light');
    }
  } catch (e) {
    console.error('Failed to save theme preference:', e);
  }
}

// ====================================
// UTILITY FUNCTIONS
// ====================================

function formatMapName(mapName) {
  // Convert underscores to spaces and capitalize
  return mapName
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function fixLeafletIconPaths() {
  // Fix Leaflet's default icon path to use local files
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: '/static/lib/images/marker-icon-2x.png',
    iconUrl: '/static/lib/images/marker-icon.png',
    shadowUrl: '/static/lib/images/marker-shadow.png',
  });
}

// ====================================
// EXPORTS (for testing/debugging)
// ====================================

window.prCalc = {
  state,
  performCalculation,
  loadSelectedMap
};
