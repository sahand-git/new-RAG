"""
PDF Rendering and Visual Inspection Utilities using PyMuPDF.
Provides high-fidelity page rendering to images, text extraction,
and visual bounding-box highlights for cited evidence.
"""

import base64
from pathlib import Path
from typing import Optional, List, Tuple
import pymupdf


def get_pdf_page_count(pdf_path: str | Path) -> int:
    """Return total number of pages in the given PDF file."""
    path = Path(pdf_path)
    if not path.is_file():
        return 0
    try:
        with pymupdf.open(str(path)) as doc:
            return len(doc)
    except Exception:
        return 0


def get_pdf_page_text(pdf_path: str | Path, page_number: int) -> str:
    """
    Extract raw text from a specific page (1-indexed).
    """
    path = Path(pdf_path)
    if not path.is_file():
        return ""
    try:
        with pymupdf.open(str(path)) as doc:
            if 1 <= page_number <= len(doc):
                return doc[page_number - 1].get_text("text")
    except Exception:
        pass
    return ""


def render_pdf_page_to_png(
    pdf_path: str | Path,
    page_number: int,
    dpi: int = 150,
    highlight_terms: Optional[List[str]] = None,
) -> Optional[bytes]:
    """
    Render a specific PDF page (1-indexed) as high-resolution PNG bytes.
    Optionally highlights occurrences of search/citation terms.
    """
    path = Path(pdf_path)
    if not path.is_file():
        return None

    try:
        doc = pymupdf.open(str(path))
        if not (1 <= page_number <= len(doc)):
            doc.close()
            return None

        page = doc[page_number - 1]

        # Highlight any matching snippets or terms if provided
        if highlight_terms:
            for term in highlight_terms:
                term_clean = term.strip()
                if len(term_clean) >= 3:
                    quads = page.search_for(term_clean)
                    for quad in quads[:10]:  # Limit highlights to avoid visual noise
                        annot = page.add_highlight_annot(quad)
                        annot.set_colors(stroke=(1.0, 0.9, 0.2))  # Warm yellow
                        annot.update()

        # Render to image pixmap
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")
        doc.close()
        return png_bytes
    except Exception as exc:
        print(f"[pdf_viewer] Error rendering page {page_number} of {pdf_path}: {exc}")
        return None


def get_pdf_iframe_html(
    pdf_path: str | Path,
    page_number: int = 1,
    height: int = 800,
) -> str:
    """
    Generate an HTML iframe embedding the PDF using browser-native PDF viewer
    and jump hash: #page=X.
    """
    path = Path(pdf_path)
    if not path.is_file():
        return "<p style='color:red;'>PDF file not found.</p>"

    try:
        pdf_bytes = path.read_bytes()
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        src = f"data:application/pdf;base64,{b64}#page={page_number}&view=FitH"
        return f"""
        <iframe
            src="{src}"
            width="100%"
            height="{height}px"
            type="application/pdf"
            style="border: 1px solid #ddd; border-radius: 8px;"
        >
            <p>Your browser does not support iframes. Please view via the Rendered Image tab.</p>
        </iframe>
        """
    except Exception as exc:
        return f"<p style='color:red;'>Failed to load PDF iframe: {exc}</p>"
