# Project Reality Mortar Calculator

Calculate accurate firing solutions for mortars in Project Reality: BF2. Takes into account height deltas automatically. Support 1.8.1.2 (November 2025)

## Features

- Visual map representation with satellite/overview imagery
- Automatic elevation detection from heightmaps
- Firing solutions in Mils and Degrees
- Support for all 84 Project Reality maps (as of 20/11/2025)
- Completely offline operation

## Requirements

- Project Reality: BF2
- This repository cloned (shallow clone recommended)
- Python dependencies installed
    - Python 3.8 or newer
    - Flask 2.3+ and Werkzeug 2.3+ (auto-installed on first run)
- Modern web browser (Chrome, Firefox, Edge)

## **IMPORTANT: Shallow Clone Highly Recommended**

**DO NOT perform a full clone of this repository** - it's over 10GB due to (zipped) map files.

Use shallow clone command instead:
```bash
git clone --depth 3 https://github.com/zadzanl/Project_Reality-Mortar-Calculator
```

This fetch only the 3 latest commits.

Note: When performing whole history clone, some older commits in `raw_map_data/` may still contain large files that haven't been cleaned.

## Installation

### 1. Clone the repository:
```bash
git clone --depth 3 https://github.com/zadzanl/Project_Reality-Mortar-Calculator
cd Project_Reality-Mortar-Calculator
```

### 2. Install Python dependencies (optional - auto-installed):
```bash
pip install -r requirements.txt
```

### 3. Run the calculator:
```bash
run.bat         # Windows
./run.sh        # Linux/Mac
```

The calculator will open automatically at `http://localhost:8080` (if the port is unused).

## Usage

1. Select a map from the dropdown menu
2. Click "Load Map"
3. Choose mortar position using shift + click
4. Move target position pointer using
5. Click "Calculate Firing Solution" (or not, as it should be done automatically)
6. Read elevation in Mils (used in game) and Degrees (secondary)

## Updating Map List

### Steps:

1. Collect map files from your PR:BF2 installation using [collect_maps.py](processor/collect_maps.py):
   ```bash
   python processor/collect_maps.py
   ```

2. Process the maps (convert heightmaps to JSON):
   - Option A: Open and run `processor/process_maps.ipynb` in Jupyter Notebook
   - Option B: Run via command line:
     ```bash
     jupyter nbconvert --to notebook --execute --inplace processor\process_maps.ipynb
     ```

3. Verify processing by checking `processor/collection_report.txt`

4. Restart the calculator - new maps should be available (large map may show wrong grid scale)

## Project Structure

- `/calculator/` - Web application and Flask server
- `/processed_maps/` - Heightmap data (JSON) and minimap images (PNG) for all maps
- `/processor/` - Tools for processing new maps (heightmaps + minimaps)
- `/raw_map_data/` - Original map files from game (server.zip + client.zip)
- `run.bat` / `run.sh` - Launch scripts

## Documentation

- [calculator/README.md](calculator/README.md) - Frontend documentation
- [processor/README.md](processor/README.md) - Map processing guide
- [openspec/project.md](openspec/project.md) - Technical context

## License

MIT License - See [LICENSE](LICENSE) file

## Credits

- Previous mortar calculator projects:
  - [BiNoops's Mortar Calculator](https://github.com/BiNoopsGITHUB/PRBF2-Mortar-Calculator)
  - [Shemich's Mortar Calculator](https://github.com/Shemich/project-reality-mortar-calculator)
  - [Other Project Reality mortar calculators on GitHub](https://github.com/search?q=project%20reality%20mortar&type=repositories)

- Community:
  - PRID and the Project Reality community for the motivation (how inaccurate we play the mortar), feedback, and testing
  - All community members and developers who discussed and answered mortar mechanics and physics

- Development
  - GitHub Copilot for UI implementation assistance
