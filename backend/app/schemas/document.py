"""Pydantic schemas for API request and response bodies."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.extraction import (
    FileValidation,
    ValidationResult,
    ProcessingMetadata
)

class DocumentType(str, Enum):
    INVOICE = "invoice"
    BALANCE_SHEET = "balance_sheet"
    PROFIT_AND_LOSS = "profit_and_loss"
    CASH_FLOW_STATEMENT = "cash_flow_statement"

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

class DocumentProcessResponse(BaseModel):
    """The mandatory structured response format mandated by Section 5.2."""
    document_name: str
    document_type: str
    processing_status: str = Field(description="PASS or FAILED")
    overall_confidence: Optional[float] = None
    file_validation: FileValidation
    extracted_data: Dict[str, Any]
    validation: ValidationResult
    processing_metadata: ProcessingMetadata

class DocumentListItem(BaseModel):
    id: int
    document_name: str
    document_type: str
    file_type: str
    page_count: int
    processing_status: str
    overall_status: str
    overall_confidence: Optional[float] = None
    created_at: Optional[str] = None

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentListItem]
