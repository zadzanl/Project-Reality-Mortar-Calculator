<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the user says:
- Words like: "proposal", "spec", "change", "plan"
- "Add a new feature" or "Change how something works"
- The request is unclear and you need to check the rules before writing code

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

---

## Project-Specific Instructions

### Read These Files FIRST (Before Writing Any Code)

**Read these files in this exact order:**

1. **`PRD.md`** - This tells you WHAT to build
   - Read this file FIRST
   - Contains ALL requirements
   - Has exact formulas and numbers - copy them exactly
   - **IMPORTANT: If PRD.md says something different than other files, PRD.md is correct**
   - Do NOT change the physics numbers (gravity = 14.86, speed = 148.64)

2. **`openspec/project.md`** - This tells you HOW to build
   - Read this file SECOND
   - Lists which programming tools to use
   - Shows how to name variables and format code
   - Explains Project Reality game rules

3. **`openspec/AGENTS.md`** - This tells you WHEN to write proposals
   - Read this file THIRD
   - Only needed when adding NEW features
   - Skip this when fixing bugs

### Critical Rules (DO NOT BREAK THESE)

**IMPORTANT NUMBERS - Copy these exactly:**

- **Gravity:** 14.86 meters per second squared
  -  WRONG: Do NOT use 9.8 (that is Earth gravity)
  -  CORRECT: Use 14.86 (this is Project Reality game gravity)
  
- **Projectile Speed:** 148.64 meters per second
  - This is how fast the mortar shell flies
  - Do NOT change this number
  
- **Maximum Distance:** 1500 meters
  - Mortar cannot shoot farther than this

**COORDINATE SYSTEM - The map origin is:**

- Origin point (0, 0) is at the **top-left corner** (Northwest)
  - NOT at the center
  - NOT at the bottom-left
  
- X-axis: Left to right (West to East)
- Y-axis: Top to bottom (North to South)
- Z-axis: Up and down (elevation)

**HEIGHT CALCULATION - Use this exact formula:**

```
elevation_in_meters = (pixel_value / 65535.0) * height_scale
```

- `pixel_value` = number from heightmap image (0 to 65535)
- `height_scale` = maximum map height from terrain.con file (usually 100 to 1000 meters)
- Do NOT use different formulas
- Do NOT change the number 65535

### What to Build in Version 1

** BUILD THESE (Version 1 Requirements):**

1. One mortar position + one target position
   - User can only place ONE mortar and ONE target
   - (Later versions will allow multiple mortars)
   
2. Three dropdown menus for coordinates:
   - Dropdown 1: Column (A through M)
   - Dropdown 2: Row (1 through 13)
   - Dropdown 3: Keypad (numbers 1-9)
   
3. Flask web server
   - Flask only serves files (HTML, CSS, JavaScript, JSON)
   - Flask does NOT do calculations
   - All math happens in the web browser
   
4. Leaflet.js map library
   - Download and include in project folder
   - Do NOT use internet links (CDN)
   
5. JSON files for heightmaps
   - Store height data as JSON (not PNG images)
   - Must keep all 16-bit precision (0 to 65535)
   
6. Bilinear interpolation
   - When reading height between pixels, average the 4 surrounding pixels
   
7. High-angle calculation
   - Calculate mortar angle in Mils (military unit)
   - Show result in both Mils and Degrees
   
8. Offline only
   - Tool works without internet
   - No external websites or APIs

** DO NOT BUILD THESE (Save for Version 2+):**

- Multiple mortars or targets (only one of each in V1)
- Save/load buttons (add placeholder buttons, but they do nothing)
- 3D trajectory visualization (only 2D map in V1)
- Real-time calculation while dragging (only calculate when button is clicked)
- Mobile phone support (only desktop computers in V1)

### Before You Write Code

**Step 1: Read the requirements**
- Open PRD.md
- Find the section about what you need to build
- Read it completely

**Step 2: Check code style rules**
- Open openspec/project.md
- Look for coding conventions section
- Follow the naming and formatting rules

**Step 3: Check for conflicting work**
- Look in openspec/changes/ folder
- See if someone else is working on the same thing
- Avoid duplicate work

**Step 4: Decide if you need a proposal**
- Read the section below: "When to Write a Proposal"

### Map Processing Workflow (Maintainer Only)

**Map processing has two phases:**

**Phase 1 - Collect Files** (file: `collect_maps.py`):

Where: Computer with Project Reality game installed

Steps:
1. Find server.zip files in game folder
2. Check each file is not corrupted (using checksums)
3. Copy files to `/raw_map_data/` folder
4. Create manifest.json (list of all maps)
5. Set up Git LFS if files are big
6. Maintainer uploads to GitHub

**Phase 2 - Convert Files** (file: `process_maps.ipynb`):

Where: Google Colab or local Jupyter (game NOT required)

Steps:
1. Read server.zip files from `/raw_map_data/`
2. Extract heightmap images
3. Convert images to JSON format
4. Save to `/processed_maps/` folder
5. Automatically upload to GitHub
6. Need: Git name, email, and token

**Important: End users do NOT run these scripts.** Pre-processed maps are already in the repository.

**Rules when working on map processing:**

DO:
- Write collection code in `collect_maps.py` only
- Write conversion code in `process_maps.ipynb` only
- Keep Phase 1 and Phase 2 separate

DO NOT:
- Change files in `/raw_map_data/` folder (these are originals)
- Mix collection code with conversion code
- Make Phase 2 depend on Phase 1 directly

### When to Write a Proposal (vs. Just Fix It)

**WRITE A PROPOSAL FIRST if you are:**

Adding something new:
- Example: "Add save/load buttons"
- Example: "Add 3D map view"
- Example: "Add database to store settings"

Changing how something works:
- Example: "Change coordinate system from grid to GPS"
- Example: "Replace Leaflet.js with different map library"
- Example: "Change gravity from 14.86 to different number" (but DON'T do this!)

**JUST FIX IT (no proposal) if you are:**

Fixing errors:
- Example: "Calculator shows wrong answer - fix the math"
- Example: "Button doesn't work - fix the click handler"

Cleaning up code:
- Example: "Add code comments to explain formulas"
- Example: "Rename variables to be clearer"
- Example: "Fix indentation and spacing"

Updating text files:
- Example: "Fix typo in README"
- Example: "Update instructions in PRD.md"

---

**FINAL REMINDER:**

The file `PRD.md` contains all the rules. If you are confused:
1. Read PRD.md first
2. Then read openspec/project.md for code style
3. Then read openspec/AGENTS.md for workflow

If documents disagree with each other, PRD.md is always correct.