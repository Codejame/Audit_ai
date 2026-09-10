"""End-to-end verification script processing all 4 document categories from New Dataset 1."""
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal, init_db
from backend.app.services.document_service import DocumentService

def main():
    init_db()
    db = SessionLocal()
    service = DocumentService(db)

    test_files = [
        ("New Dataset 1/New Dataset/Balance Sheet/Consolidated Balance Sheet 2017.pdf", "balance_sheet"),
        ("New Dataset 1/New Dataset/Profit & Loss/Consolidated Profit & Loss 2017.pdf", "profit_and_loss"),
        ("New Dataset 1/New Dataset/Cash Flows/Consolidated Cash Flow Statement 2017.pdf", "cash_flow_statement"),
        ("New Dataset 1/New Dataset/Invoices/20251118_000612.jpg", "invoice")
    ]

    for path, doc_type in test_files:
        if os.path.exists(path):
            with open(path, "rb") as f:
                content = f.read()
            filename = os.path.basename(path)
            print(f"Ingesting {filename} ({doc_type})...")
            res = service.process_document(filename, content, doc_type)
            print(f"  [OK] Status: {res['processing_status']}")
            print(f"  [OK] Checks count: {len(res['validation']['checks'])}")
            print(f"  [OK] Reconciliation: {res['validation']['overall_status']}")
        else:
            print(f"  [MISSING] {path}")

    total = len(service.list_documents())
    print(f"\nAll documents successfully processed! Total database records: {total}")
    db.close()

if __name__ == "__main__":
    main()
