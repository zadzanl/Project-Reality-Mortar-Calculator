#!/bin/bash
# Build script for Android APK
# This script prepares the www directory and builds the Android APK

set -e  # Exit on error

echo "=================================="
echo "PR Mortar Calculator - Android Build"
echo "=================================="

# Clean previous build
echo "Cleaning previous build..."
rm -rf www/
rm -rf android/app/build/

# Create www directory structure
echo "Creating www directory..."
mkdir -p www

# Copy web assets
echo "Copying web assets..."
cp -r calculator/static www/
cp calculator/templates/index.html www/
cp -r processed_maps www/
cp mapsList.json www/

echo "Web assets copied successfully!"

# Fix paths for offline use (convert absolute paths to relative paths)
echo "Fixing paths for offline use..."
# Fix HTML file
sed -i 's|href="/static/|href="static/|g' www/index.html
sed -i 's|src="/static/|src="static/|g' www/index.html
sed -i 's|href="/favicon.ico"|href="favicon.ico"|g' www/index.html

# Fix JavaScript files
sed -i "s|'/maps/list'|'mapsList.json'|g" www/static/js/app.js
sed -i 's|`/maps/${|`processed_maps/${|g' www/static/js/app.js
sed -i "s|'/static/lib/images/|'static/lib/images/|g" www/static/js/app.js
sed -i 's|`/maps/${mapName}/|`processed_maps/${mapName}/|g' www/static/js/heightmap.js
sed -i 's|/maps/\[mapName\]/|processed_maps/\[mapName\]/|g' www/static/js/heightmap.js

echo "Paths updated for offline operation!"

# Sync with Capacitor
echo "Syncing with Capacitor..."
npx cap sync android

# Build APK
echo "Building Android APK..."
cd android
./gradlew assembleDebug

# Find and display APK location
echo ""
echo "=================================="
echo "BUILD SUCCESSFUL!"
echo "=================================="
echo ""
echo "APK Location:"
find app/build/outputs/apk -name "*.apk" -exec ls -lh {} \;
echo ""
echo "To install on device:"
echo "  adb install app/build/outputs/apk/debug/app-debug.apk"
echo ""
