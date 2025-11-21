# Deployment and Distribution Specification

## ADDED Requirements

### Requirement: Portable Executable Distribution

The system SHALL provide standalone executable distributions that bundle all dependencies, allowing users to run the calculator without installing Python or any libraries.

#### Scenario: Windows user downloads executable
- **WHEN** user downloads `PR-Mortar-Calculator-Windows.zip` from GitHub Releases
- **AND** extracts archive to any folder
- **AND** double-clicks `PR-Mortar-Calculator.exe`
- **THEN** server starts and opens browser automatically
- **AND** all map data loads correctly
- **AND** no Python installation is required

#### Scenario: Linux user downloads executable
- **WHEN** user downloads `PR-Mortar-Calculator-Linux.tar.gz`
- **AND** extracts: `tar -xzf PR-Mortar-Calculator-Linux.tar.gz`
- **AND** runs: `./PR-Mortar-Calculator/PR-Mortar-Calculator`
- **THEN** server starts on port 8080
- **AND** user can access calculator at `http://localhost:8080`
- **AND** all features work identically to Python version

#### Scenario: Portable installation
- **WHEN** user copies extracted folder to USB drive or different machine
- **AND** runs executable from new location
- **THEN** calculator works without reconfiguration
- **AND** all paths resolve correctly relative to executable

### Requirement: PyInstaller Build Configuration

The system SHALL include PyInstaller specification file that correctly bundles all application components and dependencies.

#### Scenario: Build with PyInstaller
- **WHEN** developer runs `pyinstaller PR-Mortar-Calculator.spec`
- **THEN** build completes without errors
- **AND** output folder `dist/PR-Mortar-Calculator/` contains executable
- **AND** all templates, static files, and map data are included
- **AND** Flask, Werkzeug, and Pillow dependencies are bundled
- **AND** executable size is under 150 MB (uncompressed)

#### Scenario: Bundle data files
- **WHEN** PyInstaller packages application
- **THEN** includes `calculator/templates/` directory
- **AND** includes `calculator/static/` directory with all subdirectories
- **AND** includes `processed_maps/` with all map heightmaps and minimaps
- **AND** preserves directory structure relative to executable

#### Scenario: Frozen path detection
- **WHEN** application runs as PyInstaller executable
- **THEN** detects frozen state via `sys.frozen` attribute
- **AND** uses `sys._MEIPASS` for temporary extraction path
- **AND** resolves map data relative to parent of extraction path
- **AND** Flask correctly serves static files and templates

### Requirement: Automated GitHub Actions Build

The system SHALL provide GitHub Actions workflow that builds cross-platform executables and creates releases with manual trigger control.

#### Scenario: Manual workflow trigger
- **WHEN** maintainer navigates to Actions tab
- **AND** selects "Build Portable Executable" workflow
- **AND** clicks "Run workflow" button
- **AND** enters version (e.g., `v1.0.0`)
- **AND** clicks "Run workflow"
- **THEN** workflow starts building Windows and Linux executables in parallel

#### Scenario: Successful build and release
- **WHEN** workflow completes successfully
- **THEN** creates GitHub Release with specified version tag
- **AND** attaches `PR-Mortar-Calculator-Windows.zip` to release
- **AND** attaches `PR-Mortar-Calculator-Linux.tar.gz` to release
- **AND** generates release notes from recent commits
- **AND** publishes release (not draft)
- **AND** workflow summary shows download links

#### Scenario: Build matrix execution
- **WHEN** workflow runs
- **THEN** builds on `windows-latest` runner
- **AND** builds on `ubuntu-latest` runner
- **AND** both builds execute in parallel
- **AND** Windows build creates ZIP archive
- **AND** Linux build creates tar.gz archive
- **AND** each build completes in under 10 minutes

#### Scenario: Build artifact retention
- **WHEN** workflow completes
- **THEN** artifacts are retained for 90 days
- **AND** artifacts are available for download from workflow run page
- **AND** artifacts automatically attach to created release

### Requirement: Version Management

The system SHALL include version identifier in application that displays at startup and can be queried programmatically.

