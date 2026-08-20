#!/usr/bin/env python3
"""
PDF Translator - Translate PDF documents from English to Polish
while preserving the original layout, formatting, images, and styles.

Usage:
    python translate_pdf.py --input input.pdf --output output_pl.pdf
    python translate_pdf.py --input input.pdf --pages 1-10
    python translate_pdf.py --input input.pdf --lang pl
"""

import sys
import os
import argparse
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz  # PyMuPDF
from tqdm import tqdm

from config import (
    SOURCE_LANGUAGE,
    TARGET_LANGUAGE,
    VERBOSE,
    LOG_FILE,
    OUTPUT_SUFFIX,
)
from src.extractor import extract_page_elements, extract_translatable_texts, get_document_info
from src.translator import PDFTranslator
from src.reconstructor import reconstruct_page


def setup_logging(verbose: bool = VERBOSE, log_file: str = LOG_FILE):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def parse_page_range(pages_str: str, max_pages: int) -> Tuple[int, int]:
    """
    Parse page range string (e.g., '1-10', '5', '1-').
    Returns (start_page_0indexed, end_page_0indexed_exclusive).
    """
    if '-' in pages_str:
        parts = pages_str.split('-')
        start = int(parts[0]) - 1 if parts[0] else 0
        end = int(parts[1]) if parts[1] else max_pages
    else:
        start = int(pages_str) - 1
        end = start + 1

    start = max(0, min(start, max_pages - 1))
    end = max(start + 1, min(end, max_pages))

    return start, end


def translate_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    source_lang: str = SOURCE_LANGUAGE,
    target_lang: str = TARGET_LANGUAGE,
    page_range: Optional[Tuple[int, int]] = None,
):
    """
    Main function to translate a PDF file.

    Args:
        input_path: Path to the input PDF file
        output_path: Path for the translated PDF (auto-generated if None)
        source_lang: Source language code
        target_lang: Target language code
        page_range: Optional (start, end) page range (0-indexed)
    """
    logger = logging.getLogger(__name__)

    # Validate input
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Generate output path if not specified
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}{OUTPUT_SUFFIX}{input_file.suffix}"
        )

    logger.info(f"{'=' * 60}")
    logger.info(f"PDF Translator - English to Polish")
    logger.info(f"{'=' * 60}")
    logger.info(f"Input:  {input_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Languages: {source_lang} → {target_lang}")

    # Open the document
    original_doc = fitz.open(input_path)
    doc_info = get_document_info(original_doc)

    total_pages = doc_info["page_count"]
    logger.info(f"Total pages: {total_pages}")

    if doc_info.get("metadata"):
        title = doc_info["metadata"].get("title", "Unknown")
        logger.info(f"Title: {title}")

    # Determine page range
    if page_range:
        start_page, end_page = page_range
    else:
        start_page, end_page = 0, total_pages

    pages_to_process = end_page - start_page
    logger.info(f"Processing pages: {start_page + 1} to {end_page} ({pages_to_process} pages)")
    logger.info(f"{'=' * 60}")

    # Initialize translator
    translator = PDFTranslator(
        source_lang=source_lang,
        target_lang=target_lang,
    )

    # Initialize output document
    output_doc = fitz.open()

    # Process each page
    start_time = time.time()

    with tqdm(total=pages_to_process, desc="Translating pages", unit="page") as pbar:
        for page_num in range(start_page, end_page):
            page = original_doc[page_num]

            # Step 1: Extract text elements with full style info
            elements = extract_page_elements(page)

            # Step 2: Get translatable spans
            translatable_spans = extract_translatable_texts(elements)

            if translatable_spans:
                # Step 3: Translate spans
                translated_spans = translator.translate_spans(translatable_spans)

                # Step 4: Reconstruct page with translated text
                reconstruct_page(
                    original_doc, page_num, translated_spans, output_doc
                )
            else:
                # No text to translate - copy page as-is
                new_page = output_doc.new_page(
                    -1,
                    width=page.rect.width,
                    height=page.rect.height,
                )
                new_page.show_pdf_page(new_page.rect, original_doc, page_num)

            pbar.update(1)
            pbar.set_postfix({
                "cached": len(translator.cache),
                "page": page_num + 1,
            })

    # Save the translated document
    logger.info("Saving translated document...")
    output_doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
    )

    elapsed = time.time() - start_time
    original_doc.close()
    output_doc.close()

    # Final stats
    cache_stats = translator.get_cache_stats()
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Translation complete!")
    logger.info(f"{'=' * 60}")
    logger.info(f"Pages processed: {pages_to_process}")
    logger.info(f"Unique translations cached: {cache_stats['cached_entries']}")
    logger.info(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/pages_to_process:.1f}s per page)")
    logger.info(f"Output saved to: {output_path}")
    logger.info(f"{'=' * 60}")

    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Translate PDF documents from English to Polish while preserving layout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python translate_pdf.py --input book.pdf
  python translate_pdf.py --input book.pdf --output book_polish.pdf
  python translate_pdf.py --input book.pdf --pages 1-10
  python translate_pdf.py --input book.pdf --lang pl --source en
        """,
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to the input PDF file",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Path for the translated PDF (default: input_PL.pdf)",
    )
    parser.add_argument(
        "--lang", "-l",
        type=str,
        default=TARGET_LANGUAGE,
        help=f"Target language code (default: {TARGET_LANGUAGE})",
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        default=SOURCE_LANGUAGE,
        help=f"Source language code (default: {SOURCE_LANGUAGE})",
    )
    parser.add_argument(
        "--pages", "-p",
        type=str,
        default=None,
        help="Page range to translate (e.g., '1-10', '5', '1-50')",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=VERBOSE,
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose and not args.quiet)

    # Parse page range
    page_range = None
    if args.pages:
        doc = fitz.open(args.input)
        max_pages = len(doc)
        doc.close()
        page_range = parse_page_range(args.pages, max_pages)

    # Run translation
    output_path = translate_pdf(
        input_path=args.input,
        output_path=args.output,
        source_lang=args.source,
        target_lang=args.lang,
        page_range=page_range,
    )

    print(f"\n✅ Tłumaczenie zakończone! Plik zapisany: {output_path}")


if __name__ == "__main__":
    main()
