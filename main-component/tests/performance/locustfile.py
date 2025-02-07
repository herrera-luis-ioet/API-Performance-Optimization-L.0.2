"""Performance test scenarios using Locust.

This module implements load testing scenarios for product and order endpoints
to verify performance, caching, and rate limiting.
"""
import json
import random
from typing import Dict, List
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Test data for creating products and orders
SAMPLE_PRODUCTS = [
    {"name": "Test Product 1", "description": "Description 1", "price": 10.99, "stock": 100},
    {"name": "Test Product 2", "description": "Description 2", "price": 20.99, "stock": 50},
    {"name": "Test Product 3", "description": "Description 3", "price": 15.99, "stock": 75},
]

class MetricsCollector:
    """Collect and report custom metrics."""
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_hits = 0
    
    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

class APILoadTest(HttpUser):
    """Load test scenarios for the API endpoints."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    metrics = MetricsCollector()
    
    def on_start(self):
        """Setup test data before starting the load test."""
        # Create test products if needed
        for product in SAMPLE_PRODUCTS:
            response = self.client.post("/products/", json=product)
            if response.status_code == 200:
                product["id"] = response.json()["id"]
    
    @task(3)
    def browse_products(self):
        """Browse product catalog with pagination."""
        params = {
            "skip": random.randint(0, 50),
            "limit": random.randint(5, 20)
        }
        with self.client.get("/products/", params=params, catch_response=True) as response:
            if response.status_code == 200:
                if "X-Cache-Hit" in response.headers:
                    self.metrics.cache_hits += 1
                else:
                    self.metrics.cache_misses += 1
            elif response.status_code == 429:
                self.metrics.rate_limit_hits += 1
                response.failure("Rate limit exceeded")
    
    @task(2)
    def view_product_details(self):
        """View individual product details."""
        # Randomly select a product ID from 1-10 range
        product_id = random.randint(1, 10)
        with self.client.get(f"/products/{product_id}", catch_response=True) as response:
            if response.status_code == 200:
                if "X-Cache-Hit" in response.headers:
                    self.metrics.cache_hits += 1
                else:
                    self.metrics.cache_misses += 1
            elif response.status_code == 429:
                self.metrics.rate_limit_hits += 1
                response.failure("Rate limit exceeded")
            elif response.status_code == 404:
                response.failure("Product not found")
    
    @task(1)
    def create_order(self):
        """Create a new order."""
        # Create order with 1-3 random products
        items = []
        for _ in range(random.randint(1, 3)):
            items.append({
                "product_id": random.randint(1, len(SAMPLE_PRODUCTS)),
                "quantity": random.randint(1, 5)
            })
        
        order_data = {
            "customer_id": random.randint(1, 100),
            "status": "pending",
            "items": items
        }
        
        with self.client.post("/orders/", json=order_data, catch_response=True) as response:
            if response.status_code == 200:
                order_id = response.json()["id"]
                # Store order ID for future reference
                if not hasattr(self, "created_orders"):
                    self.created_orders = []
                self.created_orders.append(order_id)
            elif response.status_code == 429:
                self.metrics.rate_limit_hits += 1
                response.failure("Rate limit exceeded")
    
    @task(1)
    def check_order_status(self):
        """Check status of previously created orders."""
        if hasattr(self, "created_orders") and self.created_orders:
            order_id = random.choice(self.created_orders)
            with self.client.get(f"/orders/{order_id}", catch_response=True) as response:
                if response.status_code == 200:
                    if "X-Cache-Hit" in response.headers:
                        self.metrics.cache_hits += 1
                    else:
                        self.metrics.cache_misses += 1
                elif response.status_code == 429:
                    self.metrics.rate_limit_hits += 1
                    response.failure("Rate limit exceeded")
    
    @task(1)
    def list_orders(self):
        """List orders with pagination."""
        params = {
            "skip": random.randint(0, 20),
            "limit": random.randint(5, 15),
            "customer_id": random.randint(1, 100)
        }
        with self.client.get("/orders/", params=params, catch_response=True) as response:
            if response.status_code == 200:
                if "X-Cache-Hit" in response.headers:
                    self.metrics.cache_hits += 1
                else:
                    self.metrics.cache_misses += 1
            elif response.status_code == 429:
                self.metrics.rate_limit_hits += 1
                response.failure("Rate limit exceeded")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report custom metrics when the test stops."""
    if not isinstance(environment.runner, MasterRunner):
        # Calculate and report metrics
        metrics = environment.user_classes[0].metrics
        environment.events.request.fire(
            request_type="CUSTOM",
            name="cache_hit_ratio",
            response_time=0,
            response_length=0,
            exception=None,
            context={
                "cache_hit_ratio": metrics.cache_hit_ratio,
                "cache_hits": metrics.cache_hits,
                "cache_misses": metrics.cache_misses,
                "rate_limit_hits": metrics.rate_limit_hits
            }
        )