#### Scenario: Version display at startup
- **WHEN** user starts calculator (Python or executable)
- **THEN** startup banner displays version number
- **AND** format is: "Version X.Y.Z"
- **AND** version matches `__version__` in `server.py`

#### Scenario: Version update process
- **WHEN** maintainer releases new version
- **THEN** increments `__version__` in `calculator/server.py`
- **AND** commits version change to repository
- **AND** triggers GitHub Actions workflow with matching version tag
- **AND** workflow creates release with that version

### Requirement: Distribution Package Format

The system SHALL provide compressed distribution packages optimized for download and extraction on target platforms.

#### Scenario: Windows distribution package
- **WHEN** Windows build completes
- **THEN** creates ZIP archive using 7-Zip compression
- **AND** archive name is `PR-Mortar-Calculator-Windows.zip`
- **AND** archive size is 70-90 MB
- **AND** archive extracts to single `PR-Mortar-Calculator/` folder
- **AND** executable is `PR-Mortar-Calculator/PR-Mortar-Calculator.exe`

#### Scenario: Linux distribution package
- **WHEN** Linux build completes
- **THEN** creates tar.gz archive with gzip compression
- **AND** archive name is `PR-Mortar-Calculator-Linux.tar.gz`
- **AND** archive size is 80-100 MB
- **AND** archive extracts to single `PR-Mortar-Calculator/` folder
- **AND** executable is `PR-Mortar-Calculator/PR-Mortar-Calculator`

#### Scenario: Package contents verification
- **WHEN** user extracts distribution package
- **THEN** folder contains executable file
- **AND** folder contains `calculator/` subdirectory
- **AND** folder contains `processed_maps/` subdirectory
- **AND** folder contains Python runtime libraries
- **AND** no unnecessary files or build artifacts are included

### Requirement: Local Build Support

The system SHALL allow developers to build executables locally for testing before triggering automated builds.

#### Scenario: Local build execution
- **WHEN** developer has Python 3.11+ installed
- **AND** runs `pip install -r requirements.txt`
- **AND** runs `pyinstaller PR-Mortar-Calculator.spec`
- **THEN** build completes in under 5 minutes
- **AND** output is in `dist/PR-Mortar-Calculator/`
- **AND** executable runs correctly when tested
- **AND** build artifacts in `build/` can be safely deleted

#### Scenario: Build verification
- **WHEN** developer builds locally
- **AND** runs `dist/PR-Mortar-Calculator/PR-Mortar-Calculator`
- **THEN** server starts without errors
- **AND** browser opens automatically
- **AND** map selection works correctly
- **AND** all 84+ maps load successfully
- **AND** ballistics calculations produce correct results

### Requirement: Build Documentation

The system SHALL provide comprehensive documentation for building and distributing executables.

#### Scenario: Documentation completeness
- **WHEN** developer reads `BUILD.md`
- **THEN** understands how to trigger GitHub Actions workflow
- **AND** understands how to build locally
- **AND** knows how to troubleshoot common build errors
- **AND** knows how to update version number
- **AND** knows how to distribute packages to users

#### Scenario: User instructions included
- **WHEN** user downloads executable
- **THEN** `BUILD.md` explains extraction process
- **AND** explains how to run executable on Windows
- **AND** explains how to run executable on Linux
- **AND** explains what to do if antivirus flags executable

## MODIFIED Requirements

### Requirement: Flask Server Path Resolution (from web-server)

**MODIFIED:** Updated path resolution to support both normal Python execution and PyInstaller bundled execution.

The system SHALL resolve file paths correctly whether running as Python script or as PyInstaller executable.

#### Scenario: Python script execution
- **WHEN** server runs via `python calculator/server.py`
- **THEN** `PROJECT_ROOT` resolves to repository root
- **AND** `PROCESSED_MAPS_DIR` points to `{repo_root}/processed_maps/`
- **AND** Flask serves templates from `calculator/templates/`
- **AND** Flask serves static files from `calculator/static/`

