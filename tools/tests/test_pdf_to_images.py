"""Tests for the smart PDF processor with page classification."""

import json
import os
import sys
from pathlib import Path

import pytest
import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_to_images import classify_page, process_pdf


@pytest.fixture
def tmp_output(tmp_path):
    return str(tmp_path)


def make_text_only_pdf(path):
    """Create a PDF with only text content (like a license agreement)."""
    doc = fitz.open()
    page = doc.new_page()

    text = (
        "LICENSE AGREEMENT\n\n"
        "This software is provided 'as-is', without any express or implied warranty. "
        "In no event will the authors be held liable for any damages arising from the "
        "use of this software.\n\n"
        "Permission is granted to anyone to use this software for any purpose, including "
        "commercial applications, and to alter it and redistribute it freely, subject to "
        "the following restrictions:\n\n"
        "1. The origin of this software must not be misrepresented.\n"
        "2. Altered source versions must be plainly marked as such.\n"
        "3. This notice may not be removed or altered from any source distribution.\n"
    )
    page.insert_text((72, 72), text, fontsize=11)
    doc.save(str(path))
    doc.close()


def make_graphical_pdf(path):
    """Create a PDF with significant drawing content (like a schematic)."""
    doc = fitz.open()
    page = doc.new_page()

    shape = page.new_shape()

    # Draw a grid of lines (simulating a schematic)
    for i in range(30):
        y = 50 + i * 20
        shape.draw_line((50, y), (550, y))
        x = 50 + i * 17
        shape.draw_line((x, 50), (x, 650))

    # Draw some rectangles (simulating component boxes)
    for i in range(10):
        x = 100 + i * 40
        shape.draw_rect(fitz.Rect(x, 200, x + 30, 250))

    # Draw circles (simulating op-amp symbols)
    for i in range(5):
        shape.draw_circle((150 + i * 80, 400), 20)

    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()

    # Also add some text labels
    page.insert_text((100, 300), "R1=10k  C1=100nF  U1=LM358", fontsize=10)

    doc.save(str(path))
    doc.close()


def make_mixed_pdf(path):
    """Create a PDF with a text page followed by a graphical page."""
    doc = fitz.open()

    # Page 1: text only
    page1 = doc.new_page()
    page1.insert_text((72, 72), "BILL OF MATERIALS\n\nRef  Value  Package\nR1   10k   0603\nC1   100nF 0402\nU1   LM358 SOIC-8", fontsize=11)

    # Page 2: graphical
    page2 = doc.new_page()
    shape = page2.new_shape()
    for i in range(25):
        shape.draw_line((50, 50 + i * 25), (550, 50 + i * 25))
        shape.draw_line((50 + i * 20, 50), (50 + i * 20, 700))
    for i in range(8):
        shape.draw_rect(fitz.Rect(100 + i * 50, 300, 130 + i * 50, 340))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()
    page2.insert_text((100, 100), "POWER SUPPLY SCHEMATIC", fontsize=14)

    # Page 3: text only (another text page)
    page3 = doc.new_page()
    page3.insert_text((72, 72), "DESIGN NOTES\n\nThe power supply uses a buck topology.\nInput: 12V, Output: 5V @ 2A.\nEfficiency target: >90%.", fontsize=11)

    doc.save(str(path))
    doc.close()


def make_blank_pdf(path):
    """Create a PDF with a blank page."""
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()


class TestClassifyPage:
    def test_text_only_page(self, tmp_path):
        pdf_path = tmp_path / "text.pdf"
        make_text_only_pdf(pdf_path)
        doc = fitz.open(str(pdf_path))
        assert classify_page(doc[0]) == "text"
        doc.close()

    def test_graphical_page(self, tmp_path):
        pdf_path = tmp_path / "graphic.pdf"
        make_graphical_pdf(pdf_path)
        doc = fitz.open(str(pdf_path))
        assert classify_page(doc[0]) == "image"
        doc.close()

    def test_blank_page(self, tmp_path):
        pdf_path = tmp_path / "blank.pdf"
        make_blank_pdf(pdf_path)
        doc = fitz.open(str(pdf_path))
        assert classify_page(doc[0]) == "text"
        doc.close()


class TestProcessPdf:
    def test_text_only_pdf(self, tmp_path, tmp_output):
        pdf_path = tmp_path / "text.pdf"
        make_text_only_pdf(pdf_path)

        results = process_pdf(str(pdf_path), tmp_output)

        assert len(results) == 1
        assert results[0]["page"] == 1
        assert results[0]["type"] == "text"
        assert results[0]["path"] is None
        assert "LICENSE AGREEMENT" in results[0]["text"]

    def test_graphical_pdf(self, tmp_path, tmp_output):
        pdf_path = tmp_path / "graphic.pdf"
        make_graphical_pdf(pdf_path)

        results = process_pdf(str(pdf_path), tmp_output)

        assert len(results) == 1
        assert results[0]["page"] == 1
        assert results[0]["type"] == "image"
        assert results[0]["path"] is not None
        assert os.path.exists(results[0]["path"])
        assert results[0]["path"].endswith(".png")

    def test_mixed_pdf_classification(self, tmp_path, tmp_output):
        pdf_path = tmp_path / "mixed.pdf"
        make_mixed_pdf(pdf_path)

        results = process_pdf(str(pdf_path), tmp_output)

        assert len(results) == 3

        # Page 1: text (BOM table)
        assert results[0]["type"] == "text"
        assert results[0]["path"] is None
        assert "BILL OF MATERIALS" in results[0]["text"]

        # Page 2: image (schematic)
        assert results[1]["type"] == "image"
        assert results[1]["path"] is not None
        assert os.path.exists(results[1]["path"])

        # Page 3: text (design notes)
        assert results[2]["type"] == "text"
        assert results[2]["path"] is None
        assert "DESIGN NOTES" in results[2]["text"]

    def test_blank_pdf(self, tmp_path, tmp_output):
        pdf_path = tmp_path / "blank.pdf"
        make_blank_pdf(pdf_path)

        results = process_pdf(str(pdf_path), tmp_output)

        assert len(results) == 1
        assert results[0]["type"] == "text"
        assert results[0]["text"] == "(blank page)"

    def test_output_is_valid_json(self, tmp_path, tmp_output):
        pdf_path = tmp_path / "mixed.pdf"
        make_mixed_pdf(pdf_path)

        results = process_pdf(str(pdf_path), tmp_output)

        # Verify it serializes to valid JSON
        serialized = json.dumps(results)
        parsed = json.loads(serialized)
        assert len(parsed) == 3

    def test_image_pages_not_rendered_for_text(self, tmp_path, tmp_output):
        """Verify no PNG files are created for text-only pages."""
        pdf_path = tmp_path / "text.pdf"
        make_text_only_pdf(pdf_path)

        process_pdf(str(pdf_path), tmp_output)

        png_files = list(Path(tmp_output).glob("*.png"))
        assert len(png_files) == 0

    def test_only_graphical_pages_get_pngs(self, tmp_path, tmp_output):
        """Mixed PDF: only the graphical page should have a PNG."""
        pdf_path = tmp_path / "mixed.pdf"
        make_mixed_pdf(pdf_path)

        process_pdf(str(pdf_path), tmp_output)

        png_files = list(Path(tmp_output).glob("*.png"))
        assert len(png_files) == 1  # Only page 2 (schematic)
        assert "page_2" in png_files[0].name
