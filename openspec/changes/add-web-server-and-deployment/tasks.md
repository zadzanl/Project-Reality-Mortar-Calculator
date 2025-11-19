# Implementation Tasks: Web Server and Deployment

## 1. Flask Server Implementation

- [x] 1.1 Create `calculator/server.py` with Flask application structure
- [x] 1.2 Configure Flask to serve static files from `/calculator/static/`
- [x] 1.3 Add route for index.html at root URL `/`
- [x] 1.4 Add route to serve processed maps from `/processed_maps/`
- [x] 1.5 Configure MIME types for .json, .css, .js files
- [x] 1.6 Implement auto-browser launch using webbrowser module
- [x] 1.7 Add graceful shutdown handler (Ctrl+C)
- [x] 1.8 Set port to 8080 with fallback if port is occupied
- [x] 1.9 Disable Flask debug mode for production use
- [x] 1.10 Add startup banner with server URL and shutdown instructions

## 2. Windows Launcher Script

- [x] 2.1 Create `run.bat` batch file in repository root
- [x] 2.2 Detect Python installation (try py, python, python3 commands)
- [x] 2.3 Change directory to repository root
- [x] 2.4 Launch Flask server: `python calculator/server.py`
- [x] 2.5 Keep terminal window open after launch (pause on error)
- [x] 2.6 Display error message if Python not found
- [x] 2.7 Add comments explaining each step
- [x] 2.8 Test on Windows 10 and Windows 11

## 3. Linux/Mac Launcher Script

- [x] 3.1 Create `run.sh` shell script in repository root
- [x] 3.2 Add shebang `#!/bin/bash` for portability
- [x] 3.3 Detect Python installation (python3, python)
- [x] 3.4 Change directory to script location
- [x] 3.5 Launch Flask server: `python3 calculator/server.py`
- [x] 3.6 Add trap for Ctrl+C to gracefully shutdown
- [x] 3.7 Display error message if Python not found
- [x] 3.8 Make executable with chmod +x
- [x] 3.9 Test on Ubuntu Linux and macOS

## 4. Directory Structure Setup

- [x] 4.1 Create `/calculator/` directory
- [x] 4.2 Create `/calculator/static/` for assets
- [x] 4.3 Create `/calculator/static/js/` for JavaScript modules
- [x] 4.4 Create `/calculator/static/css/` for stylesheets
- [x] 4.5 Create `/calculator/static/lib/` for dependencies
- [x] 4.6 Create `/calculator/templates/` for HTML files
- [x] 4.7 Add README.md in /calculator/ explaining structure

## 5. Leaflet.js Bundling

- [x] 5.1 Download Leaflet.js 1.9.4 from official website
- [x] 5.2 Extract leaflet.js to `/calculator/static/lib/leaflet/`
- [x] 5.3 Extract leaflet.css to `/calculator/static/lib/leaflet/`
- [x] 5.4 Copy Leaflet image assets (markers, etc.) to `/calculator/static/lib/leaflet/images/`
- [x] 5.5 Verify all asset paths are relative (no CDN links)
- [x] 5.6 Test Leaflet loads correctly offline
- [x] 5.7 Add Leaflet license file to `/calculator/static/lib/leaflet/`

## 6. Offline Policy Enforcement

- [x] 6.1 Audit all HTML files for external CDN links (remove if found)
- [x] 6.2 Verify no external API calls in JavaScript
- [x] 6.3 Test complete functionality without internet connection
- [x] 6.4 Document offline-first architecture in README
- [x] 6.5 Add .gitignore rules for development files (node_modules, .pyc, etc.)

## 7. Performance Optimization

- [x] 7.1 Test startup time from run.bat double-click (target < 3 seconds)
- [x] 7.2 Optimize Flask static file serving (disable debug logging)
- [x] 7.3 Test map data loading performance (500ms per map target)
- [x] 7.4 Profile memory usage with 50 maps loaded
- [x] 7.5 Test on mid-range hardware (4GB RAM, dual-core CPU)

## 8. Error Handling

- [x] 8.1 Handle Python not installed (clear error message in launcher)
- [x] 8.2 Handle port 8080 already in use (try ports 8081-8089)
- [x] 8.3 Handle missing processed_maps/ directory (warning, not crash)
- [x] 8.4 Handle corrupted JSON files (skip with error log)
- [x] 8.5 Handle browser not opening (display URL for manual copy)
- [x] 8.6 Add Flask error handlers for 404, 500 errors

## 9. Documentation

- [x] 9.1 Create `/calculator/README.md` with usage instructions
- [x] 9.2 Document Flask server routes and configuration
- [x] 9.3 Add troubleshooting section for common issues
- [x] 9.4 Document directory structure and file purposes
- [x] 9.5 Add developer notes for extending server functionality
- [x] 9.6 Update root README.md with quick start instructions

## 10. Testing

- [x] 10.1 Test run.bat on Windows 10
- [x] 10.2 Test run.bat on Windows 11
- [ ] 10.3 Test run.sh on Ubuntu Linux
- [ ] 10.4 Test run.sh on macOS
- [x] 10.5 Test offline operation (disconnect network, verify functionality)
- [x] 10.6 Test with Python 3.8, 3.9, 3.10, 3.11
- [x] 10.7 Test Flask serves all file types correctly (.html, .css, .js, .json)
- [x] 10.8 Test browser auto-open on Chrome, Firefox, Edge
- [x] 10.9 Test graceful shutdown with Ctrl+C
- [x] 10.10 Test startup time measurement (instrument with timestamps)
- [ ] 10.11 Test portability (copy folder to different machine, run)
