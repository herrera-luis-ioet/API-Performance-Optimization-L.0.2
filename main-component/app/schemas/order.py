"""Order schemas for request/response validation and serialization.

This module defines Pydantic models for order-related data validation and serialization.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from .product import ProductResponse

class OrderItemBase(BaseModel):
    """Base schema for order items.
    
    Attributes:
        product_id: ID of the ordered product
        quantity: Quantity of the product ordered
    """
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class OrderItemCreate(OrderItemBase):
    """Schema for creating a new order item."""
    pass

class OrderItemResponse(OrderItemBase):
    """Schema for order item response data.
    
    Includes all order item attributes including database fields.
    """
    id: int
    unit_price: float
    created_at: datetime
    product: ProductResponse

    class Config:
        """Pydantic configuration."""
        orm_mode = True

class OrderBase(BaseModel):
    """Base order schema with common attributes.
    
    Attributes:
        customer_id: ID of the customer placing the order
        status: Order status (pending, confirmed, shipped, delivered, cancelled)
    """
    customer_id: int = Field(..., gt=0)
    status: str = Field(
        "pending",
        regex="^(pending|confirmed|shipped|delivered|cancelled)$"
    )

class OrderCreate(OrderBase):
    """Schema for creating a new order.
    
    Includes list of order items.
    """
    items: List[OrderItemCreate] = Field(..., min_items=1)

    @validator("items")
    def validate_items(cls, items):
        """Validate that order items are not duplicated."""
        product_ids = set()
        for item in items:
            if item.product_id in product_ids:
                raise ValueError(f"Duplicate product ID: {item.product_id}")
            product_ids.add(item.product_id)
        return items

class OrderUpdate(BaseModel):
    """Schema for updating an existing order.
    
    All fields are optional to allow partial updates.
    """
    status: Optional[str] = Field(
        None,
        regex="^(pending|confirmed|shipped|delivered|cancelled)$"
    )

class OrderResponse(OrderBase):
    """Schema for order response data.
    
    Includes all order attributes including database fields and items.
    """
    id: int
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]

    class Config:
        """Pydantic configuration."""
        orm_mode = True

class OrderListResponse(BaseModel):
    """Schema for paginated order list response.
    
    Attributes:
        items: List of orders
        total: Total number of orders matching the query
    """
    items: List[OrderResponse]
    total: int