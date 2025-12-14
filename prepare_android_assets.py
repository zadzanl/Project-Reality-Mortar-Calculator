import os
import shutil
import json
import re
import argparse

# Paths
ROOT_DIR = os.getcwd()
ANDROID_APP_DIR = os.path.join(ROOT_DIR, 'android_app')
ASSETS_DIR = os.path.join(ANDROID_APP_DIR, 'app', 'src', 'main', 'assets')
WWW_DIR = os.path.join(ASSETS_DIR, 'www')
MAPS_DIR = os.path.join(WWW_DIR, 'maps')

# Source paths
TEMPLATES_DIR = os.path.join(ROOT_DIR, 'calculator', 'templates')
STATIC_DIR = os.path.join(ROOT_DIR, 'calculator', 'static')
PROCESSED_MAPS_DIR = os.path.join(ROOT_DIR, 'processed_maps')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit number of maps to copy (for testing/demo)')
    args = parser.parse_args()

    print(f"Preparing assets in {WWW_DIR}")

    # 1. Create directories
    if os.path.exists(WWW_DIR):
        shutil.rmtree(WWW_DIR)

    os.makedirs(WWW_DIR, exist_ok=True)
    os.makedirs(os.path.join(ANDROID_APP_DIR, 'app', 'src', 'main', 'java', 'com', 'pr', 'mortarcalc'), exist_ok=True)
    os.makedirs(os.path.join(ANDROID_APP_DIR, 'app', 'src', 'main', 'res', 'values'), exist_ok=True)

    # 2. Copy files
    print("Copying web assets...")
    shutil.copy(os.path.join(TEMPLATES_DIR, 'index.html'), os.path.join(WWW_DIR, 'index.html'))
    shutil.copytree(STATIC_DIR, os.path.join(WWW_DIR, 'static'))

    print("Copying maps...")
    os.makedirs(MAPS_DIR, exist_ok=True)

    all_maps = [d for d in os.listdir(PROCESSED_MAPS_DIR) if os.path.isdir(os.path.join(PROCESSED_MAPS_DIR, d))]
    all_maps.sort()

    if args.limit:
        print(f"Limiting to {args.limit} maps for testing.")
        maps_to_copy = all_maps[:args.limit]
        # Ensure popular maps are included if possible
        priority_maps = ['muttrah_city_2', 'fallujah_west']
        for pm in priority_maps:
            if pm in all_maps and pm not in maps_to_copy:
                # Append if not present, don't replace to avoid confusion
                maps_to_copy.append(pm)
    else:
        maps_to_copy = all_maps

    for map_name in maps_to_copy:
        src = os.path.join(PROCESSED_MAPS_DIR, map_name)
        dst = os.path.join(MAPS_DIR, map_name)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.bat', 'README.md'))

    # 3. Process maps
    print("Processing maps metadata...")
    maps_list = []

    for map_name in os.listdir(MAPS_DIR):
        map_path = os.path.join(MAPS_DIR, map_name)
        if os.path.isdir(map_path):
            if os.path.exists(os.path.join(map_path, 'metadata.json')):
                maps_list.append({'name': map_name, 'path': map_name})
                # Check for .gz file
                if not os.path.exists(os.path.join(map_path, 'heightmap.json.gz')):
                    print(f"Warning: heightmap.json.gz missing for {map_name}")

    maps_list.sort(key=lambda x: x['name'])

    with open(os.path.join(MAPS_DIR, 'mapsList.json'), 'w', encoding='utf-8') as f:
        json.dump({'maps': maps_list, 'count': len(maps_list)}, f)

    # 4. Patch files
    print("Patching files...")

    # Patch index.html
    index_path = os.path.join(WWW_DIR, 'index.html')
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove leading slashes from links
    content = content.replace('href="/', 'href="')
    content = content.replace('src="/', 'src="')
    # Remove favicon link
    content = re.sub(r'<link rel="icon"[^>]*>', '', content)

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Patch styles.css
    css_path = os.path.join(WWW_DIR, 'static', 'css', 'styles.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix absolute paths in CSS
    # Original: url('/static/lib/images/...')
    # New relative from static/css/: ../lib/images/...
    content = content.replace("url('/static/lib/images/", "url('../lib/images/")

    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Patch app.js
    app_js_path = os.path.join(WWW_DIR, 'static', 'js', 'app.js')
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change /maps/list to maps/mapsList.json
    content = content.replace("fetch('/maps/list')", "fetch('maps/mapsList.json')")

    # Change /maps/ path to maps/ (handling template literals)
    content = content.replace("`/maps/${state.currentMap}", "`maps/${state.currentMap}")

    # Fix Leaflet icon paths
    content = content.replace("'/static/lib/images/", "'static/lib/images/")

    with open(app_js_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Patch heightmap.js
    hm_js_path = os.path.join(WWW_DIR, 'static', 'js', 'heightmap.js')
    with open(hm_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change fetch URL (relative)
    content = content.replace("`/maps/${mapName}/heightmap.json.gz`", "`maps/${mapName}/heightmap.json.gz`")
    content = content.replace("`/maps/${mapName}/metadata.json`", "`maps/${mapName}/metadata.json`")

    with open(hm_js_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Assets prepared successfully.")

if __name__ == '__main__':
    main()
