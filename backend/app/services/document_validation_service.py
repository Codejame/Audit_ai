"""Document input validation service for verifying MIME type, page limits, and file integrity."""
import io
import os
from typing import Tuple
from PIL import Image
import fitz  # PyMuPDF
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.extraction import FileValidation

class DocumentValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class DocumentValidationService:
    @staticmethod
    def validate_file(filename: str, content: bytes, content_type: str = None) -> FileValidation:
        """
        Validates uploaded file before extraction.
        Checks:
        1. Non-empty file.
        2. Extension and MIME type in allowed list.
        3. Readability / corruption check.
        4. Page count limit (<= 3 pages).
        """
        logger.info(f"Validating file: {filename} ({len(content)} bytes)")

        if not content or len(content) == 0:
            logger.warning(f"File {filename} is empty")
            raise DocumentValidationError("CORRUPTED_OR_EMPTY_FILE", "Uploaded file is empty or corrupted.")

        # Determine extension
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in settings.ALLOWED_EXTENSIONS:
            logger.warning(f"File {filename} has unsupported extension: {ext}")
            raise DocumentValidationError(
                "UNSUPPORTED_FILE_TYPE",
                "Only PDF / JPG / PNG documents are supported."
            )

        # PDF Handling
        if ext == "pdf":
            mime = "application/pdf"
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                page_count = len(doc)
                if page_count == 0:
                    raise DocumentValidationError("CORRUPTED_OR_EMPTY_FILE", "PDF file has no readable pages.")
                if page_count > settings.MAX_PAGE_LIMIT:
                    logger.warning(f"File {filename} exceeds page limit ({page_count} > {settings.MAX_PAGE_LIMIT})")
                    raise DocumentValidationError(
                        "PAGE_LIMIT_EXCEEDED",
                        f"Document contains {page_count} pages. Maximum allowed limit is {settings.MAX_PAGE_LIMIT} pages."
                    )
                doc.close()
            except DocumentValidationError:
                raise
            except Exception as e:
                logger.error(f"Failed to read PDF {filename}: {str(e)}")
                raise DocumentValidationError("CORRUPTED_OR_EMPTY_FILE", "Failed to parse PDF file; document may be corrupted.")

            return FileValidation(
                file_type=mime,
                is_supported=True,
                is_readable=True,
                page_count=page_count,
                status="PASS"
            )

        # Image Handling (JPG/PNG)
        if ext in ("jpg", "jpeg", "png"):
            mime = "image/png" if ext == "png" else "image/jpeg"
            try:
                with Image.open(io.BytesIO(content)) as img:
                    img.verify()  # Verify integrity
                page_count = 1
            except Exception as e:
                logger.error(f"Image {filename} integrity check failed: {str(e)}")
                raise DocumentValidationError("CORRUPTED_OR_EMPTY_FILE", "Uploaded image file is corrupted or unreadable.")

            return FileValidation(
                file_type=mime,
                is_supported=True,
                is_readable=True,
                page_count=page_count,
                status="PASS"
            )

        raise DocumentValidationError(
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF / JPG / PNG documents are supported."
        )

    @staticmethod
    def validate_schema_alignment(filename: str, selected_type: str, extracted_text: str = "") -> None:
        """
        Validates that the uploaded document's name and textual content
        align with the user-selected document category/schema.
        Prevents uploading a Balance Sheet under Cash Flow Statement, etc.
        """
        fn_lower = filename.lower()
        txt_lower = extracted_text.lower() if extracted_text else ""

        detected_type = None
        # Check strong signals for balance sheet
        if any(term in fn_lower for term in ["balance sheet", "balance_sheet", "balancesheet"]) or \
           ("balance sheet" in txt_lower and "capital and liabilities" in txt_lower):
            detected_type = "balance_sheet"
        # Check strong signals for cash flow
        elif any(term in fn_lower for term in ["cash flow", "cash_flow", "cashflow"]) or \
             ("cash flow statement" in txt_lower and "cash and cash equivalents" in txt_lower):
            detected_type = "cash_flow_statement"
        # Check strong signals for profit & loss
        elif any(term in fn_lower for term in ["profit & loss", "profit and loss", "profit_loss", "p&l", "profit_and_loss"]) or \
             ("profit and loss" in txt_lower or "interest expended" in txt_lower):
            detected_type = "profit_and_loss"
        # Check strong signals for invoice
        elif any(term in fn_lower for term in ["invoice", "tax_invoice", "receipt", "bill"]) or \
             ("tax invoice" in txt_lower or "bill to" in txt_lower or "invoice no" in txt_lower):
            detected_type = "invoice"

        type_names = {
            "invoice": "Invoice",
            "balance_sheet": "Balance Sheet",
            "profit_and_loss": "Profit & Loss Statement",
            "cash_flow_statement": "Cash Flow Statement"
        }

        if detected_type and detected_type != selected_type:
            expected_name = type_names.get(detected_type, detected_type)
            selected_name = type_names.get(selected_type, selected_type)
            logger.warning(
                f"Document schema mismatch for '{filename}': detected '{detected_type}' but user selected '{selected_type}'"
            )
            raise DocumentValidationError(
                "DOCUMENT_SCHEMA_MISMATCH",
                f"Document category mismatch: Uploaded file '{filename}' appears to be a {expected_name}, but '{selected_name}' was selected in the dropdown. Please select '{expected_name}' to process this document."
            )
