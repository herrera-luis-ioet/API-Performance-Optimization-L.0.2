"""Unit tests for configuration management."""
import os
import pytest
from pydantic import ValidationError

from app.config import Settings

def test_default_settings():
    """Test default configuration values."""
    settings = Settings()
    
    # Database settings
    assert str(settings.DATABASE_URL).startswith("mysql://")
    assert settings.DATABASE_POOL_SIZE == 20
    assert settings.DATABASE_POOL_OVERFLOW == 10
    
    # Redis settings
    assert str(settings.REDIS_URL).startswith("redis://")
    assert settings.REDIS_TTL == 3600
    
    # API settings
    assert settings.API_TITLE == "API Performance Optimization Service"
    assert settings.API_VERSION == "0.2"
    assert settings.RATE_LIMIT_REQUESTS == 100
    assert settings.RATE_LIMIT_WINDOW == 60
    assert settings.RATE_LIMIT_BYPASS_TOKEN is None
    
    # Environment settings
    assert settings.DEBUG is False

def test_environment_override():
    """Test configuration override using environment variables."""
    test_values = {
        "DATABASE_URL": "mysql://test:test@localhost/testdb",
        "REDIS_URL": "redis://localhost:6380/1",
        "DATABASE_POOL_SIZE": 30,
        "REDIS_TTL": 1800,
        "API_TITLE": "Test API",
        "DEBUG": "true",
        "RATE_LIMIT_REQUESTS": 50,
        "RATE_LIMIT_BYPASS_TOKEN": "test_token"
    }
    
    # Set environment variables
    for key, value in test_values.items():
        os.environ[key] = str(value)
    
    # Create settings with environment variables
    settings = Settings()
    
    # Verify overridden values
    assert str(settings.DATABASE_URL) == test_values["DATABASE_URL"]
    assert str(settings.REDIS_URL) == test_values["REDIS_URL"]
    assert settings.DATABASE_POOL_SIZE == 30
    assert settings.REDIS_TTL == 1800
    assert settings.API_TITLE == "Test API"
    assert settings.DEBUG is True
    assert settings.RATE_LIMIT_REQUESTS == 50
    assert settings.RATE_LIMIT_BYPASS_TOKEN == "test_token"
    
    # Clean up environment
    for key in test_values:
        del os.environ[key]

def test_url_validation():
    """Test URL validation for database and Redis connections."""
    # Test invalid database URL
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="invalid-url")
    
    # Test invalid Redis URL
    with pytest.raises(ValidationError):
        Settings(REDIS_URL="invalid-url")
    
    # Test missing URLs
    with pytest.raises(ValueError):
        Settings(DATABASE_URL="")
    
    with pytest.raises(ValueError):
        Settings(REDIS_URL="")

def test_pool_size_validation():
    """Test validation of database pool size settings."""
    # Test negative pool size
    with pytest.raises(ValueError):
        Settings(DATABASE_POOL_SIZE=-1)
    
    # Test negative pool overflow
    with pytest.raises(ValueError):
        Settings(DATABASE_POOL_OVERFLOW=-1)

def test_rate_limit_validation():
    """Test validation of rate limiting settings."""
    # Test negative requests
    with pytest.raises(ValueError):
        Settings(RATE_LIMIT_REQUESTS=-1)
    
    # Test negative window
    with pytest.raises(ValueError):
        Settings(RATE_LIMIT_WINDOW=-1)
