"""
PDF Utilities

Provides functions for extracting text from PDF files.
Uses PyMuPDF (fitz) for fast, accurate text extraction.
"""

import base64
import io
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from utils.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf_base64(pdf_base64: str) -> Optional[str]:
    """
    Extract text from a base64-encoded PDF.

    Args:
        pdf_base64: Base64-encoded PDF data

    Returns:
        Extracted text as string, or None if extraction fails

    Raises:
        ImportError: If PyMuPDF is not installed
        ValueError: If PDF data is invalid
    """
    if fitz is None:
        raise ImportError(
            "PyMuPDF is required for PDF text extraction. "
            "Install with: pip install pymupdf"
        )

    try:
        # Decode base64 to bytes
        pdf_bytes = base64.b64decode(pdf_base64)

        # Open PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Extract text from all pages
        text_parts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text()

            # Add page separator for multi-page PDFs
            if page_num > 0:
                text_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n")

            text_parts.append(page_text)

        doc.close()

        # Combine all pages
        full_text = ''.join(text_parts)

        # Clean up excessive whitespace
        full_text = '\n'.join(line for line in full_text.splitlines() if line.strip())

        logger.info(
            "pdf_text_extracted",
            page_count=doc.page_count if 'doc' in locals() else 0,
            text_length=len(full_text)
        )

        return full_text

    except base64.binascii.Error as e:
        logger.error("pdf_base64_decode_failed", error=str(e))
        raise ValueError(f"Invalid base64 PDF data: {e}")

    except Exception as e:
        logger.error("pdf_text_extraction_failed", error=str(e), exc_info=True)
        return None


def extract_text_from_pdf_file(file_path: str) -> Optional[str]:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text as string, or None if extraction fails
    """
    if fitz is None:
        raise ImportError(
            "PyMuPDF is required for PDF text extraction. "
            "Install with: pip install pymupdf"
        )

    try:
        doc = fitz.open(file_path)

        # Extract text from all pages
        text_parts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text()

            # Add page separator for multi-page PDFs
            if page_num > 0:
                text_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n")

            text_parts.append(page_text)

        page_count = doc.page_count
        doc.close()

        # Combine all pages
        full_text = ''.join(text_parts)

        # Clean up excessive whitespace
        full_text = '\n'.join(line for line in full_text.splitlines() if line.strip())

        logger.info(
            "pdf_text_extracted_from_file",
            file_path=file_path,
            page_count=page_count,
            text_length=len(full_text)
        )

        return full_text

    except Exception as e:
        logger.error(
            "pdf_file_extraction_failed",
            file_path=file_path,
            error=str(e),
            exc_info=True
        )
        return None


def get_pdf_metadata(pdf_base64: str) -> Optional[dict]:
    """
    Extract metadata from a base64-encoded PDF.

    Args:
        pdf_base64: Base64-encoded PDF data

    Returns:
        Dictionary with metadata (page_count, title, author, etc.)
    """
    if fitz is None:
        return None

    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        metadata = {
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "mod_date": doc.metadata.get("modDate", "")
        }

        doc.close()

        return metadata

    except Exception as e:
        logger.error("pdf_metadata_extraction_failed", error=str(e))
        return None
