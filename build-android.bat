@echo off
REM Build script for Android APK (Windows)
REM This script prepares the www directory and builds the Android APK

echo ==================================
echo PR Mortar Calculator - Android Build
echo ==================================

REM Clean previous build
echo Cleaning previous build...
if exist www rmdir /s /q www
if exist android\app\build rmdir /s /q android\app\build

REM Create www directory structure
echo Creating www directory...
mkdir www

REM Copy web assets
echo Copying web assets...
xcopy /E /I /Y calculator\static www\static
copy /Y calculator\templates\index.html www\
xcopy /E /I /Y processed_maps www\processed_maps
copy /Y mapsList.json www\

echo Web assets copied successfully!

REM Fix paths for offline use (convert absolute paths to relative paths)
echo Fixing paths for offline use...
powershell -Command "(Get-Content www\index.html) -replace 'href=\"/static/', 'href=\"static/' -replace 'src=\"/static/', 'src=\"static/' -replace 'href=\"/favicon.ico\"', 'href=\"favicon.ico\"' | Set-Content www\index.html"
powershell -Command "(Get-Content www\static\js\app.js) -replace \"'/maps/list'\", \"'mapsList.json'\" -replace '`/maps/\${', '`processed_maps/${' -replace \"'/static/lib/images/\", \"'static/lib/images/\" | Set-Content www\static\js\app.js"
powershell -Command "(Get-Content www\static\js\heightmap.js) -replace '`/maps/\${mapName}/', '`processed_maps/${mapName}/' -replace '/maps/\[mapName\]/', 'processed_maps/[mapName]/' | Set-Content www\static\js\heightmap.js"

echo Paths updated for offline operation!

REM Sync with Capacitor
echo Syncing with Capacitor...
call npx cap sync android

REM Build APK
echo Building Android APK...
cd android
call gradlew.bat assembleDebug
cd ..

REM Display completion message
echo.
echo ==================================
echo BUILD SUCCESSFUL!
echo ==================================
echo.
echo APK Location: android\app\build\outputs\apk\debug\app-debug.apk
echo.
echo To install on device:
echo   adb install android\app\build\outputs\apk\debug\app-debug.apk
echo.

pause
