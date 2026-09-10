"""Automated tests for document input validation, integrity, and constraints."""
import io
import pytest
from PIL import Image
import fitz

from backend.app.services.document_validation_service import (
    DocumentValidationService,
    DocumentValidationError
)

def create_dummy_pdf(num_pages: int = 1) -> bytes:
    """Helper to generate in-memory dummy PDF."""
    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), "Test Financial Document Page Content")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_dummy_image(format: str = "PNG") -> bytes:
    """Helper to generate in-memory valid image."""
    img = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

def test_valid_pdf_validation():
    """Verify standard 1-page PDF passes input validation."""
    content = create_dummy_pdf(1)
    val = DocumentValidationService.validate_file("invoice.pdf", content)
    assert val.status == "PASS"
    assert val.is_supported is True
    assert val.page_count == 1
    assert val.file_type == "application/pdf"

def test_valid_image_validation():
    """Verify PNG/JPG passes input validation."""
    content = create_dummy_image("JPEG")
    val = DocumentValidationService.validate_file("receipt.jpg", content)
    assert val.status == "PASS"
    assert val.is_supported is True
    assert val.page_count == 1

def test_unsupported_file_type_rejected():
    """Verify unsupported file types are rejected with UNSUPPORTED_FILE_TYPE."""
    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentValidationService.validate_file("balance_sheet.txt", b"Unsupported plain text")
    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"

def test_empty_file_rejected():
    """Verify empty 0-byte file is rejected with CORRUPTED_OR_EMPTY_FILE."""
    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentValidationService.validate_file("invoice.pdf", b"")
    assert exc_info.value.code == "CORRUPTED_OR_EMPTY_FILE"

def test_corrupted_file_rejected():
    """Verify corrupted file is rejected with CORRUPTED_OR_EMPTY_FILE."""
    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentValidationService.validate_file("corrupt.pdf", b"not a real pdf content header")
    assert exc_info.value.code == "CORRUPTED_OR_EMPTY_FILE"

def test_page_limit_exceeded_rejected():
    """Verify documents exceeding 3 pages are rejected with PAGE_LIMIT_EXCEEDED."""
    content = create_dummy_pdf(4)
    with pytest.raises(DocumentValidationError) as exc_info:
        DocumentValidationService.validate_file("long_document.pdf", content)
    assert exc_info.value.code == "PAGE_LIMIT_EXCEEDED"
