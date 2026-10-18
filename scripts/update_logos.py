#!/usr/bin/env python3
"""Generate favicons, desktop icons, and Android mipmaps from master logo.

ROLE: Maintainer-only asset generation utility.
INPUTS:
    - assets/mortar_calc_logo.png (or custom image path via CLI argument)
OUTPUTS:
    - www/favicon.ico
    - calculator/static/icon.ico
    - calculator/static/favicon.ico
    - android/app/src/main/res/mipmap-*/ic_launcher*.png
    - android/app/src/main/res/drawable*/splash.png
HOW TO RUN:
    python scripts/update_logos.py
    python scripts/update_logos.py path/to/logo.png
DID IT WORK CHECK:
    Prints 'Saved ...' and 'Updated ...' for favicons, mipmaps, and splash screens.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent


def update_icons(source_path):
    source_file = Path(source_path).resolve()
    if not source_file.is_file():
        print(f"Error: Source image {source_file} not found.")
        return

    img = Image.open(source_file)
    
    # Ensure image is RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # 1. Generate Favicons (Web & Desktop)
    print("Generating favicons...")
    favicon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Web favicon (offline build)
    www_path = REPO_ROOT / 'www' / 'favicon.ico'
    if www_path.parent.is_dir():
        img.save(www_path, format='ICO', sizes=favicon_sizes)
        print(f"Saved {www_path}")

    # Desktop icon
    static_path = REPO_ROOT / 'calculator' / 'static'
    static_path.mkdir(parents=True, exist_ok=True)
    desktop_icon_path = static_path / 'icon.ico'
    img.save(desktop_icon_path, format='ICO', sizes=favicon_sizes)
    print(f"Saved {desktop_icon_path}")

    # Flask favicon (served by server.py)
    flask_favicon_path = static_path / 'favicon.ico'
    img.save(flask_favicon_path, format='ICO', sizes=favicon_sizes)
    print(f"Saved {flask_favicon_path}")

    # 2. Generate Android Launcher Icons (Mipmaps)
    # Sizes: mdpi=48, hdpi=72, xhdpi=96, xxhdpi=144, xxxhdpi=192
    mipmap_sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192
    }

    android_res_path = REPO_ROOT / 'android' / 'app' / 'src' / 'main' / 'res'

    for folder, size in mipmap_sizes.items():
        folder_path = android_res_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        # Resize for standard icon
        resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save ic_launcher.png
        resized_img.save(folder_path / 'ic_launcher.png')
        
        # Save ic_launcher_foreground.png (for adaptive)
        adaptive_size = int(size * 108 / 48)  # Scale based on 48dp base
        adaptive_img = img.resize((adaptive_size, adaptive_size), Image.Resampling.LANCZOS)
        adaptive_img.save(folder_path / 'ic_launcher_foreground.png')

        # Save ic_launcher_round.png (Circle crop)
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        round_img = ImageOps.fit(img, (size, size), centering=(0.5, 0.5))
        round_img.putalpha(mask)
        round_img.save(folder_path / 'ic_launcher_round.png')
        
        print(f"Updated {folder}")

    # 3. Generate Android Splash Screens
    drawable_folders = [
        'drawable',
        'drawable-land-hdpi', 'drawable-land-mdpi', 'drawable-land-xhdpi', 
        'drawable-land-xxhdpi', 'drawable-land-xxxhdpi',
        'drawable-port-hdpi', 'drawable-port-mdpi', 'drawable-port-xhdpi', 
        'drawable-port-xxhdpi', 'drawable-port-xxxhdpi'
    ]

    bg_color = (34, 34, 34, 255)  # Dark grey

    for folder in drawable_folders:
        folder_path = android_res_path / folder
        if not folder_path.is_dir():
            continue
            
        is_land = 'land' in folder
        
        # Determine dimensions
        if is_land:
            width, height = 1920, 1080
        else:
            width, height = 1080, 1920
            
        splash_bg = Image.new('RGBA', (width, height), bg_color)
        
        # Resize logo to fit nicely (e.g. 1/3 of width)
        logo_width = int(min(width, height) * 0.4)
        logo_height = int(logo_width * img.height / img.width)
        
        resized_logo = img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Center paste
        paste_x = (width - logo_width) // 2
        paste_y = (height - logo_height) // 2
        
        splash_bg.paste(resized_logo, (paste_x, paste_y), resized_logo)
        
        splash_bg.save(folder_path / 'splash.png')
        print(f"Updated splash in {folder}")


if __name__ == "__main__":
    default_source = REPO_ROOT / 'assets' / 'mortar_calc_logo.png'
    source_img = sys.argv[1] if len(sys.argv) > 1 else str(default_source)
    update_icons(source_img)
