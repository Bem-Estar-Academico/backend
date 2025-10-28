"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.routers.auth import router as auth_router
from app.routers.notices import router as notices_router
from app.routers.student_registrations import router as student_registrations_router
from app.routers.users import router as users_router
from app.routers.ivs import router as ivs_router
from app.routers.appeal import router as appeal_router

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
logger.info(f"Starting BEA API v1.0.0")
logger.info(f"Environment: {settings.ENVIRONMENT}")

# CORS setup
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(appeal_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(notices_router, prefix=settings.API_V1_STR)
app.include_router(ivs_router, prefix=settings.API_V1_STR)
app.include_router(student_registrations_router, prefix=f"{settings.API_V1_STR}")


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
