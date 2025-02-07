"""API routers package.

This package contains FastAPI routers for different API endpoints.
"""
from fastapi import APIRouter

from .products import router as products_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(products_router)

__all__ = ["api_router"]