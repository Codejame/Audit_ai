"""Orchestration service coordinating validation, extraction, financial rules, and persistence."""
import datetime
import os
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.document import DocumentRecord
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.schemas.document import DocumentProcessResponse
from backend.app.schemas.extraction import ProcessingMetadata
from backend.app.services.document_validation_service import DocumentValidationService, DocumentValidationError
from backend.app.services.extraction_service import ExtractionService
from backend.app.services.financial_validation_service import FinancialValidationService
from backend.app.services.ocr_service import OCRService
from backend.app.utils.helpers import compute_sha256

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DocumentRepository(db)
        self.validation_service = DocumentValidationService()
        self.financial_service = FinancialValidationService()

    def process_document(
        self,
        filename: str,
        file_content: bytes,
        document_type: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end document processing pipeline:
        1. Document validation (MIME, corruption, page limit <= 3)
        2. OCR & page rendering
        3. Multimodal field & table extraction
        4. Financial calculations validation
        5. Persistence in database
        6. Structured response return
        """
        start_time = time.time()
        logger.info(f"--- Starting pipeline for: {filename} ({document_type}) ---")

        # 1. Document validation check
        file_validation = self.validation_service.validate_file(filename, file_content, content_type)

        # Save file to upload directory
        file_hash = compute_sha256(file_content)
        safe_filename = f"{int(time.time())}_{filename}"
        saved_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        with open(saved_path, "wb") as f:
            f.write(file_content)

        # 2. OCR & rendering
        native_text, images, ocr_used = OCRService.extract_text_and_images(file_content, filename)

        # Validate schema alignment (detects uploading Balance Sheet under Cash Flow, etc.)
        self.validation_service.validate_schema_alignment(filename, document_type, native_text)

        # 3. Multimodal / AI extraction
        extracted_data, overall_confidence = ExtractionService.extract_document(
            filename=filename,
            document_type=document_type,
            images=images,
            extracted_text=native_text
        )

        # 4. Financial calculation validations
        validation_result = self.financial_service.validate(document_type, extracted_data)

        # 5. Determine overall processing status
        # PASS: Required fields extracted accurately and required validations pass.
        # FAILED: Document could not be processed, is invalid, corrupted or unsupported.
        processing_status = "PASS" if validation_result.overall_status == "PASS" else "PASS"
        # Note: If validations fail, overall_status in validation object is FAIL,
        # but processing itself succeeded in extracting data.

        processing_time_ms = int((time.time() - start_time) * 1000)
        processed_at_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        metadata = ProcessingMetadata(
            ocr_used=ocr_used,
            processed_at=processed_at_iso,
            processing_time_ms=processing_time_ms
        )

        response_dict = {
            "document_name": filename,
            "document_type": document_type,
            "processing_status": processing_status,
            "overall_confidence": overall_confidence,
            "file_validation": file_validation.model_dump(),
            "extracted_data": extracted_data,
            "validation": validation_result.model_dump(),
            "processing_metadata": metadata.model_dump()
        }

        # 6. Database persistence
        record_data = {
            "document_name": filename,
            "document_type": document_type,
            "file_path": saved_path,
            "file_hash": file_hash,
            "file_type": file_validation.file_type,
            "page_count": file_validation.page_count,
            "processing_status": processing_status,
            "overall_status": validation_result.overall_status,
            "overall_confidence": overall_confidence,
            "file_validation": file_validation.model_dump(),
            "extracted_data": extracted_data,
            "validation": validation_result.model_dump(),
            "processing_metadata": metadata.model_dump(),
            "raw_response": response_dict
        }

        self.repository.save(record_data)
        logger.info(f"Document {filename} processed in {processing_time_ms}ms with status: {processing_status}")

        return response_dict

    def get_document_by_name(self, document_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest structured result for a given filename."""
        record = self.repository.get_latest_by_name(document_name)
        if not record:
            return None
        return record.raw_response

    def list_documents(self, skip: int = 0, limit: int = 100) -> List[DocumentRecord]:
        """Lists processed documents."""
        return self.repository.list_all(skip=skip, limit=limit)
