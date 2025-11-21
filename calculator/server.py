#!/usr/bin/env python3
"""
Flask Static File Server for Project Reality Mortar Calculator
Serves HTML, CSS, JavaScript, and JSON map data files to browser.
All calculations happen in the browser - this server only serves files.
"""

import os
import sys
import webbrowser
import time
from pathlib import Path
from flask import Flask, send_from_directory, render_template, abort, Response

__version__ = "1.0.0"

# When running as a PyInstaller bundle the application files are extracted into
# a temporary directory pointed to by sys._MEIPASS. Configure Flask so that
# templates and static files are resolved from the embedded paths when frozen.
if getattr(sys, 'frozen', False):
    _meipass = Path(sys._MEIPASS)
    # In our spec we include the calculator folder inside the bundle so templates
    # live at: <meipass>/calculator/templates
    static_folder = str(_meipass / 'calculator' / 'static')
    template_folder = str(_meipass / 'calculator' / 'templates')
    # Project root inside the bundle is the meipass directory
    PROJECT_ROOT = _meipass
else:
    static_folder = 'static'
    template_folder = 'templates'
    PROJECT_ROOT = Path(__file__).parent.parent

# Create Flask application with the resolved asset locations
app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)

# Disable debug mode for production use
app.config['DEBUG'] = False

# Processed maps directory is relative to project root (or bundled meipass)
PROCESSED_MAPS_DIR = PROJECT_ROOT / 'processed_maps'

# Configure MIME types explicitly
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development


@app.route('/')
def index():
    """Serve the main calculator page."""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
        # Return a minimal SVG favicon to avoid 404s when the browser requests /favicon.ico
        svg = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>
    <rect width='100%' height='100%' fill='#2c3e50'/>
    <text x='50%' y='50%' font-size='10' text-anchor='middle' fill='#ffffff' dy='.35em'>PR</text>
</svg>
"""
        return Response(svg, mimetype='image/svg+xml')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images, libraries)."""
    return send_from_directory(app.static_folder, filename)


@app.route('/maps/<map_name>/<filename>')
def serve_map_data(map_name, filename):
    """
    Serve processed map data from /processed_maps/ directory.
    
    Examples:
    - /maps/muttrah_city_2/heightmap.json
    - /maps/muttrah_city_2/metadata.json
    """
    map_dir = PROCESSED_MAPS_DIR / map_name
    
    # Security check: ensure map directory exists
    if not map_dir.is_dir():
        abort(404, description=f"Map '{map_name}' not found")
    
    # Security check: prevent directory traversal
    file_path = map_dir / filename
    if not file_path.is_file():
        abort(404, description=f"File '{filename}' not found in map '{map_name}'")
    
    # Serve with correct MIME type
    if filename.endswith('.json'):
        return send_from_directory(map_dir, filename, mimetype='application/json')
    else:
        return send_from_directory(map_dir, filename)


@app.route('/processed_maps/<map_name>/<filename>')
def serve_processed_map_data(map_name, filename):
    """
    Backwards compatibility: serve files from /processed_maps/<map_name>/
    This mirrors the /maps/<map_name>/ route and returns the same files.
    """
    return serve_map_data(map_name, filename)


@app.route('/maps/list')
def list_maps():
    """
    Return list of available maps as JSON.
    Used by frontend to populate map selection dropdown.
    """
    from flask import jsonify
    
    # Check if processed_maps directory exists
    if not PROCESSED_MAPS_DIR.is_dir():
        return jsonify({
            'error': 'No maps available',
            'message': 'The processed_maps directory does not exist',
            'maps': []
        }), 404
    
    # Scan for maps (directories containing metadata.json)
    maps = []
    for item in PROCESSED_MAPS_DIR.iterdir():
        if item.is_dir() and (item / 'metadata.json').is_file():
            maps.append({
                'name': item.name,
                'path': item.name
            })
    
    # Sort alphabetically
    maps.sort(key=lambda x: x['name'])
    
    return jsonify({
        'maps': maps,
        'count': len(maps)
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors with JSON response."""
    from flask import jsonify, request
    
    if request.path.startswith('/maps/'):
        return jsonify({
            'error': '404 Not Found',
            'message': str(error.description)
        }), 404
    
    return jsonify({
        'error': '404 Not Found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with JSON response."""
    from flask import jsonify
    
    return jsonify({
        'error': '500 Internal Server Error',
        'message': 'An internal error occurred. Check server logs.'
    }), 500


def find_available_port(start_port=8080, max_attempts=10):
    """
    Find an available port starting from start_port.
    Tries ports 8080-8089 by default.
    """
    import socket
    
    for port_offset in range(max_attempts):
        port = start_port + port_offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            # Port is in use, try next one
            continue
        finally:
            sock.close()
    
    # No available port found
    return None


def open_browser(url, delay=1.5):
    """
    Open default browser to the calculator URL.
    Runs in a separate thread after a small delay to let server start.
    """
    import threading
    
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            print(f"✓ Browser opened automatically")
        except Exception as e:
            print(f"⚠ Browser did not open automatically: {e}")
            print(f"  Please open manually: {url}")
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def print_banner(port):
    """Display startup banner with server information."""
    print("\n" + "="*60)
    print("  PROJECT REALITY MORTAR CALCULATOR")
    print(f"  Version {__version__}")
    print("="*60)
    print(f"\n  Server running at: http://localhost:{port}")
    print(f"  Network access:    http://127.0.0.1:{port}")
    print(f"\n  Press Ctrl+C to stop the server")
    print("\n" + "="*60 + "\n")


def check_processed_maps():
    """Check if processed_maps directory exists and warn if missing."""
    if not PROCESSED_MAPS_DIR.is_dir():
        print("⚠ WARNING: processed_maps directory not found")
        print(f"  Expected location: {PROCESSED_MAPS_DIR}")
        print("  Calculator will run but no maps will be available.")
        print()
    else:
        # Count available maps
        map_count = sum(1 for item in PROCESSED_MAPS_DIR.iterdir() 
                       if item.is_dir() and (item / 'metadata.json').is_file())
        print(f"✓ Found {map_count} processed maps")


def main():
    """Main entry point - start Flask server with auto-browser launch."""
    
    # Find available port
    port = find_available_port()
    if port is None:
        print("ERROR: Could not find an available port (tried 8080-8089)")
        print("Please close other applications using these ports and try again.")
        sys.exit(1)
    
    # Check for processed maps
    check_processed_maps()
    
    # Display startup banner
    print_banner(port)
    
    # Open browser automatically
    server_url = f"http://localhost:{port}"
    open_browser(server_url)
    
    # Start Flask server
    try:
        app.run(
            host='127.0.0.1',  # Only accessible from localhost
            port=port,
            debug=False,       # Disable debug mode for production
            use_reloader=False # Disable auto-reload to prevent double browser open
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("  Server stopped. You can close this window.")
        print("="*60 + "\n")
        sys.exit(0)


if __name__ == '__main__':
    main()
