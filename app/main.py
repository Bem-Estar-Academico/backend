"""Main FastAPI application."""

from dotenv import load_dotenv

load_dotenv()

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.routers.appeal import router as appeal_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.ivs import router as ivs_router
from app.routers.notices import router as notices_router
from app.routers.period import router as periodo_router
from app.routers.student_documents import router as student_documents_router
from app.routers.student_registrations import router as student_registrations_router
from app.routers.users import router as users_router
from app.schemas.review_registration import ReviewRegistrationResponseWithDetails
from app.schemas.student_registration import StudentRegistrationWithReviewResponse

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="BEA API",
    version="v1.0.0",
    description="BEA API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)
logger.info("Starting BEA API v1.0.0")
logger.info(f"Environment: {settings.ENVIRONMENT}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(appeal_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(notices_router, prefix=settings.API_V1_STR)
app.include_router(ivs_router, prefix=settings.API_V1_STR)
app.include_router(student_registrations_router, prefix=f"{settings.API_V1_STR}")
app.include_router(
    student_documents_router,
    prefix=f"{settings.API_V1_STR}",
)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(periodo_router, prefix=f"{settings.API_V1_STR}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "BEA API",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Rebuild Pydantic models to resolve forward references
ReviewRegistrationResponseWithDetails.model_rebuild()
StudentRegistrationWithReviewResponse.model_rebuild()
