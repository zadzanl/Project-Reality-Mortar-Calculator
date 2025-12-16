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

REM Android aapt strips the .gz extension from packaged assets.
REM To keep heightmaps compressed in the APK, rename *.gz -> *.gzip in www/.
echo Renaming compressed heightmaps for Android packaging...
for /r www\processed_maps %%F in (*.gz) do (
	ren "%%F" "%%~nF.gzip"
)

echo Web assets copied successfully!

REM Fix paths for offline use (convert absolute paths to relative paths)
echo Fixing paths for offline use...
powershell -Command "(Get-Content www\index.html) -replace 'href=\"/static/', 'href=\"static/' -replace 'src=\"/static/', 'src=\"static/' -replace 'href=\"/favicon.ico\"', 'href=\"favicon.ico\"' | Set-Content www\index.html"
powershell -Command "(Get-Content www\static\js\app.js) -replace \"'/maps/list'\", \"'mapsList.json'\" -replace '`/maps/\${', '`processed_maps/${' -replace \"'/static/lib/images/\", \"'static/lib/images/\" | Set-Content www\static\js\app.js"
powershell -Command "(Get-Content www\static\js\heightmap.js) -replace '`/maps/\${mapName}/', '`processed_maps/${mapName}/' -replace '/maps/\[mapName\]/', 'processed_maps/[mapName]/' | Set-Content www\static\js\heightmap.js"

echo Paths updated for offline operation!

REM Sync with Capacitor
echo Syncing with Capacitor...
REM Ensure Node dependencies are installed so npx resolves local CLI
echo Installing Node dependencies (npm ci)...
call npm ci --no-audit --no-fund

REM Quick Java check (warn if not Java 21)
echo Checking Java version...

REM You can suppress this check entirely by setting SKIP_JAVA_CHECK=1
REM (useful for CI or if you manage JAVA_HOME elsewhere).
if defined SKIP_JAVA_CHECK goto JAVA_CHECK_DONE

REM 1) If JAVA_HOME already points to a Java 21 JDK, prefer it.
if defined JAVA_HOME (
	if exist "%JAVA_HOME%\bin\java.exe" (
		"%JAVA_HOME%\bin\java.exe" -version 2>java_ver.txt
		findstr "\"21\"" java_ver.txt >nul 2>&1
		del java_ver.txt 2>nul
		if not errorlevel 1 goto USE_JAVA_HOME_21
	)
)

REM 2) Check the currently active java on PATH.
java -version 2>java_ver.txt
findstr "\"21\"" java_ver.txt >nul 2>&1
del java_ver.txt 2>nul
if not errorlevel 1 (
	echo Java 21 detected - OK
	goto JAVA_CHECK_DONE
)

REM 3) Try to locate a Java 21 installation and temporarily use it for this build.
set "FOUND_JAVA_21="
for /d %%D in ("C:\Program Files\Java\jdk-21*" "C:\Program Files\Eclipse Adoptium\jdk-21*" "C:\Program Files\Microsoft\jdk-21*" "C:\Program Files\Zulu\zulu-21*" "C:\Program Files\BellSoft\LibericaJDK-21*" "C:\Program Files\Amazon Corretto\jdk21*") do (
	if exist "%%~fD\bin\java.exe" set "FOUND_JAVA_21=%%~fD"
)

if defined FOUND_JAVA_21 (
	"%FOUND_JAVA_21%\bin\java.exe" -version 2>java_ver.txt
	findstr "\"21\"" java_ver.txt >nul 2>&1
	del java_ver.txt 2>nul
	if not errorlevel 1 goto USE_FOUND_JAVA_21
)

REM 4) Still not on Java 21. Warn, but do not block CI builds with an interactive pause.
echo WARNING: Java 21 not detected as the active JDK. This project targets Java 21 for Android builds.
echo If you have multiple JDKs installed (e.g. Java 25), set JAVA_HOME to your JDK 21 directory.
echo To silence this check, set SKIP_JAVA_CHECK=1.
if /I "%CI%"=="true" goto JAVA_CHECK_DONE
echo Continuing build may fail. Press any key to continue or Ctrl-C to abort.
pause

goto JAVA_CHECK_DONE

:USE_JAVA_HOME_21
set "PATH=%JAVA_HOME%\bin;%PATH%"
echo Using Java 21 from JAVA_HOME: %JAVA_HOME%
goto JAVA_CHECK_DONE

:USE_FOUND_JAVA_21
set "JAVA_HOME=%FOUND_JAVA_21%"
set "PATH=%JAVA_HOME%\bin;%PATH%"
echo Found and selected Java 21 at: %JAVA_HOME%
goto JAVA_CHECK_DONE

:JAVA_CHECK_DONE

REM Check Android SDK presence
if not defined ANDROID_HOME (
	if not exist android\local.properties (
		echo WARNING: Android SDK location not found. Set ANDROID_HOME or create android\\local.properties with sdk.dir=C:\path\to\android\sdk
	)
)

call npx cap sync android

REM Build APK
echo Building Android APK...
cd android
call gradlew.bat assembleDebug
if ERRORLEVEL 1 (
	echo.
	echo ==================================
	echo BUILD FAILED!
	echo ==================================
	exit /b %ERRORLEVEL%
)
cd ..

REM Display completion message
echo.
echo ==================================
echo BUILD SUCCESSFUL!
echo ==================================
echo.
echo APK Location: android\app\build\outputs\apk\debug\pr-mortar-calc-debug.apk
echo.
echo To install on device:
echo   adb install android\app\build\outputs\apk\debug\pr-mortar-calc-debug.apk
echo.

pause
