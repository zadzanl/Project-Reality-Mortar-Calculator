/**
 * Project Reality Mortar Calculator - Main Application
 * Orchestrates UI, map display, and calculation modules
 * 
 * COORDINATE SYSTEM CRITICAL NOTE:
 * - PR coordinates: Y increases DOWNWARD (top-left origin, like images)
 * - Leaflet coordinates: Y increases UPWARD (standard math coordinates)
 * - All conversions between systems use: leafletY = mapSize - prY
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
  targetPreciseXY: null,  // { x: number, y: number } in meters
  // Layer overlays for terrain and contour maps
  terrainLayer: null,     // Leaflet ImageOverlay for minimap.png
  contourLayer: null,     // Leaflet ImageOverlay for contourmap.png
  terrainVisible: true,   // Terrain checkbox state (default ON)
  contourVisible: false   // Contour checkbox state (default OFF)
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
    const response = await fetch('mapsList.json');
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
    state.terrainLayer = null;
    state.contourLayer = null;
  }
  
  // Reset layer visibility state and checkboxes when loading new map
  state.terrainVisible = true;
  state.contourVisible = false;
  document.getElementById('terrain-layer-toggle').checked = true;
  document.getElementById('contour-layer-toggle').checked = false;
  document.getElementById('contour-layer-toggle').disabled = false;
  document.getElementById('contour-layer-label').textContent = 'Contour Map';
  
  // Create Leaflet map with Simple CRS (non-geographic coordinates)
  state.leafletMap = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -2,
    maxZoom: 2,
    attributionControl: false
  });
  
  // Calculate bounds for the map
  const mapSize = metadata.map_size;
  // IMPORTANT: Leaflet's Y-axis goes UP, PR's Y-axis goes DOWN
  // We handle this by inverting Y in all coordinate conversions (leafletY = mapSize - prY)
  // Bounds stay standard: [[minLat, minLng], [maxLat, maxLng]] = [[0,0], [mapSize, mapSize]]
  const bounds = [[0, 0], [mapSize, mapSize]];
  
  // Create terrain layer (minimap.png)
  const minimapUrl = `processed_maps/${state.currentMap}/minimap.png`;
  
  // Try to load minimap, fallback to colored rectangle
  const img = new Image();
  img.onload = () => {
    state.terrainLayer = L.imageOverlay(minimapUrl, bounds);
    if (state.terrainVisible) {
      state.terrainLayer.addTo(state.leafletMap);
    }
    // Load contour map after terrain layer is ready
    loadContourLayer(bounds);
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
    
    state.terrainLayer = L.imageOverlay(canvas.toDataURL(), bounds);
    if (state.terrainVisible) {
      state.terrainLayer.addTo(state.leafletMap);
    }
    // Add an overlay label to indicate minimap not available
    const overlay = L.control({ position: 'topright' });
    overlay.onAdd = function () {
      const div = L.DomUtil.create('div', 'minimap-overlay');
      div.innerHTML = `<div class="minimap-overlay__content">No minimap available<br/><strong>${formatMapName(state.currentMap || '')}</strong></div>`;
      return div;
    };
    overlay.addTo(state.leafletMap);
    // Try to load contour layer even without minimap
    loadContourLayer(bounds);
  };
  img.src = minimapUrl;
  
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
 * Load contour map layer for the current map.
 * @param {L.LatLngBounds} bounds - The map bounds to use for the overlay
 */
function loadContourLayer(bounds) {
  const contourUrl = `processed_maps/${state.currentMap}/contourmap.png`;
  
  // Test if contour map exists
  const testImg = new Image();
  testImg.onload = () => {
    // Contour map exists, create the layer
    state.contourLayer = L.imageOverlay(contourUrl, bounds);
    // Set initial opacity based on terrain visibility
    updateContourOpacity();
    // Add to map if contour should be visible
    if (state.contourVisible) {
      state.contourLayer.addTo(state.leafletMap);
    }
    console.log('Contour layer loaded for', state.currentMap);
  };
  testImg.onerror = () => {
    // Contour map not available
    console.warn('Contour map not found for', state.currentMap);
    state.contourLayer = null;
    // Disable the contour checkbox and update label
    document.getElementById('contour-layer-toggle').disabled = true;
    document.getElementById('contour-layer-toggle').checked = false;
    document.getElementById('contour-layer-label').textContent = 'Contour Map (unavailable)';
    state.contourVisible = false;
  };
  testImg.src = contourUrl;
}

/**
 * Toggle visibility of terrain (minimap) layer
 * @param {boolean} visible - Whether to show the terrain layer
 */
function toggleTerrainLayer(visible) {
  state.terrainVisible = visible;
  
  if (!state.leafletMap || !state.terrainLayer) {
    return;
  }
  
  if (visible) {
    state.terrainLayer.addTo(state.leafletMap);
    // Ensure contour layer stays on top of terrain layer
    if (state.contourLayer && state.contourVisible) {
      state.contourLayer.bringToFront();
    }
  } else {
    state.terrainLayer.remove();
  }
  
  // Update contour opacity when both layers state changes
  updateContourOpacity();
}

