"""Main FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Create FastAPI application
app = FastAPI(
    title="BEA API",
    version="v1.0.0",
    description="BEA API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)
logger.info(f"Starting BEA API v1.0.0")
logger.info(f"Environment: {settings.ENVIRONMENT}")

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

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


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
