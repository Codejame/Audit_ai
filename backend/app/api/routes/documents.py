"""Document processing and retrieval API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.schemas.document import (
    DocumentProcessResponse,
    DocumentType,
    ErrorResponse
)
from backend.app.services.document_service import DocumentService
from backend.app.services.document_validation_service import DocumentValidationError

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post(
    "/process",
    response_model=DocumentProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation failure or unsupported format"},
        500: {"model": ErrorResponse, "description": "Internal processing error"}
    },
    summary="Upload and process financial document"
)
async def process_document(
    file: UploadFile = File(..., description="PDF / JPG / PNG document to process (max 3 pages)"),
    document_type: str = Form(..., description="One of: invoice, balance_sheet, profit_and_loss, cash_flow_statement"),
    db: Session = Depends(get_db)
):
    """
    Accepts multipart document upload, validates integrity, runs OCR & multimodal AI extraction,
    executes financial calculations, and stores structured JSON in the database.
    """
    # Normalize document_type
    doc_type_clean = document_type.strip().lower()
    valid_types = [t.value for t in DocumentType]
    if doc_type_clean not in valid_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_DOCUMENT_TYPE",
                    "message": f"Invalid document_type '{document_type}'. Must be one of: {', '.join(valid_types)}"
                }
            }
        )

    try:
        content = await file.read()
        service = DocumentService(db)
        result = service.process_document(
            filename=file.filename,
            file_content=content,
            document_type=doc_type_clean,
            content_type=file.content_type
        )
        return result

    except DocumentValidationError as ve:
        logger.warning(f"Validation error for {file.filename}: {ve.code} - {ve.message}")
        return JSONResponse(
            status_code=ve.status_code,
            content={"error": {"code": ve.code, "message": ve.message}}
        )
    except Exception as e:
        logger.error(f"Unexpected processing error for {file.filename}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_PROCESSING_ERROR", "message": "Failed to process document due to an internal server error."}}
        )

@router.get(
    "/{document_name}",
    response_model=DocumentProcessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"}
    },
    summary="Retrieve latest structured result for a document"
)
def get_document_by_name(
    document_name: str,
    db: Session = Depends(get_db)
):
    """Retrieves the latest processed structured JSON for a given document name."""
    service = DocumentService(db)
    result = service.get_document_by_name(document_name)
    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"No processed document found with name '{document_name}'."
                }
            }
        )
    return result

@router.get(
    "",
    summary="List all processed documents for the dashboard"
)
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Returns a list of all processed documents with metadata and processing status."""
    service = DocumentService(db)
    records = service.list_documents(skip=skip, limit=limit)
    return [
        {
            "id": r.id,
            "document_name": r.document_name,
            "document_type": r.document_type,
            "file_type": r.file_type,
            "page_count": r.page_count,
            "processing_status": r.processing_status,
            "overall_status": r.overall_status,
            "overall_confidence": r.overall_confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
