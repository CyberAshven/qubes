"""
Document Processing Module

Handles extraction and processing of documents (PDFs, images, etc.)
Creates ACTION blocks to represent document processing operations.
"""

import base64
import hashlib
from typing import Tuple, Optional, Dict, Any

from core.block import create_action_block, Block
from utils.pdf_utils import extract_text_from_pdf_base64, get_pdf_metadata
from utils.logging import get_logger

logger = get_logger(__name__)


async def _extract_from_image_pdf(
    qube,
    pdf_base64: str,
    filename: str,
    max_pages: int = 20
) -> str:
    """
    Extract text from image-only PDFs using AI vision or OCR.

    Strategy:
    1. Try AI vision extraction (if API available) - best quality
    2. Fallback to Tesseract OCR (if vision unavailable) - local processing
    3. Return empty string if both fail

    Args:
        qube: Qube instance (for API access)
        pdf_base64: Base64-encoded PDF data
        filename: PDF filename for logging
        max_pages: Maximum pages to process (default 20 to balance quality vs cost)

    Returns:
        Extracted text or empty string
    """
    try:
        import fitz  # PyMuPDF
        import io
        from PIL import Image

        # Decode PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

        page_count = len(pdf_document)
        pages_to_process = min(page_count, max_pages)

        if page_count > max_pages:
            logger.warning(
                "pdf_page_limit_reached",
                filename=filename,
                total_pages=page_count,
                processing_pages=pages_to_process
            )

        # Check if AI vision is available
        has_vision_api = False
        if qube.api_keys and any(key in qube.api_keys for key in ["anthropic", "openai", "google"]):
            has_vision_api = True

        extracted_parts = []

        if has_vision_api:
            # Try AI vision extraction (best quality)
            logger.info(
                "attempting_vision_extraction",
                filename=filename,
                pages=pages_to_process,
                method="ai_vision"
            )

            text = await _extract_with_vision_api(qube, pdf_document, pages_to_process, filename)
            if text:
                pdf_document.close()
                return text

            logger.warning("vision_extraction_failed_trying_ocr", filename=filename)

        # Fallback to Tesseract OCR (local)
        logger.info(
            "attempting_ocr_extraction",
            filename=filename,
            pages=pages_to_process,
            method="tesseract_ocr"
        )

        text = _extract_with_tesseract(pdf_document, pages_to_process, filename, qube)
        pdf_document.close()
        return text

    except Exception as e:
        logger.error(
            "image_pdf_extraction_failed",
            filename=filename,
            error=str(e),
            exc_info=True
        )
        return ""


async def _extract_with_vision_api(
    qube,
    pdf_document,
    page_count: int,
    filename: str
) -> str:
    """
    Extract text from PDF pages using AI vision API.

    Args:
        qube: Qube instance
        pdf_document: PyMuPDF document object
        page_count: Number of pages to process
        filename: PDF filename for logging

    Returns:
        Extracted text or empty string
    """
    try:
        import fitz  # PyMuPDF
        from ai.model_registry import ModelRegistry

        # Determine which vision model to use
        if "anthropic" in qube.api_keys:
            vision_model = "claude-sonnet-4-5-20250929"
            provider = "anthropic"
        elif "openai" in qube.api_keys:
            vision_model = "gpt-4o"
            provider = "openai"
        elif "google" in qube.api_keys:
            vision_model = "gemini-2.0-flash"
            provider = "google"
        else:
            return ""

        api_key = qube.api_keys.get(provider)
        model_instance = ModelRegistry.get_model(vision_model, api_key)

        extracted_parts = []

        for page_num in range(page_count):
            page = pdf_document[page_num]

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better quality
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode('utf-8')

            # Build vision message based on provider
            if provider == "anthropic":
                messages = [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Extract all text from this document page (page {page_num + 1}). Preserve formatting, tables, and structure. Return only the extracted text, no commentary."
                        }
                    ]
                }]
            elif provider == "openai":
                messages = [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                        },
                        {
                            "type": "text",
                            "text": f"Extract all text from this document page (page {page_num + 1}). Preserve formatting, tables, and structure. Return only the extracted text, no commentary."
                        }
                    ]
                }]
            elif provider == "google":
                messages = [{
                    "role": "user",
                    "content": f"Extract all text from this document page (page {page_num + 1}). Preserve formatting, tables, and structure. Return only the extracted text, no commentary."
                }]

            # Call vision API
            response = await model_instance.generate(
                messages=messages,
                max_tokens=2000,
                temperature=0.0
            )

            page_text = response.content.strip() if response.content else ""
            if page_text:
                extracted_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            logger.debug(
                "vision_page_extracted",
                filename=filename,
                page=page_num + 1,
                text_length=len(page_text)
            )

            # Emit progress event for frontend
            if hasattr(qube, 'events'):
                from core.events import Events
                percentage = int(((page_num + 1) / page_count) * 100)
                qube.events.emit(Events.DOCUMENT_PROCESSING_PROGRESS, {
                    "filename": filename,
                    "current_page": page_num + 1,
                    "total_pages": page_count,
                    "percentage": percentage
                })

        if extracted_parts:
            full_text = "\n\n".join(extracted_parts)
            logger.info(
                "vision_extraction_successful",
                filename=filename,
                pages_processed=page_count,
                total_text_length=len(full_text)
            )
            return full_text

        return ""

    except Exception as e:
        logger.error(
            "vision_api_extraction_error",
            filename=filename,
            error=str(e),
            exc_info=True
        )
        return ""


