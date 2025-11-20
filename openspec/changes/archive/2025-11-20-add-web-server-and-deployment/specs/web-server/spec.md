# Web Server Specification

## ADDED Requirements

### Requirement: Flask Static File Server

The system SHALL provide a Flask-based HTTP server that serves HTML, CSS, JavaScript, and JSON files from `/calculator/static/` and `/processed_maps/` directories.

#### Scenario: Server startup
- **WHEN** user runs `python calculator/server.py`
- **THEN** Flask application starts on localhost:8080
- **AND** startup banner displays server URL and shutdown instructions
- **AND** default browser opens automatically to `http://localhost:8080`
- **AND** server is ready to accept requests within 3 seconds

#### Scenario: Static file serving
- **WHEN** browser requests `/static/js/app.js`
- **THEN** Flask serves file with correct MIME type `application/javascript`
- **AND** file is returned with HTTP 200 status

#### Scenario: Map data serving
- **WHEN** browser requests `/maps/muttrah_city_2/heightmap.json`
- **THEN** Flask serves file from `/processed_maps/muttrah_city_2/heightmap.json`
- **AND** file is returned with MIME type `application/json`
- **AND** file loads within 500ms

#### Scenario: Port already in use
- **WHEN** port 8080 is occupied by another process
- **THEN** Flask tries ports 8081, 8082, up to 8089
- **AND** first available port is used
- **AND** startup message displays actual port number

### Requirement: One-Click Windows Launcher

The system SHALL provide run.bat script that auto-detects Python installation and launches Flask server with single double-click.

#### Scenario: Standard Python installation
- **WHEN** user double-clicks run.bat on Windows with Python installed
- **THEN** batch script detects Python using py launcher
- **AND** Flask server starts in new terminal window
- **AND** browser opens to calculator within 3 seconds
- **AND** terminal remains open showing server logs

#### Scenario: Python not found
- **WHEN** user double-clicks run.bat on system without Python
- **THEN** error message displays "Python not found. Please install Python 3.8 or newer"
- **AND** batch script pauses to show error
- **AND** browser does not open

#### Scenario: Manual shutdown
- **WHEN** user presses Ctrl+C in terminal window
- **THEN** Flask server shuts down gracefully
- **AND** message displays "Server stopped. You can close this window."

### Requirement: Cross-Platform Launcher Script

The system SHALL provide run.sh script for Linux and macOS that launches Flask server and handles errors gracefully.

#### Scenario: Linux/Mac execution
- **WHEN** user runs `./run.sh` on Linux or macOS
- **THEN** script detects python3 installation
- **AND** Flask server starts in current terminal
- **AND** browser opens to calculator
- **AND** Ctrl+C gracefully shuts down server

#### Scenario: Permission error
- **WHEN** run.sh is not executable
- **THEN** user sees "Permission denied" error
- **AND** error message suggests `chmod +x run.sh`

### Requirement: Offline Operation Guarantee

The system SHALL operate completely offline with zero external dependencies, no CDN links, and no API calls.

#### Scenario: Network disconnected
- **WHEN** user disconnects from internet and runs calculator
- **THEN** all functionality works identically to online mode
- **AND** Leaflet.js loads from local `/calculator/static/lib/` directory
- **AND** no network errors appear in browser console

#### Scenario: Bundled dependencies
- **WHEN** calculator loads in browser
- **THEN** Leaflet.js 1.9.4 is loaded from local files
- **AND** Leaflet CSS and image assets load from local files
- **AND** no HTTP requests are made to external domains
- **AND** browser Network tab shows only localhost requests

### Requirement: Portable Installation

The system SHALL be fully portable allowing entire calculator folder to be copied to different machines or USB drives without reconfiguration.

#### Scenario: Copy to different machine
- **WHEN** user copies entire project folder to different Windows machine
- **AND** user runs run.bat on new machine
- **THEN** calculator launches identically to original machine
- **AND** no file paths require updating
- **AND** no configuration files require editing

#### Scenario: USB drive execution
- **WHEN** user copies project to USB drive and runs from drive letter E:\
- **THEN** calculator launches with paths relative to drive letter
- **AND** Flask serves files correctly regardless of drive letter