/**
 * Toggle visibility of contour map layer
 * @param {boolean} visible - Whether to show the contour layer
 */
function toggleContourLayer(visible) {
  state.contourVisible = visible;
  
  if (!state.leafletMap || !state.contourLayer) {
    return;
  }
  
  if (visible) {
    state.contourLayer.addTo(state.leafletMap);
  } else {
    state.contourLayer.remove();
  }
  
  // Update contour opacity based on terrain visibility
  updateContourOpacity();
}

/**
 * Update contour layer opacity based on terrain visibility.
 * - If both layers visible: contour opacity = 0.7
 * - If contour only: contour opacity = 1.0
 */
function updateContourOpacity() {
  if (!state.contourLayer) {
    return;
  }
  
  if (state.terrainVisible && state.contourVisible) {
    // Both layers visible - reduce contour opacity for overlay effect
    state.contourLayer.setOpacity(0.5);
  } else if (state.contourVisible) {
    // Contour only - full opacity
    state.contourLayer.setOpacity(1.0);
  }
}

/**
 * Add grid lines and labels to the Leaflet map using map metadata.
 * 
 * The minimap grid structure (41x41 keypads total):
 * - 1 padding keypad, then 13 major grid squares (each 3x3 keypads), then 1 padding keypad
 * - Total: 1 + (13 * 3) + 1 = 41 keypads per side
 * 
 * Grid line positions (in keypad units, 0-41):
 * - Thin lines: every keypad boundary
 * - Thick lines: at major grid square boundaries (every 3 keypads after the first padding)
 *   Thick line keypad positions: 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40
 */
