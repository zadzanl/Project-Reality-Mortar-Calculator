import os
from PIL import Image, ImageDraw, ImageOps

def update_icons(source_path):
    if not os.path.exists(source_path):
        print(f"Error: Source image {source_path} not found.")
        return

    img = Image.open(source_path)
    
    # Ensure image is RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # 1. Generate Favicons (Web & Desktop)
    print("Generating favicons...")
    favicon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Web favicon (offline build)
    www_path = os.path.join('www', 'favicon.ico')
    img.save(www_path, format='ICO', sizes=favicon_sizes)
    print(f"Saved {www_path}")

    # Desktop icon
    static_path = os.path.join('calculator', 'static')
    os.makedirs(static_path, exist_ok=True)
    desktop_icon_path = os.path.join(static_path, 'icon.ico')
    img.save(desktop_icon_path, format='ICO', sizes=favicon_sizes)
    print(f"Saved {desktop_icon_path}")

    # Flask favicon (served by server.py)
    flask_favicon_path = os.path.join(static_path, 'favicon.ico')
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

    android_res_path = os.path.join('android', 'app', 'src', 'main', 'res')

    for folder, size in mipmap_sizes.items():
        folder_path = os.path.join(android_res_path, folder)
        os.makedirs(folder_path, exist_ok=True)

        # Resize for standard icon
        resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save ic_launcher.png
        resized_img.save(os.path.join(folder_path, 'ic_launcher.png'))
        
        # Save ic_launcher_foreground.png (for adaptive)
        # Usually foreground is 108x108 for 48x48 icon (approx 2.25x)
        # But here we just replace the existing file which is likely the icon content
        # We'll make it slightly larger to account for masking if needed, or just same size?
        # Adaptive foregrounds are usually 108dp. 
        # mdpi 1dp = 1px -> 108px
        # hdpi 1.5x -> 162px
        # xhdpi 2x -> 216px
        # xxhdpi 3x -> 324px
        # xxxhdpi 4x -> 432px
        
        adaptive_size = int(size * 108 / 48) # Scale based on 48dp base
        adaptive_img = img.resize((adaptive_size, adaptive_size), Image.Resampling.LANCZOS)
        adaptive_img.save(os.path.join(folder_path, 'ic_launcher_foreground.png'))

        # Save ic_launcher_round.png (Circle crop)
        # Create mask
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        round_img = ImageOps.fit(img, (size, size), centering=(0.5, 0.5))
        round_img.putalpha(mask)
        round_img.save(os.path.join(folder_path, 'ic_launcher_round.png'))
        
        print(f"Updated {folder}")

    # 3. Generate Android Splash Screens
    # We will generate a centered logo on a transparent (or white) background
    # For simplicity, we'll just save the logo as splash.png in all drawable folders
    # and let Android handle the background color (defined in styles.xml or layout)
    
    drawable_folders = [
        'drawable',
        'drawable-land-hdpi', 'drawable-land-mdpi', 'drawable-land-xhdpi', 
        'drawable-land-xxhdpi', 'drawable-land-xxxhdpi',
        'drawable-port-hdpi', 'drawable-port-mdpi', 'drawable-port-xhdpi', 
        'drawable-port-xxhdpi', 'drawable-port-xxxhdpi'
    ]

    # Base splash size (e.g. 512x512) - Android will center it if using layer-list, 
    # but if it's a direct bitmap background, it might stretch.
    # The existing style uses <item name="android:background">@drawable/splash</item>
    # If it's a simple bitmap, it stretches.
    # So we MUST generate a full-screen image.
    
    # Background color: Let's pick a color from the logo or default to dark/white?
    # I'll use a dark grey #222222 to match the app theme, or just transparent if the logo handles it.
    # Let's assume the logo has transparency.
    
    bg_color = (34, 34, 34, 255) # Dark grey
    
    for folder in drawable_folders:
        folder_path = os.path.join(android_res_path, folder)
        if not os.path.exists(folder_path):
            continue
            
        is_land = 'land' in folder
        
        # Determine dimensions
        if is_land:
            width, height = 1920, 1080
        else:
            width, height = 1080, 1920
            
        # Adjust for density if we want to be fancy, but fixed high-res is usually fine for splash
        # or we can just save the logo itself and hope the layout centers it?
        # If the current implementation is just `android:background="@drawable/splash"`, it WILL stretch.
        # So we MUST generate a full-screen image.
        
        splash_bg = Image.new('RGBA', (width, height), bg_color)
        
        # Resize logo to fit nicely (e.g. 1/3 of width)
        logo_width = int(min(width, height) * 0.4)
        logo_height = int(logo_width * img.height / img.width)
        
        resized_logo = img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Center paste
        paste_x = (width - logo_width) // 2
        paste_y = (height - logo_height) // 2
        
        splash_bg.paste(resized_logo, (paste_x, paste_y), resized_logo)
        
        splash_bg.save(os.path.join(folder_path, 'splash.png'))
        print(f"Updated splash in {folder}")

if __name__ == "__main__":
    update_icons('mortar_calc_logo.png')