def _extract_with_tesseract(
    pdf_document,
    page_count: int,
    filename: str,
    qube=None
) -> str:
    """
    Extract text from PDF pages using Tesseract OCR (local).

    Args:
        pdf_document: PyMuPDF document object
        page_count: Number of pages to process
        filename: PDF filename for logging

    Returns:
        Extracted text or empty string
    """
    try:
        import pytesseract
        import fitz  # PyMuPDF
        from PIL import Image
        import io

        extracted_parts = []

        for page_num in range(page_count):
            page = pdf_document[page_num]

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better quality
            img_data = pix.tobytes("png")

            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))

            # Run OCR
            page_text = pytesseract.image_to_string(image).strip()

            if page_text:
                extracted_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            logger.debug(
                "ocr_page_extracted",
                filename=filename,
                page=page_num + 1,
                text_length=len(page_text)
            )

            # Emit progress event for frontend
            if qube and hasattr(qube, 'events'):
                from core.events import Events
                percentage = int(((page_num + 1) / page_count) * 100)
                qube.events.emit(Events.DOCUMENT_PROCESSING_PROGRESS, {
                    "filename": filename,
                    "current_page": page_num + 1,
                    "total_pages": page_count,
                    "percentage": percentage
                })

        if extracted_parts:
            full_text = "\n\n".join(extracted_parts)
            logger.info(
                "tesseract_extraction_successful",
                filename=filename,
                pages_processed=page_count,
                total_text_length=len(full_text)
            )
            return full_text

        return ""

    except ImportError:
        logger.warning(
            "tesseract_not_available",
            filename=filename,
            message="pytesseract not installed - install with: pip install pytesseract"
        )
        return ""
    except Exception as e:
        logger.error(
            "tesseract_extraction_error",
            filename=filename,
            error=str(e),
            exc_info=True
        )
        return ""


