"""Integration tests for the API endpoints.

This module contains comprehensive integration tests for the API endpoints,
including tests for CRUD operations, validation, caching, and concurrent operations.
"""
import pytest
from fastapi import status

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}

def test_get_product_list(test_client, sample_product):
    """Test getting the list of products."""
    response = test_client.get("/api/v1/products/")
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Test Product"
    assert products[0]["price"] == 99.99

def test_get_product_detail(test_client, sample_product):
    """Test getting a single product's details."""
    response = test_client.get(f"/api/v1/products/{sample_product.id}")
    assert response.status_code == status.HTTP_200_OK
    product = response.json()
    assert product["name"] == "Test Product"
    assert product["description"] == "A test product"

def test_create_product(test_client):
    """Test creating a new product."""
    product_data = {
        "name": "New Product",
        "description": "A new test product",
        "price": 49.99,
        "stock": 5
    }
    response = test_client.post("/api/v1/products/", json=product_data)
    assert response.status_code == status.HTTP_201_CREATED
    created_product = response.json()
    assert created_product["name"] == product_data["name"]
    assert created_product["price"] == product_data["price"]

def test_update_product(test_client, sample_product):
    """Test updating a product's details."""
    update_data = {
        "name": "Updated Product",
        "price": 149.99,
        "stock": 15
    }
    response = test_client.patch(
        f"/api/v1/products/{sample_product.id}",
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    updated_product = response.json()
    assert updated_product["name"] == update_data["name"]
    assert updated_product["price"] == update_data["price"]

def test_delete_product(test_client, sample_product):
    """Test deleting a product."""
    response = test_client.delete(f"/api/v1/products/{sample_product.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify product is deleted
    get_response = test_client.get(f"/api/v1/products/{sample_product.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

def test_create_order_success(test_client, sample_product):
    """Test creating a new order with valid data."""
    order_data = {
        "customer_id": 1,
        "status": "pending",
        "items": [
            {
                "product_id": sample_product.id,
                "quantity": 2
            }
        ]
    }
    response = test_client.post("/api/v1/orders/", json=order_data)
    assert response.status_code == status.HTTP_201_CREATED
    created_order = response.json()
    assert created_order["customer_id"] == order_data["customer_id"]
    assert created_order["status"] == "pending"
    assert len(created_order["items"]) == 1
    assert created_order["items"][0]["quantity"] == 2
    assert created_order["total_amount"] == sample_product.price * 2

def test_create_order_invalid_product(test_client):
    """Test creating an order with non-existent product."""
    order_data = {
        "customer_id": 1,
        "status": "pending",
        "items": [
            {
                "product_id": 999,  # Non-existent product
                "quantity": 1
            }
        ]
    }
    response = test_client.post("/api/v1/orders/", json=order_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Product 999 not found" in response.json()["detail"]

def test_create_order_insufficient_stock(test_client, sample_product):
    """Test creating an order with quantity exceeding stock."""
    order_data = {
        "customer_id": 1,
        "status": "pending",
        "items": [
            {
                "product_id": sample_product.id,
                "quantity": 100  # More than available stock
            }
        ]
    }
    response = test_client.post("/api/v1/orders/", json=order_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient stock" in response.json()["detail"]

def test_create_order_duplicate_products(test_client, sample_product):
    """Test creating an order with duplicate products."""
    order_data = {
        "customer_id": 1,
        "status": "pending",
        "items": [
            {"product_id": sample_product.id, "quantity": 1},
            {"product_id": sample_product.id, "quantity": 2}
        ]
    }
    response = test_client.post("/api/v1/orders/", json=order_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Duplicate product" in response.json()["detail"][0]["msg"]

def test_get_order_detail_success(test_client, sample_order):
    """Test getting order details."""
    response = test_client.get(f"/api/v1/orders/{sample_order.id}")
    assert response.status_code == status.HTTP_200_OK
    order = response.json()
    assert order["customer_id"] == 1
    assert len(order["items"]) == 1
    assert order["total_amount"] == 99.99

def test_get_order_detail_not_found(test_client):
    """Test getting non-existent order."""
    response = test_client.get("/api/v1/orders/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Order not found" in response.json()["detail"]

def test_list_orders_pagination(test_client, test_db_session, sample_product):
    """Test order listing with pagination."""
    # Create multiple orders
    for i in range(15):
        order_data = {
            "customer_id": i + 1,
            "status": "pending",
            "items": [{"product_id": sample_product.id, "quantity": 1}]
        }
        test_client.post("/api/v1/orders/", json=order_data)
    
    # Test default pagination (limit=10)
    response = test_client.get("/api/v1/orders/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 16  # Including sample_order
    
    # Test custom pagination
    response = test_client.get("/api/v1/orders/?skip=10&limit=5")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] == 16

def test_list_orders_filtering(test_client, test_db_session, sample_product):
    """Test order listing with filters."""
    # Create orders with different statuses
    statuses = ["pending", "confirmed", "shipped"]
    for status in statuses:
        order_data = {
            "customer_id": 1,
            "status": status,
            "items": [{"product_id": sample_product.id, "quantity": 1}]
        }
        test_client.post("/api/v1/orders/", json=order_data)
    
    # Test status filter
    response = test_client.get("/api/v1/orders/?status=confirmed")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "confirmed"
    
    # Test customer filter
    response = test_client.get("/api/v1/orders/?customer_id=1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(item["customer_id"] == 1 for item in data["items"])

def test_update_order_status(test_client, sample_order):
    """Test updating order status."""
    update_data = {"status": "confirmed"}
    response = test_client.put(f"/api/v1/orders/{sample_order.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    updated_order = response.json()
    assert updated_order["status"] == "confirmed"

def test_update_order_invalid_status(test_client, sample_order):
    """Test updating order with invalid status."""
    update_data = {"status": "invalid_status"}
    response = test_client.put(f"/api/v1/orders/{sample_order.id}", json=update_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_delete_order(test_client, sample_order, test_db_session):
    """Test deleting an order and verifying stock restoration."""
    # Get initial product stock
    product = sample_order.items[0].product
    initial_stock = product.stock
    
    # Delete order
    response = test_client.delete(f"/api/v1/orders/{sample_order.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify order is deleted
    get_response = test_client.get(f"/api/v1/orders/{sample_order.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    # Verify stock is restored
    test_db_session.refresh(product)
    assert product.stock == initial_stock + sample_order.items[0].quantity

def test_order_caching(test_client, sample_order, mock_redis):
    """Test order caching behavior."""
    # First request should cache the result
    response1 = test_client.get(f"/api/v1/orders/{sample_order.id}")
    assert response1.status_code == status.HTTP_200_OK
    
    # Verify data was cached
    cache_key = f"orders:detail:{sample_order.id}"
    assert mock_redis.exists(cache_key)
    
    # Second request should use cached data
    response2 = test_client.get(f"/api/v1/orders/{sample_order.id}")
    assert response2.status_code == status.HTTP_200_OK
    assert response2.json() == response1.json()
    
    # Update order should invalidate cache
    update_data = {"status": "confirmed"}
    test_client.put(f"/api/v1/orders/{sample_order.id}", json=update_data)
    assert not mock_redis.exists(cache_key)

def test_concurrent_stock_updates(test_client, sample_product):
    """Test handling of concurrent order creation."""
    order_data = {
        "customer_id": 1,
        "status": "pending",
        "items": [
            {
                "product_id": sample_product.id,
                "quantity": sample_product.stock // 2  # Half of available stock
            }
        ]
    }
    
    # Create two orders concurrently
    response1 = test_client.post("/api/v1/orders/", json=order_data)
    response2 = test_client.post("/api/v1/orders/", json=order_data)
    
    # Both orders should succeed as total quantity <= available stock
    assert response1.status_code == status.HTTP_201_CREATED
    assert response2.status_code == status.HTTP_201_CREATED
    
    # Third order should fail due to insufficient stock
    response3 = test_client.post("/api/v1/orders/", json=order_data)
    assert response3.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient stock" in response3.json()["detail"]

def test_product_caching(test_client, sample_product, mock_redis):
    """Test that product details are cached."""
    # First request should cache the result
    response1 = test_client.get(f"/api/v1/products/{sample_product.id}")
    assert response1.status_code == status.HTTP_200_OK
    
    # Verify data was cached in Redis
    cache_key = f"product:{sample_product.id}"
    assert mock_redis.exists(cache_key)
    
    # Second request should use cached data
    response2 = test_client.get(f"/api/v1/products/{sample_product.id}")
    assert response2.status_code == status.HTTP_200_OK
    assert response2.json() == response1.json()

def test_rate_limiting(test_client):
    """Test that rate limiting is enforced."""
    # Make multiple requests in quick succession
    responses = []
    for _ in range(10):  # Assuming rate limit is less than 10 requests per second
        response = test_client.get("/api/v1/products/")
        responses.append(response)
    
    # At least one response should be rate limited
    assert any(r.status_code == status.HTTP_429_TOO_MANY_REQUESTS for r in responses)
