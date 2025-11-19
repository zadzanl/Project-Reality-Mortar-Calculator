<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

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

1. **`PRD.md`** - Product Requirements Document
   - This file tells you WHAT to build
   - Contains all requirements and rules
   - Has exact formulas and numbers you MUST use
   - **IF PRD.md CONFLICTS WITH OTHER DOCUMENTS: PRD.md IS ALWAYS CORRECT**
   - Do NOT change ANY physics values in this file

2. **`openspec/project.md`** - Project setup guide
   - This file tells you HOW to build
   - Explains which tools to use (Flask, Leaflet.js, JavaScript)
   - Shows code style rules (how to name things, how to format code)
   - Explains Project Reality game concepts (grid system, coordinates)

3. **`openspec/AGENTS.md`** - Workflow guide
   - This file tells you WHEN to create proposals
   - Only read this when adding NEW features
   - NOT needed for fixing bugs

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

### When to Write a Proposal (vs. Just Fix It)

**Write a proposal document BEFORE coding if:**
- Adding a NEW feature (example: add save/load buttons)
- Changing how coordinates work (breaking change)
- Switching to different libraries (example: replace Leaflet with something else)
- Adding a database or API server

**Just fix it directly (NO proposal needed) if:**
- Fixing a bug (making it work like PRD.md says)
- Improving code formatting or adding comments
- Updating documentation files
- Making code faster WITHOUT changing what it does

---

**FINAL REMINDER:**

The file `PRD.md` contains all the rules. If you are confused:
1. Read PRD.md first
2. Then read openspec/project.md for code style
3. Then read openspec/AGENTS.md for workflow

If documents disagree with each other, PRD.md is always correct.