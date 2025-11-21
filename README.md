# Project Reality Mortar Calculator

Calculate accurate firing solutions for mortars in Project Reality: BF2.

**IMPORTANT: shallow clone only the ~5 latest commit. DO NOT FULL CLONE THE REPO**
```bash
git clone --depth 5 https://github.com/zadzanl/Project_Reality-Mortar-Calculator
```
Only after finishing i realise that the repo size are over 10GB 
(because all maps' `client.zip` and `server.zip` are pushed) 

## Quick Start

**Windows:**
```bash
run.bat
```

**Linux/Mac:** (Untested)
```bash
./run.sh
```

The calculator opens automatically (if port unoccupied) at `http://localhost:8080`

## Requirements

- Python 3.8 or newer
- Flask 2.3+ and Werkzeug 2.3+ (auto-installed on first run)
- Modern web browser (Chrome, Firefox, Edge)

## Features

- Visual map representation with satellite/overview imagery
- Automatic elevation detection from heightmaps
- High-angle firing solutions in Mils and Degrees
- Support for all 84 Project Reality maps (as of 20/11/2025)
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
- `/processed_maps/` - Heightmap data (JSON) and minimap images (PNG) for all maps
- `/processor/` - Tools for processing new maps (heightmaps + minimaps)
- `/raw_map_data/` - Original map files from game (server.zip + client.zip)
- `run.bat` / `run.sh` - Launch scripts

## Documentation

- [PRD.md](PRD.md) - Complete product requirements
- [calculator/README.md](calculator/README.md) - Frontend documentation
- [processor/README.md](processor/README.md) - Map processing guide
- [openspec/project.md](openspec/project.md) - Technical context

## License

MIT License - See [LICENSE](LICENSE) file

## Credits

- To previous attempt at making a mortar calculator:
    - [BiNoops's Mortar Calculator](https://github.com/BiNoopsGITHUB/PRBF2-Mortar-Calculator)
    - [Shemich's Mortar Calculator](https://github.com/Shemich/project-reality-mortar-calculator)

- And other repo found when searching ["Project Reality Mortar" in github](https://github.com/search?q=project%20reality%20mortar&type=repositories)

- To PRID for how badly we aim the mortar and motivating me to create the calculator

- To all community member and devs that discussed and answers mortar mechanics and physics discussion

- To copilot for implementing the UI
