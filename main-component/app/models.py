"""SQLAlchemy models for the API service.

This module defines the database models for products and orders using SQLAlchemy ORM.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

class Product(Base):
    """Product model representing items available for purchase.
    
    Attributes:
        id: Unique identifier for the product
        name: Product name
        description: Detailed product description
        price: Product price
        stock: Current stock quantity
        created_at: Timestamp of product creation
        updated_at: Timestamp of last update
        orders: Relationship to Order model through OrderItem
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with orders through OrderItem
    orders = relationship("OrderItem", back_populates="product")

class Order(Base):
    """Order model representing customer orders.
    
    Attributes:
        id: Unique identifier for the order
        customer_id: Identifier for the customer who placed the order
        status: Current status of the order
        total_amount: Total order amount
        created_at: Timestamp of order creation
        updated_at: Timestamp of last update
        items: Relationship to OrderItem model
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with order items
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    """OrderItem model representing items within an order.
    
    Attributes:
        id: Unique identifier for the order item
        order_id: Reference to the parent order
        product_id: Reference to the product
        quantity: Quantity of the product ordered
        unit_price: Price per unit at the time of order
        created_at: Timestamp of order item creation
        order: Relationship to Order model
        product: Relationship to Product model
    """
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="orders")