function addGridOverlay() {
  const metadata = state.mapData.metadata;
  const mapSize = metadata.map_size;
  
  // Keypad size: map divided into 41 keypads per side
  const keypadSize = mapSize / 41;

  // Remove existing overlay if any
  clearGridOverlay();

  // Create layer groups
  state.gridGroup = L.layerGroup().addTo(state.leafletMap);
  state.gridLabelGroup = L.layerGroup().addTo(state.leafletMap);

  // Major grid boundaries (thick lines) - at these keypad positions
  // These mark the edges of the 13x13 major grid squares (A-M, 1-13)
  const thickLinePositions = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40];
  
  // All keypad boundaries (thin lines) - positions 0 through 41
  const allLinePositions = [];
  for (let i = 0; i <= 41; i++) {
    allLinePositions.push(i);
  }

  // Helper function to draw a vertical line at keypad position
  function drawVerticalLine(keypadPos, isThick) {
    const x = keypadPos * keypadSize;
    L.polyline([[0, x], [mapSize, x]], {
      color: '#999',
      weight: isThick ? 2 : 1,
      opacity: isThick ? 0.8 : 0.5
    }).addTo(state.gridGroup);
  }

  // Helper function to draw a horizontal line at keypad position
  function drawHorizontalLine(keypadPos, isThick) {
    const y = keypadPos * keypadSize;
    L.polyline([[y, 0], [y, mapSize]], {
      color: '#999',
      weight: isThick ? 2 : 1,
      opacity: isThick ? 0.8 : 0.5
    }).addTo(state.gridGroup);
  }

  // Draw all grid lines
  for (const pos of allLinePositions) {
    const isThick = thickLinePositions.includes(pos);
    drawVerticalLine(pos, isThick);
    drawHorizontalLine(pos, isThick);
  }

  // Column labels (A-M) positioned at center of each major grid square
  // Major grid squares start at keypad 1 and each spans 3 keypads
  // Column A: keypads 1-3, center at 2.5
  // Column B: keypads 4-6, center at 5.5
  // etc.
  const columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M'];
  const columnCenterKeypads = [2.5, 5.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5, 26.5, 29.5, 32.5, 35.5, 38.5];
  
  for (let i = 0; i < 13; i++) {
    const x = columnCenterKeypads[i] * keypadSize;
    const y = 0.5 * keypadSize; // Near top edge (in padding area)
    L.marker([y, x], {
      icon: L.divIcon({
        className: 'grid-label grid-label--column',
        html: `<div>${columns[i]}</div>`,
        iconSize: [40, 18]
      })
    }).addTo(state.gridLabelGroup);
  }

  // Row labels (1-13) positioned at center of each major grid row
  // Row 1 at top (keypads 1-3), Row 13 at bottom (keypads 37-39)
  const rowCenterKeypads = [2.5, 5.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5, 26.5, 29.5, 32.5, 35.5, 38.5];
  
  for (let i = 0; i < 13; i++) {
    const y = rowCenterKeypads[i] * keypadSize;
    const x = 40.5 * keypadSize; // Near right edge (in padding area)
    const rowNumber = 13 - i; // 13 at top, 1 at bottom
    L.marker([y, x], {
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
  const x = latlng.lng;  // X-axis is same in both systems
  const metadata = state.mapData.metadata;
  // IMPORTANT: Convert Leaflet Y (up) to PR Y (down): prY = mapSize - leafletY
  const y = metadata.map_size - latlng.lat;
  
  // For placing markers, keep original Leaflet coordinates (will display at correct visual position)
  const leafletLat = latlng.lat;
  const leafletLng = latlng.lng;

  // Decide which marker to place
  if (e.originalEvent && e.originalEvent.shiftKey) {
    // Place mortar
    if (!state.mortarMarker) {
      state.mortarMarker = L.marker([leafletLat, leafletLng], {
        icon: createCustomIcon('blue'),
        draggable: true
      }).addTo(state.leafletMap);
      setupMarkerEvents(state.mortarMarker, 'mortar');
    } else {
      state.mortarMarker.setLatLng([leafletLat, leafletLng]);
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
      state.targetMarker = L.marker([leafletLat, leafletLng], {
        icon: createCustomIcon('red'),
        draggable: true
      }).addTo(state.leafletMap);
      setupMarkerEvents(state.targetMarker, 'target');
    } else {
      state.targetMarker.setLatLng([leafletLat, leafletLng]);
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
  
  // Convert to Leaflet coordinates: [lat, lng] where lat=Y, lng=X
  // IMPORTANT: Invert Y-axis because Leaflet Y goes UP, PR Y goes DOWN
  const mortarLatLng = [metadata.map_size - mortarXY.y, mortarXY.x];
  const targetLatLng = [metadata.map_size - targetXY.y, targetXY.x];
  
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
    const x = latlng.lng;  // X-axis is same in both systems
    // IMPORTANT: Convert Leaflet Y (up) to PR Y (down): prY = mapSize - leafletY
    const y = metadata.map_size - latlng.lat;
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
    const x = latlng.lng;  // X-axis is same in both systems
    // IMPORTANT: Convert Leaflet Y (up) to PR Y (down): prY = mapSize - leafletY
    const y = metadata.map_size - latlng.lat;
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
 * Create or update the range circle centered on mortar marker.
 * Note: With angle-based constraint (85° max), effective range varies greatly with elevation.
 * Circle shows approximate flat-ground max range (~1485m) - actual range depends on height difference.
 */
function updateRangeCircle(centerLatLng) {
  if (!centerLatLng) return;

  // Remove existing circle if present
  if (state.rangeCircle) {
    state.rangeCircle.setLatLng(centerLatLng);
    // Display approximate max range on flat ground (45° optimal angle ≈ 1485m)
    state.rangeCircle.setRadius(1485);
    return;
  }

  state.rangeCircle = L.circle(centerLatLng, {
    radius: 1485,  // Approximate max range at 45° on level ground
    color: '#00bcd4',
    weight: 2,
    fillColor: '#00bcd4',
    fillOpacity: 0.05,
    className: 'range-circle'
  }).addTo(state.leafletMap);
}

function createCustomIcon(color) {
  const iconUrl = color === 'blue' 
    ? 'static/lib/images/marker-icon.png'
    : 'static/lib/images/marker-icon.png';
  
  return L.icon({
    iconUrl: iconUrl,
    shadowUrl: 'static/lib/images/marker-shadow.png',
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
  const targetZBase = state.mapData.getElevationAt(targetXY.x, targetXY.y);
  
  // Get height offset from input field (for buildings, etc.)
  const heightOffsetInput = document.getElementById('target-height-offset');
  const heightOffset = heightOffsetInput ? parseFloat(heightOffsetInput.value) || 0 : 0;
  const targetZ = targetZBase + heightOffset;
  
  // Update elevation displays
  document.getElementById('mortar-elevation-display').textContent = `${mortarZ.toFixed(1)}m`;
  if (heightOffset > 0) {
    document.getElementById('target-elevation-display').textContent = `${targetZBase.toFixed(1)}m (+${heightOffset.toFixed(1)}m) = ${targetZ.toFixed(1)}m`;
  } else {
    document.getElementById('target-elevation-display').textContent = `${targetZ.toFixed(1)}m`;
  }
  
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

  // Highlight target if angle is too high or unreachable
  if (state.targetMarker) {
    if (solution.status === 'ANGLE_TOO_HIGH' || solution.status === 'UNREACHABLE' || solution.status === 'OUT_OF_RANGE') {
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
  
  // Height offset input - triggers auto-calculation
  const heightOffsetInput = document.getElementById('target-height-offset');
  if (heightOffsetInput) {
    heightOffsetInput.addEventListener('input', () => {
      if (state.leafletMap) {
        autoCalculateFiringSolution();
      }
    });
    heightOffsetInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        performCalculation();
      }
    });
  }
  
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
  
  // Terrain layer toggle
  document.getElementById('terrain-layer-toggle').addEventListener('change', (e) => {
    toggleTerrainLayer(e.target.checked);
  });
  
  // Contour layer toggle
  document.getElementById('contour-layer-toggle').addEventListener('change', (e) => {
    toggleContourLayer(e.target.checked);
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
    iconRetinaUrl: 'static/lib/images/marker-icon-2x.png',
    iconUrl: 'static/lib/images/marker-icon.png',
    shadowUrl: 'static/lib/images/marker-shadow.png',
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
