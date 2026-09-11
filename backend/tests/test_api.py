"""Integration tests for FastAPI REST endpoints."""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import init_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is created before tests."""
    init_db()

def test_health_check_endpoint():
    """Verify GET /api/v1/health returns status healthy."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_api_v1_root_endpoint():
    """Verify GET /api/v1 returns discovery metadata."""
    response = client.get("/api/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "docs_url" in data
    assert "endpoints" in data

def test_process_invalid_file_type_returns_400():
    """Verify uploading unsupported file type returns 400 with UNSUPPORTED_FILE_TYPE."""
    file_payload = ("test.txt", io.BytesIO(b"Unsupported plain text"), "text/plain")
    response = client.post(
        "/api/v1/documents/process",
        files={"file": file_payload},
        data={"document_type": "invoice"}
    )
    assert response.status_code == 400
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

def test_process_invalid_document_type_returns_400():
    """Verify invalid document type parameter returns 400."""
    from backend.tests.test_validation import create_dummy_pdf
    pdf_bytes = create_dummy_pdf(1)
    file_payload = ("dummy.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    response = client.post(
        "/api/v1/documents/process",
        files={"file": file_payload},
        data={"document_type": "passport"}
    )
    assert response.status_code == 400
    err = response.json()
    assert err["error"]["code"] == "INVALID_DOCUMENT_TYPE"

def test_process_document_category_mismatch_returns_400():
    """Verify selecting wrong document category (e.g. cash flow for balance sheet) returns 400."""
    from backend.tests.test_validation import create_dummy_pdf
    pdf_bytes = create_dummy_pdf(1)
    file_payload = ("Consolidated Balance Sheet 2017.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    response = client.post(
        "/api/v1/documents/process",
        files={"file": file_payload},
        data={"document_type": "cash_flow_statement"}
    )
    assert response.status_code == 400
    err = response.json()
    assert err["error"]["code"] == "DOCUMENT_SCHEMA_MISMATCH"
    assert "Document category mismatch" in err["error"]["message"]

def test_process_valid_document_pipeline():
    """Verify end-to-end processing of a valid document."""
    from backend.tests.test_validation import create_dummy_pdf
    pdf_bytes = create_dummy_pdf(1)
    file_payload = ("sample_invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    
    response = client.post(
        "/api/v1/documents/process",
        files={"file": file_payload},
        data={"document_type": "invoice"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_name"] == "sample_invoice.pdf"
    assert data["document_type"] == "invoice"
    assert data["processing_status"] in ("PASS", "FAILED")
    assert "file_validation" in data
    assert "extracted_data" in data
    assert "validation" in data
    assert "processing_metadata" in data

def test_get_document_by_name_success():
    """Verify GET /api/v1/documents/{document_name} returns latest structured result."""
    response = client.get("/api/v1/documents/sample_invoice.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["document_name"] == "sample_invoice.pdf"

def test_get_document_by_name_not_found():
    """Verify 404 for non-existent document."""
    response = client.get("/api/v1/documents/non_existent_file.pdf")
    assert response.status_code == 404
    err = response.json()
    assert err["error"]["code"] == "DOCUMENT_NOT_FOUND"

def test_list_documents_dashboard():
    """Verify GET /api/v1/documents returns list of records."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
