#!/usr/bin/env python3
"""Smart PDF processor: auto-classifies pages as text or image.

Text-only pages (license agreements, BOM tables, spec text) → extracted as text.
Graphical pages (schematics, circuit diagrams, drawings) → rendered to PNG at 300 DPI.

Output: JSON array to stdout with page results.
"""

import json
import os
import sys

import fitz  # PyMuPDF

DPI = 300

# Thresholds for page classification
# A page is "graphical" if it has enough drawing commands (lines, curves, rects)
# relative to its text content.
MIN_DRAWING_COMMANDS = 20  # pages with fewer than this are likely text-only
MIN_IMAGES = 1             # any embedded image makes it graphical


def classify_page(page):
    """Classify a page as 'text' or 'image' based on its content.

    Heuristic:
    - Count embedded raster images — any image means graphical
    - Count total drawing items (lines, curves, rects) across all path groups
    - If the page has significant graphical content → 'image' (render to PNG)
    - If it's mostly text blocks → 'text' (extract text directly)

    Returns:
        'text' or 'image'
    """
    # Check for embedded raster images first — any image means graphical
    images = page.get_images(full=False)
    if len(images) >= MIN_IMAGES:
        return "image"

    # Count total vector drawing items across all path groups.
    # get_drawings() returns path groups; each group contains individual
    # drawing items (lines, curves, rects). A schematic page will have
    # many items even if they're committed in few groups.
    drawings = page.get_drawings()
    total_items = sum(len(d.get("items", [])) for d in drawings)
    if total_items >= MIN_DRAWING_COMMANDS:
        return "image"

    # If we get here, the page is mostly text
    text = page.get_text("text").strip()
    if not text:
        # Blank page or only whitespace — treat as text (skip it)
        return "text"

    return "text"


def process_pdf(pdf_path, output_dir=None):
    """Process a PDF with smart page classification.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory for image output. Defaults to tmp/ at project root.

    Returns:
        List of page result dicts.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    results = []

    zoom = DPI / 72
    matrix = fitz.Matrix(zoom, zoom)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_type = classify_page(page)

        if page_type == "text":
            text = page.get_text("text").strip()
            results.append({
                "page": page_num + 1,
                "type": "text",
                "path": None,
                "text": text if text else "(blank page)",
            })
        else:
            # Render to PNG
            pix = page.get_pixmap(matrix=matrix)
            output_path = os.path.join(
                output_dir, f"{base_name}_page_{page_num + 1}.png"
            )
            pix.save(output_path)
            results.append({
                "page": page_num + 1,
                "type": "image",
                "path": output_path,
                "text": None,
            })

    doc.close()
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 pdf_to_images.py <pdf_path> [output_dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    results = process_pdf(pdf_path, output_dir)
    print(json.dumps(results, indent=2))
