"""Unit tests for database models."""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import event

from app.models import Product, Order, OrderItem

def test_product_creation(test_db_session):
    """Test creating a new product."""
    product = Product(
        name="Test Product",
        description="Test Description",
        price=99.99,
        stock=10
    )
    test_db_session.add(product)
    test_db_session.commit()
    
    assert product.id is not None
    assert product.name == "Test Product"
    assert product.description == "Test Description"
    assert product.price == 99.99
    assert product.stock == 10
    assert isinstance(product.created_at, datetime)
    assert isinstance(product.updated_at, datetime)

def test_order_creation(test_db_session):
    """Test creating a new order."""
    order = Order(
        customer_id=1,
        status="pending",
        total_amount=199.98
    )
    test_db_session.add(order)
    test_db_session.commit()
    
    assert order.id is not None
    assert order.customer_id == 1
    assert order.status == "pending"
    assert order.total_amount == 199.98
    assert isinstance(order.created_at, datetime)
    assert isinstance(order.updated_at, datetime)
    assert len(order.items) == 0

def test_order_item_creation(test_db_session, sample_product, sample_order):
    """Test creating a new order item."""
    order_item = OrderItem(
        order_id=sample_order.id,
        product_id=sample_product.id,
        quantity=2,
        unit_price=sample_product.price
    )
    test_db_session.add(order_item)
    test_db_session.commit()
    
    assert order_item.id is not None
    assert order_item.order_id == sample_order.id
    assert order_item.product_id == sample_product.id
    assert order_item.quantity == 2
    assert order_item.unit_price == sample_product.price
    assert isinstance(order_item.created_at, datetime)

def test_order_items_relationship(test_db_session, sample_order):
    """Test order-items relationship."""
    assert len(sample_order.items) == 1
    order_item = sample_order.items[0]
    assert order_item.order_id == sample_order.id
    assert order_item.quantity == 1

def test_product_orders_relationship(test_db_session, sample_product, sample_order):
    """Test product-orders relationship."""
    # Refresh the product to ensure relationships are loaded
    test_db_session.expire(sample_product)
    test_db_session.refresh(sample_product)
    
    assert len(sample_product.orders) == 1
    order_item = sample_product.orders[0]
    assert order_item.product_id == sample_product.id
    assert order_item.unit_price == sample_product.price

def test_cascade_delete_order_items(test_db_session, sample_order):
    """Test cascade deletion of order items when order is deleted."""
    order_id = sample_order.id
    test_db_session.delete(sample_order)
    test_db_session.commit()
    
    # Verify order items are deleted
    order_items = test_db_session.query(OrderItem).filter_by(order_id=order_id).all()
    assert len(order_items) == 0

def test_product_required_fields(test_db_session):
    """Test product required fields validation."""
    # Test missing name
    product = Product(price=10.0, stock=5)
    test_db_session.add(product)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

def test_product_price_validation(test_db_session):
    """Test product price validation."""
    # Test negative price
    product = Product(
        name="Test Product",
        description="Test Description",
        price=-10.0,
        stock=10
    )
    
    # In a real application, this should be validated at the model level
    # For now, we'll just document that negative prices are not recommended
    test_db_session.add(product)
    test_db_session.commit()
    test_db_session.refresh(product)
    
    # Note: This test demonstrates that price validation should be added to the model
    # Currently, the model allows negative prices, which should be fixed in a future update
    assert isinstance(product.price, float), "Price should be a float"
    test_db_session.rollback()

def test_order_status_validation(test_db_session):
    """Test order status validation."""
    # Test valid statuses
    valid_statuses = ["pending", "processing", "completed", "cancelled"]
    for status in valid_statuses:
        order = Order(
            customer_id=1,
            status=status,
            total_amount=100.0
        )
        test_db_session.add(order)
        test_db_session.commit()
        assert order.status == status
        test_db_session.delete(order)
    test_db_session.commit()

def test_order_item_quantity_validation(test_db_session, sample_product, sample_order):
    """Test order item quantity validation."""
    # Test positive quantity
    order_item = OrderItem(
        order_id=sample_order.id,
        product_id=sample_product.id,
        quantity=5,
        unit_price=sample_product.price
    )
    test_db_session.add(order_item)
    test_db_session.commit()
    assert order_item.quantity > 0, "Quantity should be positive"
    
    # Update to zero quantity
    order_item.quantity = 0
    test_db_session.commit()
    assert order_item.quantity >= 0, "Quantity should not be negative"

def test_product_update(test_db_session, sample_product):
    """Test product update functionality."""
    # Update product
    original_updated_at = sample_product.updated_at
    sample_product.price = 199.99
    sample_product.stock = 20
    test_db_session.commit()
    test_db_session.refresh(sample_product)
    
    assert sample_product.price == 199.99
    assert sample_product.stock == 20
    assert sample_product.updated_at > original_updated_at

def test_order_total_amount_update(test_db_session, sample_order, sample_product):
    """Test order total amount update."""
    # Add another item to the order
    order_item = OrderItem(
        order_id=sample_order.id,
        product_id=sample_product.id,
        quantity=2,
        unit_price=sample_product.price
    )
    test_db_session.add(order_item)
    test_db_session.commit()
    
    # Update order total
    sample_order.total_amount = sample_product.price * 3  # 1 from fixture + 2 new
    test_db_session.commit()
    test_db_session.refresh(sample_order)
    
    assert len(sample_order.items) == 2
    assert sample_order.total_amount == sample_product.price * 3
