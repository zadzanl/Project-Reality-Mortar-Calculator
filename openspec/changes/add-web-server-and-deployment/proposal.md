# Proposal: Web Server and Deployment Infrastructure

## Why

The mortar calculator needs a web server to send files to your web browser.

The server must:
1. Send HTML, CSS, JavaScript, and map data files
2. Work without internet (no external websites)
3. Start with one click (double-click run.bat)

Right now, we have no web server.

## What Changes

- **Flask Static File Server** (`calculator/server.py`):
  - Small Flask program that sends files only
  - Does NOT do calculations (browser does all math)
  - Sends HTML, CSS, JavaScript, and map data files
  - Opens browser automatically to http://localhost:8080
  - Shuts down cleanly when you press Ctrl+C
  - Works only on your computer (not accessible from other computers)

- **Launch Scripts**:
  - `run.bat` for Windows (double-click to start)
  - `run.sh` for Linux/Mac (make executable with chmod +x)
  - Finds Python automatically
  - Starts Flask server and opens browser
  - Shows server address and how to stop it

- **Directory Structure**:
  - `/calculator/` - Web application root
  - `/calculator/static/` - Static assets (CSS, JS, images)
  - `/calculator/static/js/` - JavaScript modules
  - `/calculator/static/css/` - Stylesheets
  - `/calculator/static/lib/` - Bundled dependencies (Leaflet.js)
  - `/calculator/templates/` - HTML files
  - `/processed_maps/` - JSON heightmap data (served by Flask)

- **Offline Dependency Bundling**:
  - Download Leaflet.js 1.9.4 and save in `/calculator/static/lib/` folder
  - Include all Leaflet files (CSS, images) in project
  - No links to external websites
  - You can copy the entire folder to a USB drive and it still works

- **Performance Requirements**:
  - Startup time < 3 seconds from run.bat double-click
  - Flask serves static files with correct MIME types
  - Browser opens automatically to correct URL
  - Tool works completely offline

## Impact

- **Affected Specs**: Creates new capability `web-server`
- **Affected Code**:
  - New files: `calculator/server.py`, `run.bat`, `run.sh`, `calculator/static/lib/leaflet/*`
  - New directories: `/calculator/`, `/calculator/static/`, `/calculator/templates/`
- **Dependencies**: Flask 2.3+, Werkzeug 2.3+, Python 3.8+
- **User Impact**: End users run `run.bat` for one-click launch, no manual server configuration needed
- **Deployment**: Tool is fully portable (copy entire folder to USB drive)