#### Scenario: PyInstaller executable execution
- **WHEN** server runs as `PR-Mortar-Calculator.exe` or `PR-Mortar-Calculator`
- **AND** `sys.frozen` is True
- **THEN** `APPLICATION_PATH` resolves to PyInstaller temporary extraction path
- **AND** `PROJECT_ROOT` resolves to parent of extraction path
- **AND** `PROCESSED_MAPS_DIR` points to bundled `processed_maps/`
- **AND** Flask serves templates from bundled `calculator/templates/`
- **AND** Flask serves static files from bundled `calculator/static/`

## Design Notes

### Why Manual Workflow Trigger?

- Game updates infrequently (quarterly or less)
- Application is still in beta phase
- Maintainer needs granular control over releases
- Allows testing before creating public release
- Avoids accidental releases from development commits

### Why Folder Distribution (not single-file)?

- **Faster startup:** No extraction delay on each run
- **Smaller size:** Dependencies shared between files
- **User-friendly:** Maps and assets visible in folder
- **Easier debugging:** Can inspect bundled files
- **Better performance:** No temporary file overhead

### Why No macOS Support?

- No identified macOS users in community
- GitHub Actions macOS runners cost more
- Can be added later if needed

### PyInstaller Exclusions

The spec file excludes heavy unused modules:
- `tkinter` - GUI toolkit (not used)
- `matplotlib` - Plotting library (not used)
- `scipy` - Scientific computing (not used)
- `numpy` - Not required (only used in processor)
- `pandas` - Not required

This reduces executable size by ~40-50 MB.

### Path Resolution Strategy

**Normal Python execution:**
```python
PROJECT_ROOT = Path(__file__).parent.parent
# /home/user/PR-Calculator/calculator/server.py
# PROJECT_ROOT = /home/user/PR-Calculator/
```

**PyInstaller execution:**
```python
APPLICATION_PATH = Path(sys._MEIPASS)  # Temp extraction
PROJECT_ROOT = APPLICATION_PATH.parent  # User's install folder
# sys._MEIPASS = /tmp/_MEIxxxxxx/
# PROJECT_ROOT = /home/user/PR-Calculator/
```

### Compression Choice

- **Windows:** ZIP format (native Windows support)
- **Linux:** tar.gz (standard Unix format)
- Both achieve ~50-60% compression ratio

## Testing Checklist

Before releasing new version:

- [ ] Increment `__version__` in `server.py`
- [ ] Test local build: `pyinstaller PR-Mortar-Calculator.spec`
- [ ] Run built executable locally
- [ ] Verify all maps load correctly
- [ ] Verify ballistics calculations work
- [ ] Verify browser auto-opens
- [ ] Commit version change to main branch
- [ ] Trigger GitHub Actions workflow
- [ ] Wait for build completion (~10 min)
- [ ] Download Windows ZIP from release
- [ ] Download Linux tar.gz from release
- [ ] Test both archives on respective platforms
- [ ] Update release notes if needed

## Future Considerations

Potential enhancements for future versions:

1. **Code Signing:**
   - Windows: Authenticode certificate
   - Linux: GPG signature
   - Requires paid certificate or self-signed setup

2. **Auto-Update:**
   - Check GitHub API for new releases
   - Download and replace executable
   - Requires update framework integration

3. **Single-File Option:**
   - Alternative spec file for single `.exe`
   - Trade-off: Slower startup (~5-10 seconds)
   - Simpler distribution (one file)

4. **Application Icon:**
   - Create `.ico` (Windows) and `.png` (Linux)
   - Add to PyInstaller spec: `icon='path/to/icon.ico'`
   - Branding and professionalism

5. **macOS Support:**
   - Add `macos-latest` to build matrix
   - Create `.app` bundle
   - Handle code signing requirements

6. **Installer Creation:**
   - Windows: NSIS or Inno Setup
   - Linux: AppImage or Snap package
   - macOS: DMG with drag-to-Applications

## References

- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Flask Deployment Options](https://flask.palletsprojects.com/en/latest/deploying/)
- [softprops/action-gh-release](https://github.com/softprops/action-gh-release)
