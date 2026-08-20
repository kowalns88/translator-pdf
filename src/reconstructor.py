"""
PDF Reconstructor - Rebuilds PDF with translated text while preserving layout.

Strategy:
1. Copy the original page as-is (preserving all images, drawings, backgrounds)
2. Use redaction annotations to remove original text (white-out)
3. Insert translated text at the same position with matching style using TTF fonts
"""

try:
    import fitz  # PyMuPDF legacy import
except ImportError:
    import pymupdf as fitz  # PyMuPDF new import
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from config import FALLBACK_FONT, USE_CUSTOM_FONT, CUSTOM_FONT_PATH

logger = logging.getLogger(__name__)

# Font file paths (Noto Sans supports Polish diacritics: ą, ć, ę, ł, ń, ó, ś, ź, ż)
# Auto-detect font directory (works on Docker, Linux, and custom installs)
FONT_SEARCH_PATHS = [
    "/usr/share/fonts/google-noto",          # Sandbox / some Linux
    "/usr/share/fonts/truetype/noto",        # Debian/Ubuntu (apt install fonts-noto)
    "/usr/share/fonts/noto",                 # Fedora/RHEL
    "/usr/share/fonts/truetype/dejavu",      # Fallback: DejaVu
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts"),  # Local fonts/ dir
]


def _find_font_dir() -> str:
    """Find the first available font directory."""
    for path in FONT_SEARCH_PATHS:
        if os.path.isdir(path):
            return path
    return FONT_SEARCH_PATHS[0]  # Fallback


def _find_font_file(font_dir: str, variants: list) -> str:
    """Find a font file trying multiple name variants."""
    for variant in variants:
        path = os.path.join(font_dir, variant)
        if os.path.exists(path):
            return path
    return os.path.join(font_dir, variants[0])


FONT_DIR = _find_font_dir()
FONT_FILES = {
    "regular": _find_font_file(FONT_DIR, [
        "NotoSans-Regular.ttf", "NotoSans[wdth,wght].ttf", "DejaVuSans.ttf"
    ]),
    "bold": _find_font_file(FONT_DIR, [
        "NotoSans-Bold.ttf", "NotoSans[wdth,wght].ttf", "DejaVuSans-Bold.ttf"
    ]),
    "italic": _find_font_file(FONT_DIR, [
        "NotoSans-Italic.ttf", "NotoSans-Italic[wdth,wght].ttf", "DejaVuSans-Oblique.ttf"
    ]),
    "bold_italic": _find_font_file(FONT_DIR, [
        "NotoSans-BoldItalic.ttf", "NotoSans-Italic[wdth,wght].ttf", "DejaVuSans-BoldOblique.ttf"
    ]),
}

# Font names registered in each page (to avoid re-registering)
_registered_fonts: Dict[str, str] = {}


def normalize_color(color_int: int) -> Tuple[float, float, float]:
    """
    Convert a 24-bit integer RGB color to a tuple with normalized values (0.0 - 1.0).
    """
    if isinstance(color_int, (tuple, list)):
        return tuple(color_int)

    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return (red / 255.0, green / 255.0, blue / 255.0)


def get_font_properties(flags: int) -> Dict[str, bool]:
    """
    Extract font properties from flags integer.
    PyMuPDF flags: bit 0=superscript, bit 1=italic, bit 2=serif, bit 3=monospace, bit 4=bold
    """
    return {
        "is_superscript": bool(flags & 1),
        "is_italic": bool(flags & 2),
        "is_serif": bool(flags & 4),
        "is_monospace": bool(flags & 8),
        "is_bold": bool(flags & 16),
    }


def select_font_variant(flags: int) -> str:
    """
    Select the font variant key based on text style flags.
    Returns one of: 'regular', 'bold', 'italic', 'bold_italic'
    """
    props = get_font_properties(flags)

    if props["is_bold"] and props["is_italic"]:
        return "bold_italic"
    elif props["is_bold"]:
        return "bold"
    elif props["is_italic"]:
        return "italic"
    return "regular"


def register_font_on_page(page: fitz.Page, variant: str) -> str:
    """
    Register a TTF font on the page and return the font reference name.
    Uses Noto Sans which has full Polish character support.
    """
    font_file = FONT_FILES.get(variant, FONT_FILES["regular"])
    font_name = f"NotoSans-{variant}"

    if not os.path.exists(font_file):
        logger.warning(f"Font file not found: {font_file}, using regular")
        font_file = FONT_FILES["regular"]
        font_name = "NotoSans-regular"

    # Insert font into the page
    page.insert_font(fontname=font_name, fontfile=font_file)
    return font_name


