# Project Reality Mortar Calculator

Calculate accurate firing solutions for mortars in Project Reality: BF2.

## Quick Start

**Windows:**
```bash
run.bat
```

**Linux/Mac:**
```bash
./run.sh
```

The calculator opens automatically at `http://localhost:8080`

## Requirements

- Python 3.8 or newer
- Flask 2.3+ and Werkzeug 2.3+ (auto-installed on first run)
- Modern web browser (Chrome, Firefox, Edge)

## Features

- Automatic elevation detection from heightmaps
- High-angle firing solutions in Mils and Degrees
- Support for 80+ Project Reality maps
- Grid coordinate system (A-M columns, 1-13 rows, keypad 1-9)
- Completely offline operation
- One-click launch

## Installation

1. Clone the repository:
```bash
git clone https://github.com/zadzanl/Project_Reality-Mortar-Calculator.git
cd Project_Reality-Mortar-Calculator
```

2. Install Python dependencies (optional - auto-installed):
```bash
pip install -r requirements.txt
```

3. Run the calculator:
```bash
run.bat         # Windows
./run.sh        # Linux/Mac
```

## Usage

1. Select a map from the dropdown menu
2. Click "Load Map"
3. Choose mortar position using dropdowns (Column, Row, Keypad)
4. Choose target position using dropdowns
5. Click "Calculate Firing Solution"
6. Read elevation in Mils (primary) and Degrees (secondary)

## Project Structure

- `/calculator/` - Web application and Flask server
- `/processed_maps/` - Heightmap data for all maps (JSON format)
- `/processor/` - Tools for processing new maps
- `/raw_map_data/` - Original map files from game
- `run.bat` / `run.sh` - Launch scripts

## Documentation

- [PRD.md](PRD.md) - Complete product requirements
- [calculator/README.md](calculator/README.md) - Frontend documentation
- [processor/README.md](processor/README.md) - Map processing guide
- [openspec/project.md](openspec/project.md) - Technical context

## License

MIT License - See [LICENSE](LICENSE) file

## Credits

Built for the Project Reality: BF2 community