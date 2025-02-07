# Performance Testing with Locust

This directory contains performance test scenarios for the API endpoints using Locust.

## Test Scenarios

The test suite includes the following scenarios:

1. Product Catalog Browsing
   - List products with pagination
   - View product details
   - Verifies cache hit ratio

2. Order Management
   - Create new orders
   - Check order status
   - List orders with pagination

3. Performance Metrics
   - Response time measurements
   - Cache hit ratio tracking
   - Rate limiting validation

## Prerequisites

Install Locust:
```bash
pip install locust
```

## Running the Tests

1. Start the API server:
```bash
cd ../../
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Run Locust tests:
```bash
cd tests/performance
locust -f locustfile.py --host http://localhost:8000
```

3. Open Locust web interface:
   - Visit http://localhost:8089
   - Set number of users and spawn rate
   - Start the test

## Test Configuration

The test scenarios are configured with:
- Wait time between requests: 1-3 seconds
- Realistic user behavior simulation
- Automatic test data creation
- Custom metrics collection

## Metrics Collected

- Response times for all endpoints
- Cache hit ratio
- Rate limit hits
- Error rates

## Test Data

The tests automatically create sample products during startup:
- Test products with varying prices and stock levels
- Random order creation with 1-3 items
- Simulated customer IDs