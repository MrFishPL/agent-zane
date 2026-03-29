#!/usr/bin/env python3
"""Crop and re-render a region of a PDF page at high resolution.

Used when the agent identifies an unreadable area on a schematic page
and needs to "zoom in" — just like an engineer squinting at a printout.
"""

import os
import sys

import fitz  # PyMuPDF

DPI = 600


def crop_zoom(pdf_path, page_number, x1_pct, y1_pct, x2_pct, y2_pct, output_dir=None):
    """Crop a rectangular region from a PDF page and render at high DPI.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.
        x1_pct, y1_pct: Top-left corner as percentages (0-100).
        x2_pct, y2_pct: Bottom-right corner as percentages (0-100).
        output_dir: Directory to save output. Defaults to tmp/ at project root.

    Returns:
        Path to the output PNG.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    page_index = page_number - 1

    if page_index < 0 or page_index >= len(doc):
        print(
            f"Error: Page {page_number} out of range (PDF has {len(doc)} pages)",
            file=sys.stderr,
        )
        sys.exit(1)

    page = doc[page_index]
    rect = page.rect

    # Convert percentages to absolute coordinates
    x1 = rect.x0 + (x1_pct / 100) * rect.width
    y1 = rect.y0 + (y1_pct / 100) * rect.height
    x2 = rect.x0 + (x2_pct / 100) * rect.width
    y2 = rect.y0 + (y2_pct / 100) * rect.height

    clip = fitz.Rect(x1, y1, x2, y2)

    zoom = DPI / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=clip)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(
        output_dir,
        f"{base_name}_p{page_number}_crop_{int(x1_pct)}_{int(y1_pct)}_{int(x2_pct)}_{int(y2_pct)}.png",
    )
    pix.save(output_path)

    doc.close()
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(
            "Usage: python3 pdf_crop_zoom.py <pdf_path> <page_number> <x1%> <y1%> <x2%> <y2%>",
            file=sys.stderr,
        )
        print(
            "  Coordinates are percentages (0-100). Example: 50 0 100 50 = top-right quarter",
            file=sys.stderr,
        )
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_number = int(sys.argv[2])
    x1_pct = float(sys.argv[3])
    y1_pct = float(sys.argv[4])
    x2_pct = float(sys.argv[5])
    y2_pct = float(sys.argv[6])

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    path = crop_zoom(pdf_path, page_number, x1_pct, y1_pct, x2_pct, y2_pct)
    print(path)
