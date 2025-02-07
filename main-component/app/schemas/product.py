"""Product schemas for request/response validation and serialization.

This module defines Pydantic models for product-related data validation and serialization.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    """Base product schema with common attributes.
    
    Attributes:
        name: Product name
        description: Optional product description
        price: Product price
        stock: Current stock quantity
    """
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)

class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass

class ProductUpdate(BaseModel):
    """Schema for updating an existing product.
    
    All fields are optional to allow partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    """Schema for product response data.
    
    Includes all product attributes including database fields.
    """
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True

class ProductListResponse(BaseModel):
    """Schema for paginated product list response.
    
    Attributes:
        items: List of products
        total: Total number of products matching the query
    """
    items: List[ProductResponse]
    total: int