async def process_pdf_to_action_block(
    qube,
    pdf_base64: str,
    filename: Optional[str] = None
) -> Tuple[Block, str]:
    """
    Extract PDF text and create ACTION block for document processing.

    This function:
    1. Decodes base64 PDF data
    2. Extracts text content using PyMuPDF
    3. Extracts metadata (page count, title, author, etc.)
    4. Creates an ACTION block with type "process_document"
    5. Stores extracted content in the result field (not parameters)

    The ACTION block will later be converted to a tool result in AI context,
    allowing the AI to process document content without bloating messages.

    Args:
        qube: The qube instance (for potential future use)
        pdf_base64: Base64-encoded PDF data
        filename: Original filename (defaults to "document.pdf")

    Returns:
        Tuple of (action_block, reference_string):
        - action_block: ACTION block dict with document data
        - reference_string: Human-readable reference like "[Document: file.pdf - 5 pages]"

    Example:
        >>> block, ref = process_pdf_to_action_block(qube, pdf_data, "report.pdf")
        >>> print(ref)
        "[Document: report.pdf - 12 pages]"
        >>> print(block["content"]["result"]["page_count"])
        12
    """
    if filename is None:
        filename = "document.pdf"

    # Calculate file size and hash for parameters
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        file_size = len(pdf_bytes)
        content_hash = hashlib.sha256(pdf_bytes).hexdigest()[:16]  # First 16 chars

        # Size limit: 10MB (prevents extremely large PDFs from hanging)
        max_size_bytes = 10 * 1024 * 1024  # 10MB
        if file_size > max_size_bytes:
            logger.warning(
                f"PDF too large: {file_size} bytes (max {max_size_bytes})",
                filename=filename
            )
            return _create_failed_action_block(
                filename=filename,
                file_size=file_size,
                content_hash=content_hash,
                error=f"PDF too large ({file_size // 1024 // 1024}MB). Maximum size is 10MB."
            )

        logger.info(
            "pdf_decoding_complete",
            filename=filename,
            file_size=file_size
        )

    except Exception as e:
        logger.error(f"Failed to decode PDF base64: {e}")
        return _create_failed_action_block(
            filename=filename,
            error=f"Failed to decode PDF: {str(e)}"
        )

    # Extract text and metadata
    try:
        logger.info(
            "starting_pdf_text_extraction",
            filename=filename,
            file_size=file_size
        )

        extracted_text = extract_text_from_pdf_base64(pdf_base64)

        logger.info(
            "pdf_text_extraction_complete",
            filename=filename,
            text_length=len(extracted_text) if extracted_text else 0
        )

        if not extracted_text or not extracted_text.strip():
            logger.warning(
                "pdf_text_extraction_empty_trying_ocr",
                filename=filename,
                file_size=file_size
            )

            # Try advanced extraction for image-only PDFs
            extracted_text = await _extract_from_image_pdf(
                qube=qube,
                pdf_base64=pdf_base64,
                filename=filename
            )

            if not extracted_text or not extracted_text.strip():
                logger.warning("all_extraction_methods_failed", filename=filename)
                return _create_failed_action_block(
                    filename=filename,
                    file_size=file_size,
                    content_hash=content_hash,
                    error="Could not extract text (tried text extraction, AI vision, and OCR)"
                )

        # Get metadata (page count, title, etc.)
        metadata = get_pdf_metadata(pdf_base64)
        page_count = metadata.get("page_count", 0)

        logger.info(
            "pdf_extracted_successfully",
            filename=filename,
            file_size=file_size,
            page_count=page_count,
            text_length=len(extracted_text)
        )

        # Create successful ACTION block
        # Use -1 as placeholder - session will assign actual block number
        action_block = create_action_block(
            qube_id=qube.qube_id,
            block_number=-1,  # Placeholder for session block
            action_type="process_document",
            parameters={
                "filename": filename,
                "file_size_bytes": file_size,
                "content_hash": content_hash
            },
            result={
                "success": True,
                "extracted_text": extracted_text,
                "page_count": page_count,
                "extraction_method": "pymupdf",
                "metadata": {
                    "title": metadata.get("title"),
                    "author": metadata.get("author"),
                    "creation_date": metadata.get("creation_date"),
                    "subject": metadata.get("subject")
                }
            },
            status="completed",
            temporary=True  # Session block
        )

        # Create human-readable reference string
        page_str = f"{page_count} page{'s' if page_count != 1 else ''}"
        reference_string = f"[Document: {filename} - {page_str}]"

        return action_block, reference_string

    except Exception as e:
        logger.error(
            "pdf_extraction_failed",
            filename=filename,
            error=str(e),
            exc_info=True
        )
        return _create_failed_action_block(
            filename=filename,
            file_size=file_size,
            content_hash=content_hash,
            error=str(e)
        )


def _create_failed_action_block(
    filename: str,
    file_size: Optional[int] = None,
    content_hash: Optional[str] = None,
    error: str = "Unknown error"
) -> Tuple[Block, str]:
    """
    Create an ACTION block for a failed document processing operation.

    Args:
        filename: Name of the document
        file_size: Size in bytes (if available)
        content_hash: SHA256 hash (if available)
        error: Error message describing the failure

    Returns:
        Tuple of (action_block, reference_string)
    """
    # Create parameters dict (only include available fields)
    parameters = {"filename": filename}
    if file_size is not None:
        parameters["file_size_bytes"] = file_size
    if content_hash is not None:
        parameters["content_hash"] = content_hash

    # Create failed ACTION block
    # Use -1 as placeholder - session will assign actual block number
    action_block = create_action_block(
        qube_id="",  # Will be set when added to session
        block_number=-1,  # Placeholder for session block
        action_type="process_document",
        parameters=parameters,
        result={
            "success": False,
            "error": error,
            "extracted_text": None,
            "page_count": 0
        },
        status="failed",
        temporary=True  # Session block
    )

    # Create reference string showing failure
    reference_string = f"[Document: {filename} - extraction failed: {error}]"

    return action_block, reference_string