def calculate_font_size_adjustment(
    original_text: str,
    translated_text: str,
    original_size: float,
    bbox: tuple,
) -> float:
    """
    Calculate adjusted font size to fit translated text in the same bounding box.
    Polish text is typically ~15-20% longer than English.
    """
    if not original_text or not translated_text:
        return original_size

    # Calculate ratio of text lengths
    len_ratio = len(translated_text) / max(len(original_text), 1)

    # Available width
    available_width = bbox[2] - bbox[0]

    if len_ratio > 1.0:
        # Text is longer - reduce font size proportionally but with limits
        # Don't reduce below 60% of original size
        scale_factor = max(1.0 / len_ratio, 0.6)
        adjusted_size = original_size * scale_factor
    else:
        adjusted_size = original_size

    return adjusted_size


def reconstruct_page(
    original_doc: fitz.Document,
    page_number: int,
    translated_spans: List[Dict[str, Any]],
    output_doc: fitz.Document,
    font_file: Optional[str] = None,
) -> fitz.Page:
    """
    Reconstruct a single page with translated text.

    Process:
    1. Copy the original page completely (images, drawings, backgrounds)
    2. For each translated span:
       a. Add a redaction annotation over the original text area
       b. Apply redactions (removes original text, fills with page background)
       c. Insert translated text at the same position using TTF font
    """
    original_page = original_doc[page_number]

    # Create new page with same dimensions
    new_page = output_doc.new_page(
        -1,
        width=original_page.rect.width,
        height=original_page.rect.height,
    )

    # Copy original page content (preserves everything: images, vectors, backgrounds)
    new_page.show_pdf_page(new_page.rect, original_doc, page_number)

    if not translated_spans:
        return new_page

    # Pre-register all needed font variants on this page
    font_variants_needed = set()
    for span in translated_spans:
        variant = select_font_variant(span["flags"])
        font_variants_needed.add(variant)

    registered_fonts = {}
    for variant in font_variants_needed:
        registered_fonts[variant] = register_font_on_page(new_page, variant)

    # Step 1: Add redaction annotations for all text areas that will be replaced
    for span in translated_spans:
        bbox = span["bbox"]
        rect = fitz.Rect(bbox)

        # Add redaction annotation (marks area for text removal)
        new_page.add_redact_annot(
            rect,
            text="",  # No replacement text in redaction
            fill=(1, 1, 1),  # White fill to cover original text
        )

    # Step 2: Apply all redactions at once (removes original text)
    new_page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    # Step 3: Insert translated text at original positions with TTF fonts
    for span in translated_spans:
        translated_text = span.get("translated_text", span["text"])
        if not translated_text or not translated_text.strip():
            continue

        bbox = span["bbox"]
        original_size = span["size"]
        color = normalize_color(span["color"])
        flags = span["flags"]
        origin = span["origin"]

        # Select appropriate font variant
        variant = select_font_variant(flags)
        font_name = registered_fonts.get(variant, registered_fonts.get("regular"))

        # Calculate adjusted font size for longer translated text
        adjusted_size = calculate_font_size_adjustment(
            span["text"], translated_text, original_size, bbox
        )

        # Insert translated text
        # Use origin point for precise positioning (baseline position)
        insert_point = fitz.Point(origin[0], origin[1])

        try:
            new_page.insert_text(
                insert_point,
                translated_text,
                fontname=font_name,
                fontfile=FONT_FILES.get(variant, FONT_FILES["regular"]),
                fontsize=adjusted_size,
                color=color,
                overlay=True,
            )
        except Exception as e:
            logger.warning(
                f"Failed to insert text '{translated_text[:30]}...' at {insert_point}: {e}"
            )
            # Fallback: try with regular font
            try:
                new_page.insert_text(
                    insert_point,
                    translated_text,
                    fontname=registered_fonts.get("regular", "NotoSans-regular"),
                    fontfile=FONT_FILES["regular"],
                    fontsize=original_size * 0.85,
                    color=color,
                    overlay=True,
                )
            except Exception as e2:
                logger.error(f"Fallback insertion also failed: {e2}")

    return new_page


def reconstruct_document(
    input_path: str,
    output_path: str,
    all_translated_spans: Dict[int, List[Dict[str, Any]]],
    page_range: Optional[Tuple[int, int]] = None,
) -> str:
    """
    Reconstruct the entire document with translated text.

    Args:
        input_path: Path to the original PDF
        output_path: Path for the translated PDF
        all_translated_spans: Dictionary mapping page numbers to translated spans
        page_range: Optional tuple (start, end) to process only specific pages

    Returns:
        Path to the output file
    """
    original_doc = fitz.open(input_path)
    output_doc = fitz.open()

    start_page = page_range[0] if page_range else 0
    end_page = page_range[1] if page_range else len(original_doc)

    for page_num in range(start_page, end_page):
        spans = all_translated_spans.get(page_num, [])
        reconstruct_page(original_doc, page_num, spans, output_doc)

        if (page_num + 1) % 10 == 0:
            logger.info(f"Reconstructed page {page_num + 1}/{end_page}")

    # Save with garbage collection and deflate compression
    output_doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
    )

    original_doc.close()
    output_doc.close()

    return output_path
