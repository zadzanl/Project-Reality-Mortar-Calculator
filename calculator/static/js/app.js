/**
 * Project Reality Mortar Calculator - Main Application
 * Orchestrates UI, map display, and calculation modules
 */

import { calculateFiringSolution } from './ballistics.js';
import { gridToXY, formatGridReference } from './coordinates.js';
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
  pathLine: null
};

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
    
    console.log('Map loaded:', mapName);
    console.log('Map metadata:', state.mapData.metadata);
    
    // Initialize Leaflet map
    initializeLeafletMap();
    
    // Enable calculate button
    document.getElementById('calculate-btn').disabled = false;
    
    // Update grid displays
    updateGridDisplays();
    
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
  
  // Place initial markers
  placeMarkers();
  
  console.log('Leaflet map initialized');
}

function addGridOverlay() {
  // Grid overlay will be added in future version
  // For now, just log that it's ready
  console.log('Grid overlay ready (to be implemented)');
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
  
  // Convert to XY coordinates
  const mortarXY = gridToXY(mortarColumn, mortarRow, mortarKeypad, metadata.grid_scale);
  const targetXY = gridToXY(targetColumn, targetRow, targetKeypad, metadata.grid_scale);
  
  // Convert to Leaflet coordinates (Y-inverted for Leaflet)
  const mortarLatLng = [mortarXY.y, mortarXY.x];
  const targetLatLng = [targetXY.y, targetXY.x];
  
  // Create blue marker for mortar
  if (state.mortarMarker) {
    state.mortarMarker.setLatLng(mortarLatLng);
  } else {
    state.mortarMarker = L.marker(mortarLatLng, {
      icon: createCustomIcon('blue'),
      draggable: false  // V1: not draggable, V2+: enable dragging
    }).addTo(state.leafletMap);
  }
  
  // Create red marker for target
  if (state.targetMarker) {
    state.targetMarker.setLatLng(targetLatLng);
  } else {
    state.targetMarker = L.marker(targetLatLng, {
      icon: createCustomIcon('red'),
      draggable: false  // V1: not draggable, V2+: enable dragging
    }).addTo(state.leafletMap);
  }
  
  // Draw line between markers
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

function performCalculation() {
  if (!state.mapData) {
    alert('Please load a map first');
    return;
  }
  
  const metadata = state.mapData.metadata;
  
  // Get mortar position
  const mortarColumn = document.getElementById('mortar-column').value;
  const mortarRow = parseInt(document.getElementById('mortar-row').value);
  const mortarKeypad = parseInt(document.getElementById('mortar-keypad').value);
  const mortarXY = gridToXY(mortarColumn, mortarRow, mortarKeypad, metadata.grid_scale);
  // Use the helper returned by loadMapData: getElevationAt(x, y)
  if (typeof state.mapData.getElevationAt !== 'function') {
    console.error('getElevationAt not available on mapData');
    alert('Elevation data not available for this map');
    return;
  }
  const mortarZ = state.mapData.getElevationAt(mortarXY.x, mortarXY.y);
  
  // Get target position
  const targetColumn = document.getElementById('target-column').value;
  const targetRow = parseInt(document.getElementById('target-row').value);
  const targetKeypad = parseInt(document.getElementById('target-keypad').value);
  const targetXY = gridToXY(targetColumn, targetRow, targetKeypad, metadata.grid_scale);
  const targetZ = state.mapData.getElevationAt(targetXY.x, targetXY.y);
  
  // Update elevation displays
  document.getElementById('mortar-elevation-display').textContent = `${mortarZ.toFixed(1)}m`;
  document.getElementById('target-elevation-display').textContent = `${targetZ.toFixed(1)}m`;
  
  // Calculate firing solution
  const mortar = { x: mortarXY.x, y: mortarXY.y, z: mortarZ };
  const target = { x: targetXY.x, y: targetXY.y, z: targetZ };
  
  const solution = calculateFiringSolution(mortar, target);
  
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
  document.getElementById('result-elevation-mils').textContent = solution.elevationMils.toFixed(0);
  document.getElementById('result-elevation-degrees').textContent = solution.elevationDeg.toFixed(1);
  
  // Time of flight
  document.getElementById('result-tof').textContent = `${solution.timeOfFlight.toFixed(1)}s`;
  
  // Status
  const statusElement = document.getElementById('result-status');
  statusElement.textContent = solution.status;
  
  // Update status styling
  statusElement.className = 'calculator__result-status';
  if (solution.status === 'OK') {
    statusElement.classList.add('calculator__result-status--ok');
  } else if (solution.status.includes('WARNING')) {
    statusElement.classList.add('calculator__result-status--warning');
  } else {
    statusElement.classList.add('calculator__result-status--error');
  }
}

// ====================================
// EVENT LISTENERS
// ====================================

function setupEventListeners() {
  // Map selection
  document.getElementById('map-dropdown').addEventListener('change', () => {
    document.getElementById('load-map-btn').disabled = !document.getElementById('map-dropdown').value;
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
      }
    });
  });
  
  // Calculate button
  document.getElementById('calculate-btn').addEventListener('click', performCalculation);
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
