# Project Reality Mortar Calculator - Android App

This document describes how to build and use the Android version of the PR Mortar Calculator.

## Overview

The Android app is a WebView wrapper that bundles the web-based mortar calculator for offline use on Android devices. It uses **Capacitor** to wrap the web application and package it as a native Android APK.

## Features

- ✅ **100% Offline** - All maps and assets are bundled in the APK
- ✅ **Mobile Optimized** - Viewport configured for mobile screens
- ✅ **All 84 Maps** - Includes all Project Reality maps with heightmap data
- ✅ **Native Performance** - Uses Android WebView for efficient rendering
- ✅ **Dark Mode Support** - Same dark/light theme toggle as web version

## Requirements

### For Building the APK

1. **Java Development Kit (JDK) 21**
   - Required by Capacitor 7.x
   - Download: [OpenJDK 21](https://adoptium.net/) or use system package manager
   - Ensure `JAVA_HOME` environment variable is set and points to JDK 21
   - Verify installation: `java -version` should show version 21

2. **Android SDK**
   - Android Studio (recommended) OR
   - Command-line Android SDK tools
   - Minimum SDK: API 23 (Android 6.0)
   - Target SDK: API 35

3. **Node.js and npm**
   - Node.js 16+ recommended
   - npm is included with Node.js

4. **Gradle**
   - Included with the Android project (gradlew wrapper)

### For Installing the APK

- Android device running Android 6.0 (API 23) or higher
- ~400 MB of free storage space (APK is ~377 MB due to map data)
- Developer mode enabled (for sideloading)

## Building the Android APK

### Quick Build (Recommended)

We provide automated build scripts for easy APK generation:

#### On Linux/macOS:
```bash
./build-android.sh
```

#### On Windows:
```batch
build-android.bat
```

These scripts will:
1. Clean previous builds
2. Copy web assets to `www/` directory
3. Sync assets with Capacitor
4. Build the debug APK

### GitHub Actions (CI/CD)

The repository includes a GitHub Actions workflow that automatically builds the APK:

1. Go to the **Actions** tab in the GitHub repository
2. Select **Build Android APK** workflow
3. Click **Run workflow**
4. Enter a version tag (e.g., `v1.0.0`)
5. Click **Run workflow**

The workflow will:
- Build the APK with Java 21 and Node.js 20
- Run verification checks
- Upload the APK as an artifact
- Create a GitHub Release with the APK attached

**Workflow file:** `.github/workflows/build-android.yml`

### Manual Build Steps

If you prefer to build manually or need to troubleshoot:

#### 1. Install Dependencies
```bash
npm install
```

#### 2. Prepare Web Assets
```bash
# Create www directory
mkdir -p www

# Copy calculator files
cp -r calculator/static www/
cp calculator/templates/index.html www/
cp -r processed_maps www/
cp mapsList.json www/
```

#### 3. Sync with Capacitor
```bash
npx cap sync android
```

#### 4. Build the APK
```bash
cd android
./gradlew assembleDebug    # Linux/macOS
gradlew.bat assembleDebug  # Windows
```

#### 5. Locate the APK
The built APK will be at:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

## Installing on Android Device

### Method 1: USB Installation (Recommended)

1. **Enable Developer Options** on your Android device:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings → Developer Options
   - Enable "USB Debugging"

2. **Connect your device** via USB

3. **Install using ADB**:
   ```bash
   adb install android/app/build/outputs/apk/debug/app-debug.apk
   ```

### Method 2: Direct Transfer

1. Copy the APK file to your device (via USB, cloud storage, etc.)
2. Open the APK file on your device
3. Allow installation from unknown sources if prompted
4. Tap "Install"

## Using the App

The Android app functions identically to the web version:

1. **Launch the app** - Opens to the map selection screen
2. **Select a map** - Choose from 84 available maps
3. **Load the map** - Click "Load Map" button
4. **Place mortar** - Shift + tap on the map
5. **Place target** - Regular tap on the map
6. **View solution** - Calculations are automatic
7. **Read elevation** - Use the displayed mils value in-game

### Mobile-Specific Features

- **Pinch to zoom** - Works on the map
- **Drag markers** - Touch and hold, then drag
- **Dark mode** - Toggle in the header
- **Grid overlay** - Toggle for coordinate reference

## App Configuration

Key configuration files:

- **capacitor.config.json** - Capacitor settings
  - App ID: `com.projectreality.mortarcalculator`
  - App Name: PR Mortar Calculator
  - Web directory: `www`

- **android/variables.gradle** - Android SDK versions
  - Min SDK: 23 (Android 6.0)
  - Target SDK: 35
  - Compile SDK: 35

- **android/app/build.gradle** - Build configuration
  - Java version: 21
  - Kotlin stdlib: 1.9.0

## Troubleshooting

### Build Errors

**"Invalid source release: 21"**
- Install JDK 21 (not JDK 17 or lower)
- Set JAVA_HOME environment variable to point to JDK 21 installation
- On Linux/macOS: `export JAVA_HOME=/path/to/jdk-21`
- On Windows: Set system environment variable `JAVA_HOME=C:\path\to\jdk-21`
- Verify with: `java -version` and `echo $JAVA_HOME` (or `echo %JAVA_HOME%` on Windows)

**"Duplicate class kotlin.xxx"**
- Already fixed in build.gradle with dependency resolution
- Clean build: `cd android && ./gradlew clean`

**"SDK location not found"**
- Set ANDROID_HOME environment variable
- OR create `android/local.properties` with:
  ```
  sdk.dir=/path/to/android/sdk
  ```

### Runtime Errors

**"App crashes on launch"**
- Check Android version (must be 6.0+)
- Check available storage (~400 MB needed)
- Clear app data and reinstall

**"Maps don't load"**
- Ensure `processed_maps/` was copied to `www/`
- Rebuild with `npx cap sync android`

**"Calculations are wrong"**
- File an issue on GitHub - the calculation logic is the same as the web version

## Building Release APK

For production releases (smaller size, signed):

1. **Generate signing key**:
   ```bash
   keytool -genkey -v -keystore my-release-key.keystore -keyalg RSA -keysize 2048 -validity 10000 -alias my-key-alias
   ```

2. **Configure signing** in `android/app/build.gradle`:
   ```gradle
   android {
       signingConfigs {
           release {
               storeFile file("my-release-key.keystore")
               storePassword "your-password"
               keyAlias "my-key-alias"
               keyPassword "your-password"
           }
       }
       buildTypes {
           release {
               signingConfig signingConfigs.release
               minifyEnabled true
               proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
           }
       }
   }
   ```

3. **Build release APK**:
   ```bash
   cd android
   ./gradlew assembleRelease
   ```

4. **Locate release APK**:
   ```
   android/app/build/outputs/apk/release/app-release.apk
   ```

## Project Structure

```
Project-Reality-Mortar-Calculator/
├── android/                      # Android project (Capacitor)
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── assets/public/    # Web assets (auto-copied)
│   │   │   ├── java/             # MainActivity
│   │   │   └── res/              # Android resources
│   │   └── build.gradle          # App build configuration
│   ├── gradle/                   # Gradle wrapper
│   ├── build.gradle              # Root build configuration
│   └── variables.gradle          # SDK versions
├── calculator/                   # Web app source
│   ├── static/                   # CSS, JS, images
│   └── templates/                # HTML files
├── processed_maps/               # Map data (JSON + images)
├── www/                          # Web build output (gitignored)
├── capacitor.config.json         # Capacitor configuration
├── build-android.sh              # Build script (Linux/Mac)
└── build-android.bat             # Build script (Windows)
```

## Technical Details

### Technologies Used

- **Capacitor 7.0** - Native wrapper framework
- **Android WebView** - Web rendering engine
- **Leaflet.js** - Map library (bundled locally)
- **Gradle 8.11** - Build system
- **Java 21** - Required by Capacitor 7

### Offline Operation

All assets are bundled locally:
- HTML, CSS, JavaScript files
- Leaflet.js library and images
- All 84 map heightmaps (JSON format)
- Minimap images for each map
- Contour maps where available

No network requests are made after installation.

### Mobile Optimizations

The viewport meta tag is configured for optimal mobile display:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
```

This ensures:
- Proper scaling on all screen sizes
- Prevents accidental zoom
- Covers full screen including notches

### App Size

The APK is large (~377 MB) because it includes:
- 84 maps × ~4-5 MB each (heightmaps + minimaps)
- Total of ~350 MB of map data
- Additional overhead from Android libraries

This is intentional for offline operation.

## Performance

- **Launch time**: < 3 seconds on modern devices
- **Map load time**: 2-5 seconds depending on map size
- **Calculation time**: < 100ms (instant)
- **Memory usage**: ~150-300 MB (varies by map)

## Known Limitations

1. **Large APK size** - Required for offline maps
2. **Android only** - iOS version not yet implemented
3. **Portrait orientation** - Landscape works but not optimized
4. **No auto-update** - Manual APK installation required

## Future Enhancements

Potential improvements for future versions:

- [ ] iOS support (using Capacitor)
- [ ] Landscape layout optimization
- [ ] Reduce APK size (compression, on-demand map download)
- [ ] In-app update mechanism
- [ ] Export/import firing solutions
- [ ] Multiple mortar positions
- [ ] Trajectory visualization

## Support

For issues or questions:

1. Check this documentation
2. Check the main README.md
3. Review existing GitHub issues
4. Open a new issue with:
   - Android version
   - Device model
   - Error messages
   - Steps to reproduce

## License

Same as the main project - MIT License

## Credits

- Capacitor team for the excellent wrapper framework
- Android WebView team for the rendering engine
- All contributors to the web version
