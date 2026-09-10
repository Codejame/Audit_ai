"""SQLAlchemy ORM model for storing processed document records."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from backend.app.core.database import Base

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_name = Column(String(255), index=True, nullable=False)
    document_type = Column(String(64), index=True, nullable=False)
    file_path = Column(String(512), nullable=True)
    file_hash = Column(String(64), nullable=True)
    file_type = Column(String(64), nullable=False)
    page_count = Column(Integer, default=1)
    processing_status = Column(String(32), default="PASS")  # PASS / FAILED
    overall_status = Column(String(32), default="PASS")     # PASS / FAIL
    overall_confidence = Column(Float, nullable=True)
    
    # Structured JSON stores
    file_validation = Column(JSON, nullable=False)
    extracted_data = Column(JSON, nullable=False)
    validation = Column(JSON, nullable=False)
    processing_metadata = Column(JSON, nullable=False)
    raw_response = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Converts model to dictionary."""
        return {
            "id": self.id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "file_type": self.file_type,
            "page_count": self.page_count,
            "processing_status": self.processing_status,
            "overall_status": self.overall_status,
            "overall_confidence": self.overall_confidence,
            "file_validation": self.file_validation,
            "extracted_data": self.extracted_data,
            "validation": self.validation,
            "processing_metadata": self.processing_metadata,
            "raw_response": self.raw_response,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
