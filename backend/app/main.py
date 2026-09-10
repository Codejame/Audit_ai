"""Main FastAPI application entry point with API routes and Jinja2 frontend views."""
import os
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import init_db, get_db
from backend.app.core.logging import logger
from backend.app.api.routes import documents, health
from backend.app.services.document_service import DocumentService

# Define root paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database initialized successfully.")
    yield

# Initialize FastAPI
app = FastAPI(
    title="Intelligent Document Extraction, Validation & API Platform",
    description=(
        "Production-ready Document Intelligence API and Dashboard for financial documents "
        "(Invoices, Balance Sheets, Profit & Loss, Cash Flow Statements). "
        "Built for AI Engineer Internship Assessment."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for all origins in development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include REST API routes
app.include_router(health.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")

# -----------------------------------------------------------------------------
# FRONTEND VIEWS (HTML/CSS Dashboard)
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, summary="Frontend Dashboard")
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    """Renders the main upload and processed documents dashboard."""
    service = DocumentService(db)
    documents_list = service.list_documents()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "documents": documents_list,
            "project_name": settings.PROJECT_NAME
        }
    )

@app.get("/documents/{document_name}", response_class=HTMLResponse, summary="Document Details View")
def document_result_view(request: Request, document_name: str, db: Session = Depends(get_db)):
    """Renders the structured extraction result and financial validations view."""
    service = DocumentService(db)
    result = service.get_document_by_name(document_name)
    if not result:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "documents": service.list_documents(),
                "project_name": settings.PROJECT_NAME,
                "error_message": f"Document '{document_name}' not found."
            },
            status_code=404
        )

    return templates.TemplateResponse(
        request=request,
        name="document_result.html",
        context={
            "doc": result,
            "document_name": document_name,
            "project_name": settings.PROJECT_NAME
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
