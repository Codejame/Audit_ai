"""Pydantic schemas for extracted data, evidence, and financial validation checks."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class GroundedValue(BaseModel):
    """Represents an extracted value with grounding/evidence."""
    value: Optional[Union[str, float, int, bool]] = None
    confidence: Optional[float] = None
    page_number: Optional[int] = 1
    source_text: Optional[str] = None

class ValidationCheck(BaseModel):
    """Represents an individual financial calculation reconciliation check."""
    name: str
    formula: str
    operands: Dict[str, Optional[Union[float, int]]]
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = 0.0
    status: str = Field(description="PASS, FAIL, or NOT_APPLICABLE")

class ValidationResult(BaseModel):
    """Collection of validation checks and overall reconciliation status."""
    checks: List[ValidationCheck] = []
    overall_status: str = Field(default="PASS", description="PASS or FAIL")
    issues: List[str] = []

class ProcessingMetadata(BaseModel):
    """Technical metadata for observability and audit trail."""
    ocr_used: bool = True
    processed_at: str
    processing_time_ms: int

class FileValidation(BaseModel):
    """Pre-extraction input validation status."""
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: str = Field(description="PASS or FAILED")
    details: Optional[str] = None
