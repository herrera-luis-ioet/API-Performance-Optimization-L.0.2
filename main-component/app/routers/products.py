"""Product management endpoints with CRUD operations.

This module implements REST API endpoints for product management with Redis caching
and rate limiting middleware.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.cache import cached, invalidate_cache
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse
)

router = APIRouter(prefix="/products", tags=["products"])

# PUBLIC_INTERFACE
@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
) -> ProductResponse:
    """Create a new product.
    
    Args:
        product: Product data
        db: Database session
        
    Returns:
        ProductResponse: Created product
        
    Raises:
        HTTPException: If product creation fails
    """
    try:
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        # Invalidate products list cache
        invalidate_cache("products:list")
        
        return ProductResponse.from_orm(db_product)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create product: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.get("/{product_id}", response_model=ProductResponse)
@cached("products:detail")
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
) -> ProductResponse:
    """Get product by ID.
    
    Args:
        product_id: Product identifier
        db: Database session
        
    Returns:
        ProductResponse: Product details
        
    Raises:
        HTTPException: If product not found
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    return ProductResponse.from_orm(product)

# PUBLIC_INTERFACE
@router.get("/", response_model=ProductListResponse)
@cached("products:list")
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ProductListResponse:
    """List products with pagination and optional search.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Optional search term for product name
        db: Database session
        
    Returns:
        ProductListResponse: List of products and total count
    """
    query = db.query(Product)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    
    return ProductListResponse(
        items=[ProductResponse.from_orm(p) for p in products],
        total=total
    )

# PUBLIC_INTERFACE
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
) -> ProductResponse:
    """Update product by ID.
    
    Args:
        product_id: Product identifier
        product: Updated product data
        db: Database session
        
    Returns:
        ProductResponse: Updated product
        
    Raises:
        HTTPException: If product not found or update fails
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    
    try:
        for key, value in product.dict(exclude_unset=True).items():
            setattr(db_product, key, value)
        
        db.commit()
        db.refresh(db_product)
        
        # Invalidate caches
        invalidate_cache("products:detail", product_id)
        invalidate_cache("products:list")
        
        return ProductResponse.from_orm(db_product)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update product: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
) -> None:
    """Delete product by ID.
    
    Args:
        product_id: Product identifier
        db: Database session
        
    Raises:
        HTTPException: If product not found or deletion fails
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    
    try:
        db.delete(db_product)
        db.commit()
        
        # Invalidate caches
        invalidate_cache("products:detail", product_id)
        invalidate_cache("products:list")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete product: {str(e)}"
        )