"""
PDF Text Extractor - Extracts text with full style and position information.

Uses PyMuPDF to extract text spans with:
- Position (bounding box)
- Font name and size
- Color
- Flags (bold, italic, etc.)
"""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Optional
from config import SKIP_PATTERNS, MIN_TEXT_LENGTH


def should_skip_text(text: str) -> bool:
    """
    Determine if text should be skipped from translation.
    Skips numbers, math symbols, very short text, etc.
    """
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return True

    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text.strip()):
            return True

    return False


def extract_page_elements(page: fitz.Page) -> Dict[str, Any]:
    """
    Extract all elements from a page including text spans with full style info.

    Returns a dictionary with:
    - 'text_blocks': list of text blocks, each containing lines and spans
    - 'images': list of image references
    - 'drawings': list of drawing elements
    - 'page_rect': page dimensions
    """
    # Get detailed text information
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    elements = {
        "page_rect": page.rect,
        "text_blocks": [],
        "images": [],
        "width": page.rect.width,
        "height": page.rect.height,
    }

    for block in text_dict.get("blocks", []):
        if block["type"] == 0:  # Text block
            block_data = {
                "type": "text",
                "bbox": block["bbox"],
                "lines": [],
            }

            for line in block.get("lines", []):
                line_data = {
                    "bbox": line["bbox"],
                    "wmode": line.get("wmode", 0),  # Writing mode
                    "dir": line.get("dir", (1, 0)),  # Text direction
                    "spans": [],
                }

                for span in line.get("spans", []):
                    span_data = {
                        "text": span["text"],
                        "bbox": span["bbox"],
                        "font": span["font"],
                        "size": span["size"],
                        "color": span["color"],
                        "flags": span["flags"],  # Bold, italic, etc.
                        "origin": span.get("origin", (span["bbox"][0], span["bbox"][3])),
                        "should_translate": not should_skip_text(span["text"]),
                    }
                    line_data["spans"].append(span_data)

                block_data["lines"].append(line_data)

            elements["text_blocks"].append(block_data)

        elif block["type"] == 1:  # Image block
            elements["images"].append({
                "type": "image",
                "bbox": block["bbox"],
                "image_index": block.get("number", 0),
            })

    return elements


def extract_translatable_texts(elements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract only the translatable text spans from page elements.

    Returns a flat list of spans that should be translated, preserving
    their reference to enable later reconstruction.
    """
    translatable = []

    for block_idx, block in enumerate(elements["text_blocks"]):
        for line_idx, line in enumerate(block["lines"]):
            for span_idx, span in enumerate(line["spans"]):
                if span["should_translate"] and span["text"].strip():
                    translatable.append({
                        "text": span["text"],
                        "block_idx": block_idx,
                        "line_idx": line_idx,
                        "span_idx": span_idx,
                        "bbox": span["bbox"],
                        "font": span["font"],
                        "size": span["size"],
                        "color": span["color"],
                        "flags": span["flags"],
                        "origin": span["origin"],
                    })

    return translatable


def get_document_info(doc: fitz.Document) -> Dict[str, Any]:
    """
    Get general information about the PDF document.
    """
    return {
        "page_count": len(doc),
        "metadata": doc.metadata,
        "is_encrypted": doc.is_encrypted,
        "permissions": doc.permissions,
    }
