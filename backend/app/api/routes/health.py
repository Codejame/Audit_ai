"""Health check route for container liveness and readiness probes."""
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health", summary="Health Check")
def health_check():
    """Returns service health status and current UTC timestamp."""
    return {
        "status": "healthy",
        "service": "document-intelligence-api",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
