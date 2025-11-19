# Implementation Tasks: Web Server and Deployment

## 1. Flask Server Implementation

- [ ] 1.1 Create `calculator/server.py` with Flask application structure
- [ ] 1.2 Configure Flask to serve static files from `/calculator/static/`
- [ ] 1.3 Add route for index.html at root URL `/`
- [ ] 1.4 Add route to serve processed maps from `/processed_maps/`
- [ ] 1.5 Configure MIME types for .json, .css, .js files
- [ ] 1.6 Implement auto-browser launch using webbrowser module
- [ ] 1.7 Add graceful shutdown handler (Ctrl+C)
- [ ] 1.8 Set port to 8080 with fallback if port is occupied
- [ ] 1.9 Disable Flask debug mode for production use
- [ ] 1.10 Add startup banner with server URL and shutdown instructions

## 2. Windows Launcher Script

- [ ] 2.1 Create `run.bat` batch file in repository root
- [ ] 2.2 Detect Python installation (try py, python, python3 commands)
- [ ] 2.3 Change directory to repository root
- [ ] 2.4 Launch Flask server: `python calculator/server.py`
- [ ] 2.5 Keep terminal window open after launch (pause on error)
- [ ] 2.6 Display error message if Python not found
- [ ] 2.7 Add comments explaining each step
- [ ] 2.8 Test on Windows 10 and Windows 11

## 3. Linux/Mac Launcher Script

- [ ] 3.1 Create `run.sh` shell script in repository root
- [ ] 3.2 Add shebang `#!/bin/bash` for portability
- [ ] 3.3 Detect Python installation (python3, python)
- [ ] 3.4 Change directory to script location
- [ ] 3.5 Launch Flask server: `python3 calculator/server.py`
- [ ] 3.6 Add trap for Ctrl+C to gracefully shutdown
- [ ] 3.7 Display error message if Python not found
- [ ] 3.8 Make executable with chmod +x
- [ ] 3.9 Test on Ubuntu Linux and macOS

## 4. Directory Structure Setup

- [ ] 4.1 Create `/calculator/` directory
- [ ] 4.2 Create `/calculator/static/` for assets
- [ ] 4.3 Create `/calculator/static/js/` for JavaScript modules
- [ ] 4.4 Create `/calculator/static/css/` for stylesheets
- [ ] 4.5 Create `/calculator/static/lib/` for dependencies
- [ ] 4.6 Create `/calculator/templates/` for HTML files
- [ ] 4.7 Add README.md in /calculator/ explaining structure

## 5. Leaflet.js Bundling

- [ ] 5.1 Download Leaflet.js 1.9.4 from official website
- [ ] 5.2 Extract leaflet.js to `/calculator/static/lib/leaflet/`
- [ ] 5.3 Extract leaflet.css to `/calculator/static/lib/leaflet/`
- [ ] 5.4 Copy Leaflet image assets (markers, etc.) to `/calculator/static/lib/leaflet/images/`
- [ ] 5.5 Verify all asset paths are relative (no CDN links)
- [ ] 5.6 Test Leaflet loads correctly offline
- [ ] 5.7 Add Leaflet license file to `/calculator/static/lib/leaflet/`

## 6. Offline Policy Enforcement

- [ ] 6.1 Audit all HTML files for external CDN links (remove if found)
- [ ] 6.2 Verify no external API calls in JavaScript
- [ ] 6.3 Test complete functionality without internet connection
- [ ] 6.4 Document offline-first architecture in README
- [ ] 6.5 Add .gitignore rules for development files (node_modules, .pyc, etc.)

## 7. Performance Optimization

- [ ] 7.1 Test startup time from run.bat double-click (target < 3 seconds)
- [ ] 7.2 Optimize Flask static file serving (disable debug logging)
- [ ] 7.3 Test map data loading performance (500ms per map target)
- [ ] 7.4 Profile memory usage with 50 maps loaded
- [ ] 7.5 Test on mid-range hardware (4GB RAM, dual-core CPU)

## 8. Error Handling

- [ ] 8.1 Handle Python not installed (clear error message in launcher)
- [ ] 8.2 Handle port 8080 already in use (try ports 8081-8089)
- [ ] 8.3 Handle missing processed_maps/ directory (warning, not crash)
- [ ] 8.4 Handle corrupted JSON files (skip with error log)
- [ ] 8.5 Handle browser not opening (display URL for manual copy)
- [ ] 8.6 Add Flask error handlers for 404, 500 errors

## 9. Documentation

- [ ] 9.1 Create `/calculator/README.md` with usage instructions
- [ ] 9.2 Document Flask server routes and configuration
- [ ] 9.3 Add troubleshooting section for common issues
- [ ] 9.4 Document directory structure and file purposes
- [ ] 9.5 Add developer notes for extending server functionality
- [ ] 9.6 Update root README.md with quick start instructions

## 10. Testing

- [ ] 10.1 Test run.bat on Windows 10
- [ ] 10.2 Test run.bat on Windows 11
- [ ] 10.3 Test run.sh on Ubuntu Linux
- [ ] 10.4 Test run.sh on macOS
- [ ] 10.5 Test offline operation (disconnect network, verify functionality)
- [ ] 10.6 Test with Python 3.8, 3.9, 3.10, 3.11
- [ ] 10.7 Test Flask serves all file types correctly (.html, .css, .js, .json)
- [ ] 10.8 Test browser auto-open on Chrome, Firefox, Edge
- [ ] 10.9 Test graceful shutdown with Ctrl+C
- [ ] 10.10 Test startup time measurement (instrument with timestamps)
- [ ] 10.11 Test portability (copy folder to different machine, run)
