#!/bin/bash
# Build script for Android APK
# This script prepares the www directory and builds the Android APK

set -e  # Exit on error

echo "=================================="
echo "PR Mortar Calculator - Android Build"
echo "=================================="

# Check Java version and set JAVA_HOME if needed
echo "Checking Java version..."
JAVA_VERSION=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)

if [ "$JAVA_VERSION" != "21" ]; then
  echo "WARNING: Java $JAVA_VERSION is currently active, but Java 21 is required."
  echo "Attempting to find Java 21..."
  
  # Try common Java 21 installation locations
  JAVA_21_PATHS=(
    "/usr/lib/jvm/java-21-openjdk-amd64"
    "/usr/lib/jvm/java-1.21.0-openjdk-amd64"
    "/usr/lib/jvm/temurin-21-jdk-amd64"
    "/usr/lib/jvm/java-21"
    "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
    "/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home"
  )
  
  FOUND_JAVA_21=false
  for path in "${JAVA_21_PATHS[@]}"; do
    if [ -d "$path" ] && [ -x "$path/bin/java" ]; then
      export JAVA_HOME="$path"
      export PATH="$JAVA_HOME/bin:$PATH"
      FOUND_JAVA_21=true
      echo "Found Java 21 at: $JAVA_HOME"
      break
    fi
  done
  
  if [ "$FOUND_JAVA_21" = false ]; then
    echo ""
    echo "ERROR: Java 21 could not be found."
    echo "Please install JDK 21 and set JAVA_HOME to point to it."
    echo ""
    echo "Example:"
    echo "  export JAVA_HOME=/path/to/jdk-21"
    echo "  export PATH=\$JAVA_HOME/bin:\$PATH"
    exit 1
  fi
else
  echo "Java 21 detected - OK"
  # Always ensure JAVA_HOME points to Java 21 for Gradle
  JAVA_BIN=$(which java)
  DETECTED_JAVA_HOME=$(readlink -f "$JAVA_BIN" 2>/dev/null | sed 's:/bin/java::' || dirname $(dirname "$JAVA_BIN"))
  
  if [ "$JAVA_HOME" != "$DETECTED_JAVA_HOME" ]; then
    echo "Updating JAVA_HOME to match active Java 21"
    export JAVA_HOME="$DETECTED_JAVA_HOME"
  fi
  echo "JAVA_HOME: $JAVA_HOME"
fi
echo ""

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

# Detect OS for sed compatibility and define a function
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS requires empty string after -i
  sed_inplace() {
    sed -i '' "$@"
  }
else
  # Linux/Unix
  sed_inplace() {
    sed -i "$@"
  }
fi

# Fix HTML file
sed_inplace 's|href="/static/|href="static/|g' www/index.html
sed_inplace 's|src="/static/|src="static/|g' www/index.html
sed_inplace 's|href="/favicon.ico"|href="favicon.ico"|g' www/index.html

# Fix JavaScript files
sed_inplace "s|'/maps/list'|'mapsList.json'|g" www/static/js/app.js
sed_inplace 's|`/maps/${|`processed_maps/${|g' www/static/js/app.js
sed_inplace "s|'/static/lib/images/|'static/lib/images/|g" www/static/js/app.js
sed_inplace 's|`/maps/${mapName}/|`processed_maps/${mapName}/|g' www/static/js/heightmap.js
sed_inplace 's|/maps/\[mapName\]/|processed_maps/\[mapName\]/|g' www/static/js/heightmap.js

echo "Paths updated for offline operation!"

# Sync with Capacitor
echo "Syncing with Capacitor..."
# Ensure Node dependencies are installed so cap CLI resolves locally
echo "Installing Node dependencies (npm ci)..."
npm ci --no-audit --no-fund

# Check Android SDK presence
if [ -z "$ANDROID_HOME" ] && [ ! -f "android/local.properties" ]; then
  echo "WARNING: ANDROID_HOME not set and android/local.properties not found."
  echo "Please set ANDROID_HOME or create android/local.properties with sdk.dir=/path/to/android/sdk"
fi

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
echo "  adb install app/build/outputs/apk/debug/pr-mortar-calc-debug.apk"
echo ""
