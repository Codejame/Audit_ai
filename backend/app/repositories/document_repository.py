"""Repository pattern for Document database operations."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.document import DocumentRecord

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, record_data: dict) -> DocumentRecord:
        """Create or update an existing DocumentRecord by document_name."""
        existing = self.get_latest_by_name(record_data.get("document_name"))
        if existing:
            for k, v in record_data.items():
                setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = DocumentRecord(**record_data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_by_name(self, document_name: str) -> Optional[DocumentRecord]:
        """Fetch the most recent processed result for a given filename."""
        return (
            self.db.query(DocumentRecord)
            .filter(DocumentRecord.document_name == document_name)
            .order_by(desc(DocumentRecord.created_at), desc(DocumentRecord.id))
            .first()
        )

    def get_by_id(self, doc_id: int) -> Optional[DocumentRecord]:
        """Fetch a record by primary key."""
        return self.db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[DocumentRecord]:
        """List documents ordered by latest processed first."""
        query = self.db.query(DocumentRecord)
        if document_type:
            query = query.filter(DocumentRecord.document_type == document_type)
        if status:
            query = query.filter(DocumentRecord.processing_status == status)
        return query.order_by(desc(DocumentRecord.created_at), desc(DocumentRecord.id)).offset(skip).limit(limit).all()

    def count_all(self) -> int:
        """Count total processed records."""
        return self.db.query(DocumentRecord).count()
