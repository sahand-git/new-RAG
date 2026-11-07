import pytest
from pathlib import Path
from src.pdf_viewer import (
    get_pdf_page_count,
    get_pdf_page_text,
    render_pdf_page_to_png,
)
from src.config import DOCUMENTS_DIR


def test_pdf_page_count():
    doc_path = DOCUMENTS_DIR / "Manual_P200_Robotics.pdf"
    assert doc_path.exists(), "Sample PDF must exist"
    count = get_pdf_page_count(doc_path)
    assert count == 5


def test_pdf_page_text():
    doc_path = DOCUMENTS_DIR / "Manual_P200_Robotics.pdf"
    page1_text = get_pdf_page_text(doc_path, 1)
    assert "Apex P200" in page1_text
    assert "Payload" in page1_text

    page4_text = get_pdf_page_text(doc_path, 4)
    assert "Error E-301" in page4_text
    assert "Error E-405" in page4_text


def test_pdf_page_render_png():
    doc_path = DOCUMENTS_DIR / "Manual_P200_Robotics.pdf"
    png_bytes = render_pdf_page_to_png(doc_path, 1, dpi=100)
    assert png_bytes is not None
    assert len(png_bytes) > 1000
    # Check PNG magic bytes
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


if __name__ == "__main__":
    test_pdf_page_count()
    test_pdf_page_text()
    test_pdf_page_render_png()
    print("All pdf_viewer tests passed!")
