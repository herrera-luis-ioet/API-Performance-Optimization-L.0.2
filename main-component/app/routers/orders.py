"""Order management endpoints with CRUD operations.

This module implements REST API endpoints for order management with Redis caching,
proper relationship handling with products, and validation.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Order, OrderItem, Product
from app.cache import cached, invalidate_cache
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse
)

router = APIRouter(prefix="/orders", tags=["orders"])

# PUBLIC_INTERFACE
@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db)
) -> OrderResponse:
    """Create a new order with items.
    
    Args:
        order: Order data with items
        db: Database session
        
    Returns:
        OrderResponse: Created order with items
        
    Raises:
        HTTPException: If order creation fails or products not found
    """
    try:
        # Create order
        db_order = Order(
            customer_id=order.customer_id,
            status=order.status
        )
        db.add(db_order)
        
        # Add order items and calculate total
        total_amount = 0.0
        for item in order.items:
            # Get product and validate stock
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                db.rollback()
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found"
                )
            
            if product.stock < item.quantity:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product {item.product_id}"
                )
            
            # Create order item
            db_item = OrderItem(
                order=db_order,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price
            )
            db.add(db_item)
            
            # Update product stock
            product.stock -= item.quantity
            total_amount += product.price * item.quantity
        
        # Update order total
        db_order.total_amount = total_amount
        
        db.commit()
        db.refresh(db_order)
        
        # Invalidate caches
        invalidate_cache("orders:list")
        invalidate_cache("products:list")  # Stock changes affect product list
        
        return OrderResponse.from_orm(db_order)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database integrity error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create order: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.get("/{order_id}", response_model=OrderResponse)
@cached("orders:detail")
async def get_order(
    order_id: int,
    db: Session = Depends(get_db)
) -> OrderResponse:
    """Get order by ID.
    
    Args:
        order_id: Order identifier
        db: Database session
        
    Returns:
        OrderResponse: Order details with items
        
    Raises:
        HTTPException: If order not found
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    return OrderResponse.from_orm(order)

# PUBLIC_INTERFACE
@router.get("/", response_model=OrderListResponse)
@cached("orders:list")
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> OrderListResponse:
    """List orders with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        customer_id: Optional customer ID filter
        status: Optional order status filter
        db: Database session
        
    Returns:
        OrderListResponse: List of orders and total count
    """
    query = db.query(Order)
    
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return OrderListResponse(
        items=[OrderResponse.from_orm(o) for o in orders],
        total=total
    )

# PUBLIC_INTERFACE
@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order: OrderUpdate,
    db: Session = Depends(get_db)
) -> OrderResponse:
    """Update order status.
    
    Args:
        order_id: Order identifier
        order: Updated order data
        db: Database session
        
    Returns:
        OrderResponse: Updated order
        
    Raises:
        HTTPException: If order not found or update fails
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    
    try:
        # Update status
        if order.status:
            db_order.status = order.status
        
        db.commit()
        db.refresh(db_order)
        
        # Invalidate caches
        invalidate_cache("orders:detail", order_id)
        invalidate_cache("orders:list")
        
        return OrderResponse.from_orm(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update order: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
) -> None:
    """Delete order by ID.
    
    This will also delete all associated order items and restore product stock.
    
    Args:
        order_id: Order identifier
        db: Database session
        
    Raises:
        HTTPException: If order not found or deletion fails
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    
    try:
        # Restore product stock
        for item in db_order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
        
        # Delete order (cascade will handle items)
        db.delete(db_order)
        db.commit()
        
        # Invalidate caches
        invalidate_cache("orders:detail", order_id)
        invalidate_cache("orders:list")
        invalidate_cache("products:list")  # Stock changes affect product list
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete order: {str(e)}"
        )