### Requirement: Directory Structure Convention

The system SHALL organize files according to standard web application structure with separation of static assets, templates, and data.

#### Scenario: Expected directory layout
- **WHEN** developer inspects calculator folder
- **THEN** structure matches:
  - `/calculator/server.py` - Flask application
  - `/calculator/static/js/` - JavaScript modules
  - `/calculator/static/css/` - Stylesheets
  - `/calculator/static/lib/leaflet/` - Leaflet.js library
  - `/calculator/templates/index.html` - Main HTML template
  - `/processed_maps/` - JSON heightmap data

#### Scenario: Static asset resolution
- **WHEN** HTML references `/static/js/app.js`
- **THEN** Flask resolves to `/calculator/static/js/app.js`
- **AND** file is served correctly

### Requirement: Correct MIME Type Handling

The system SHALL serve all file types with correct MIME types to ensure browser compatibility.

#### Scenario: JavaScript MIME type
- **WHEN** browser requests .js file
- **THEN** Flask serves with `Content-Type: application/javascript`

#### Scenario: JSON MIME type
- **WHEN** browser requests .json file
- **THEN** Flask serves with `Content-Type: application/json`

#### Scenario: CSS MIME type
- **WHEN** browser requests .css file
- **THEN** Flask serves with `Content-Type: text/css`

#### Scenario: HTML MIME type
- **WHEN** browser requests .html file
- **THEN** Flask serves with `Content-Type: text/html; charset=utf-8`

### Requirement: Graceful Error Handling

The system SHALL handle common errors gracefully without crashes, providing clear user feedback.

#### Scenario: Missing processed_maps directory
- **WHEN** Flask starts and /processed_maps/ directory does not exist
- **THEN** warning message displays in console
- **AND** server continues running
- **AND** UI shows "No maps available" message instead of crashing

#### Scenario: Corrupted JSON file
- **WHEN** browser requests corrupted heightmap.json
- **THEN** Flask returns HTTP 500 error
- **AND** error message displays in browser console
- **AND** other maps continue to function

#### Scenario: Browser launch failure
- **WHEN** default browser cannot be determined or launched
- **THEN** server starts successfully anyway
- **AND** console displays: "Browser did not open automatically. Visit: http://localhost:8080"

### Requirement: Performance Targets

The system SHALL meet performance benchmarks for startup time, file serving, and map loading.

#### Scenario: Startup time measurement
- **WHEN** user measures time from run.bat double-click to browser fully loaded
- **THEN** total time is less than 3 seconds on mid-range hardware (4GB RAM, dual-core CPU)

#### Scenario: Static file serving speed
- **WHEN** browser requests JavaScript or CSS file
- **THEN** Flask responds within 50ms
- **AND** file transfer completes within 100ms for files under 1MB

#### Scenario: Map data loading speed
- **WHEN** browser requests heightmap.json (typical size 5MB)
- **THEN** file loads within 500ms on localhost
- **AND** browser receives complete file without timeouts

### Requirement: No Server-Side Calculation

The system SHALL delegate all ballistic calculations to client-side JavaScript, with Flask serving only as static file server.

#### Scenario: Calculator request
- **WHEN** user clicks "Calculate" button in UI
- **THEN** no HTTP request is sent to Flask server
- **AND** all calculations happen in browser JavaScript
- **AND** Flask server logs show no calculation-related requests

### Requirement: Startup Banner and Instructions

The system SHALL display clear startup banner with server information and shutdown instructions when Flask launches.

#### Scenario: Server startup display
- **WHEN** Flask server starts successfully
- **THEN** console displays:
  - Application name: "PROJECT REALITY MORTAR CALCULATOR"
  - Server URL: "Server running at http://localhost:8080"
  - Shutdown instruction: "Press Ctrl+C to stop server"
  - Status: "Browser opened automatically"

#### Scenario: Development mode warning
- **WHEN** Flask is run with debug=True (development only)
- **THEN** warning displays: "⚠ Debug mode enabled - disable for production use"
