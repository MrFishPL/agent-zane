---
name: ask
description: Primary entry point for all user requests. Accepts any input (text, images, PDFs, schematics, requirements) and kicks off the full component sourcing workflow. Use /ask to start any interaction with the agent.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, WebSearch, WebFetch
user-invocable: true
---

The user has submitted a request. This is the main workflow entry point.

## Step 0: Clean Temp Directory

Before anything else, clean the `tmp/` directory at project root:
```bash
.venv/bin/python3 tools/clean_tmp.py
```
This ensures no stale images from previous runs interfere.

## Step 1: Load Context (parallel)

Immediately spawn these in parallel:
- **lessons-reader** agent → reads `lessons/` directory for learned rules
- **Input analysis** → examine what the user provided (text, image, PDF, etc.)

## Step 2: Understand the Input

Assess what the user gave you:

**Text-only request** (e.g., "I need a 5V buck converter for 2A"):
- Extract component requirements directly
- Proceed to Step 4

**Schematic (image — PNG, JPG, WEBP, etc.)**:
- Identify all functional blocks in the schematic
- Spawn one **schematic-analyzer** agent per block (parallel)
- Merge results into a unified component requirements list

**Schematic (PDF)**:
- First, process the PDF using the smart conversion tool:
  ```bash
  .venv/bin/python3 tools/pdf_to_images.py "<pdf_path>"
  ```
  This auto-classifies each page as **text** or **image** and outputs a JSON manifest to stdout:
  ```json
  [
    {"page": 1, "type": "image", "path": "tmp/schematic_page_1.png"},
    {"page": 2, "type": "text", "text": "License agreement text...", "path": null},
    {"page": 3, "type": "image", "path": "tmp/schematic_page_3.png"}
  ]
  ```
- If `.venv` doesn't exist or the command fails, set it up first:
  ```bash
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
  ```
  Then re-run the conversion.
- **For `"type": "image"` pages:** Read the PNG using the Read tool for visual analysis. Spawn one **schematic-analyzer** agent per image page (parallel).
- **For `"type": "text"` pages:** The text content is already in the JSON. Scan it for useful info (BOM tables, specifications, part lists, design notes). Do NOT render these as images — text is cheaper and more accurate than vision on pages of prose.
- Skip pages that are clearly non-technical (license agreements, legal boilerplate, blank pages).
- Merge all page analyses into a unified component requirements list.

**Crop-zoom pass (automatic — do NOT skip):**
After merging initial page analyses, check every image page result for unreadable values, unclear reference designators, or uncertain part numbers. For each unreadable area:
1. Estimate the region's position as percentage coordinates (x1%, y1%, x2%, y2%) on the page.
2. Crop-zoom that region:
   ```bash
   .venv/bin/python3 tools/pdf_crop_zoom.py "<pdf_path>" <page_number> <x1> <y1> <x2> <y2>
   ```
   This renders just that region at 600 DPI and outputs a single PNG path.
3. Read the cropped PNG with the Read tool and extract the previously-unreadable values.
4. Multiple crop-zoom calls can run in parallel (one per unclear area, even across pages).
5. Merge the zoomed readings back into the component list, replacing "?" and "unreadable" entries.

Only proceed to clarification (Step 3) after the crop-zoom pass is complete. The goal is to resolve as much as possible through re-rendering before ever asking the user.

**Mixed input** (schematic + text instructions):
- Process both in parallel
- Text instructions override or add constraints to what's found in the schematic

## Step 3: Clarify if Needed

If anything is unclear or ambiguous, output a JSON response per `.claude/rules/output-format.md`:

```json
{
  "status": "needs_clarification",
  "message": "I can read the schematic but need a few answers before sourcing.",
  "data": {
    "questions": [
      {"id": 1, "question": "...", "default": "...", "why": "..."}
    ]
  }
}
```

- If questions relate to a schematic, annotate a copy of the image with red rectangles and numbered labels
- User answers concisely: "1. yes 2. 47uF 3. skip"
- Maximum 3 clarification rounds, then proceed with best interpretation + caveats

## Step 4: Source Components (parallel)

Once requirements are clear:
- Spawn one **component-sourcer** agent per distributor (DigiKey, Mouser, LCSC — simultaneously)
- If user specified a single distributor, spawn only that one
- Apply optimization priority (price or availability)
- Apply all qualification filters (automotive, medical, temperature, etc.)

Each sourcer agent has a **built-in web search fallback**: if MCP APIs return 0 results, the agent automatically searches the distributor's website (`site:mouser.com ...`, `site:digikey.com ...`, etc.) and extracts data with WebFetch. Results from web fallback are marked `mpn_confidence: "searched"`.

**The agent must NEVER report "NOT FOUND" without the sourcer having tried web search fallback first.** If a sourcer returns "no match" without any WebSearch tool calls, its output is suspect — re-run it or do the web search yourself.

## Step 5: Merge and Check (parallel)

- Spawn **result-merger** agent to combine distributor results into ranked recommendations
- Simultaneously spawn **cad-model-checker** agent for SnapMagic lookup

## Step 6: Present Results

Output a JSON response per `.claude/rules/output-format.md`:
- Use the unified `{status, message, data}` envelope
- `message` contains all reasoning, warnings, and strategic advice
- `data` contains the structured component list, BOM summary, etc.
- Every URL must be full and clickable — never truncated
- All data marked `"verified": false` until sourced from MCP APIs
- Do NOT prompt for feedback. Feedback comes through `/feedback`.

## Step 7: Clean Up

After presenting results, clean the temp directory:
```bash
.venv/bin/python3 tools/clean_tmp.py
```
