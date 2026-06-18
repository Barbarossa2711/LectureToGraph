"""PDF reading for provider-agnostic vision: extract text (pdfplumber) and render
pages to PNG images (PyMuPDF, pure wheels -> no Poppler dependency)."""
from __future__ import annotations

import base64
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from app.config import settings
from app.models.ai import TextBlock, ImageBlock


def _parse_pages(pages: str | None, total: int) -> list[int]:
    """0-based page indices for a '1-5' / '3' style range (1-based, inclusive)."""
    if not pages:
        return list(range(total))
    pages = pages.strip()
    if "-" in pages:
        a, b = pages.split("-", 1)
        start, end = int(a), int(b)
    else:
        start = end = int(pages)
    start = max(1, start)
    end = min(total, end)
    return [i - 1 for i in range(start, end + 1)]


def _render_page(doc: fitz.Document, index: int, dpi: int, max_edge: int) -> bytes:
    page = doc.load_page(index)
    zoom = dpi / 72.0
    rect = page.rect
    longest = max(rect.width, rect.height) * zoom
    if longest > max_edge:
        zoom *= max_edge / longest
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return pix.tobytes("png")


def read_pdf_blocks(path: Path, pages: str | None) -> list:
    """Return a list of TextBlock / ImageBlock for the requested pages."""
    blocks: list = []
    with fitz.open(path) as doc:
        total = doc.page_count
        indices = _parse_pages(pages, total)
        if len(indices) > settings.pdf_max_pages_per_batch:
            indices = indices[: settings.pdf_max_pages_per_batch]
            blocks.append(TextBlock(text=(
                f"[Only the first {settings.pdf_max_pages_per_batch} requested pages are "
                f"shown. Call read_pdf again with a later 'pages' range for more.]"
            )))

        with pdfplumber.open(str(path)) as pl:
            for idx in indices:
                page_no = idx + 1
                text = ""
                if idx < len(pl.pages):
                    text = pl.pages[idx].extract_text() or ""
                blocks.append(TextBlock(text=f"--- {path.name} page {page_no} (text) ---\n{text}"))
                png = _render_page(doc, idx, settings.pdf_render_dpi, settings.pdf_image_max_edge)
                blocks.append(ImageBlock(
                    media_type="image/png",
                    data_b64=base64.standard_b64encode(png).decode("ascii"),
                ))
    return blocks
