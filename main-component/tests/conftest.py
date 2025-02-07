"""Test fixtures for the API service tests."""
import pytest
import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Product, Order, OrderItem
from app.config import Settings
from app.cache import get_redis
from main import app

@pytest.fixture
def test_settings():
    """Create test settings with in-memory database and mock Redis."""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/1",  # Use different DB for testing
        DATABASE_POOL_SIZE=1,
        DATABASE_POOL_OVERFLOW=0,
        DEBUG=True
    )

@pytest.fixture
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def sample_product(test_db_session):
    """Create a sample product for testing."""
    product = Product(
        name="Test Product",
        description="A test product",
        price=99.99,
        stock=10
    )
    test_db_session.add(product)
    test_db_session.commit()
    test_db_session.refresh(product)
    return product

@pytest.fixture
def sample_order(test_db_session, sample_product):
    """Create a sample order with one item for testing."""
    order = Order(
        customer_id=1,
        status="pending",
        total_amount=99.99
    )
    test_db_session.add(order)
    test_db_session.flush()
    
    order_item = OrderItem(
        order_id=order.id,
        product_id=sample_product.id,
        quantity=1,
        unit_price=sample_product.price
    )
    test_db_session.add(order_item)
    test_db_session.commit()
    
    # Refresh both order and product to ensure relationships are loaded
    test_db_session.refresh(order)
    test_db_session.refresh(sample_product)
    test_db_session.expire_all()  # Clear all object caches
    test_db_session.refresh(order)  # Reload objects
    test_db_session.refresh(sample_product)
    return order

@pytest.fixture
def mock_redis():
    """Create a mock Redis instance for testing."""
    fake_redis = fakeredis.FakeStrictRedis()
    return fake_redis

@pytest.fixture
def test_app(test_db_session, mock_redis):
    """Create a test FastAPI application with dependencies overridden."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    return app

@pytest.fixture
def test_client(test_app):
    """Create a TestClient instance for making test requests."""
    with TestClient(test_app) as client:
        yield client
