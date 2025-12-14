# Project Reality Mortar Calculator - Android Build

This directory contains the Android Studio project files to build the APK.

## Prerequisites

- Android Studio or command-line SDK tools
- Python 3 (to prepare assets)

## Build Instructions

1. **Prepare Assets:**
   Run the preparation script from the repository root to copy and patch the web assets.

   ```bash
   # From repo root
   python3 prepare_android_assets.py
   # NOTE: By default this may limit map copying in dev environment.
   # Ensure the script copies ALL maps for production build.
   ```

2. **Open in Android Studio:**
   - Open `android_app` directory as an existing project.
   - Sync Gradle.

3. **Build APK:**
   - Go to `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
   - The APK will be generated in `app/build/outputs/apk/debug/`.

## Structure

- `app/src/main/assets/www`: Contains the web application (HTML, JS, CSS, Maps).
- `app/src/main/java`: Contains the WebView wrapper code (`MainActivity.java`).
- `prepare_android_assets.py`: Script to generate the `www` folder content.

## Key Configurations

- **Offline Mode:** All assets are loaded from `file:///android_asset/`.
- **Gzip Support:** The app expects `.gz` compressed heightmaps to save space. Android WebView handles this automatically via `DecompressionStream` in `heightmap.js`.
- **Permissions:** `INTERNET` permission is declared but not strictly required for offline mode; `FileAccess` is enabled in WebView settings.
