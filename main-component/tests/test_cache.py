"""Unit tests for Redis cache functionality."""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.cache import RedisCache, generate_cache_key, cached, invalidate_cache
from redis.exceptions import RedisError

@pytest.fixture
def redis_cache():
    """Create a RedisCache instance for testing."""
    return RedisCache()

def test_generate_cache_key():
    """Test cache key generation."""
    # Test with only prefix
    assert generate_cache_key("test") == "test"
    
    # Test with args
    assert generate_cache_key("test", 1, "abc") == "test:1:abc"
    
    # Test with kwargs
    assert generate_cache_key("test", x=1, y="abc") == "test:x=1:y=abc"
    
    # Test with both args and kwargs
    assert generate_cache_key("test", 1, x="abc") == "test:1:x=abc"

def test_redis_cache_get(redis_cache):
    """Test cache get operation."""
    with patch.object(redis_cache._redis, 'get') as mock_get:
        # Test successful get
        mock_get.return_value = "test_value"
        assert redis_cache.get("test_key") == "test_value"
        
        # Test failed get
        mock_get.side_effect = RedisError()
        assert redis_cache.get("test_key") is None

def test_redis_cache_set(redis_cache):
    """Test cache set operation."""
    with patch.object(redis_cache._redis, 'set') as mock_set:
        # Test successful set
        mock_set.return_value = True
        assert redis_cache.set("test_key", "test_value", 60) is True
        mock_set.assert_called_with("test_key", "test_value", ex=60)
        
        # Test failed set
        mock_set.side_effect = RedisError()
        assert redis_cache.set("test_key", "test_value") is False

def test_redis_cache_delete(redis_cache):
    """Test cache delete operation."""
    with patch.object(redis_cache._redis, 'delete') as mock_delete:
        # Test successful delete
        mock_delete.return_value = 1
        assert redis_cache.delete("test_key") is True
        
        # Test failed delete
        mock_delete.side_effect = RedisError()
        assert redis_cache.delete("test_key") is False

def test_redis_cache_clear_pattern(redis_cache):
    """Test cache clear pattern operation."""
    with patch.object(redis_cache._redis, 'keys') as mock_keys, \
         patch.object(redis_cache._redis, 'delete') as mock_delete:
        # Test successful clear with matching keys
        mock_keys.return_value = ["key1", "key2"]
        mock_delete.return_value = 2
        assert redis_cache.clear_pattern("test:*") is True
        mock_delete.assert_called_with("key1", "key2")
        
        # Test successful clear with no matching keys
        mock_keys.return_value = []
        assert redis_cache.clear_pattern("test:*") is True
        
        # Test failed clear
        mock_keys.side_effect = RedisError()
        assert redis_cache.clear_pattern("test:*") is False

@pytest.mark.asyncio
async def test_cached_decorator():
    """Test cached decorator functionality."""
    # Mock async function to be cached
    @cached("test")
    async def test_func(x, y):
        return {"result": x + y}
    
    # Test cache miss and set
    with patch('app.cache.cache.get', return_value=None) as mock_get, \
         patch('app.cache.cache.set') as mock_set:
        result = await test_func(1, 2)
        assert result == {"result": 3}
        mock_get.assert_called_once()
        mock_set.assert_called_once()
    
    # Test cache hit
    cached_value = json.dumps({"result": 3})
    with patch('app.cache.cache.get', return_value=cached_value) as mock_get, \
         patch('app.cache.cache.set') as mock_set:
        result = await test_func(1, 2)
        assert result == {"result": 3}
        mock_get.assert_called_once()
        mock_set.assert_not_called()

def test_invalidate_cache():
    """Test cache invalidation."""
    # Test specific key invalidation
    with patch('app.cache.cache.delete') as mock_delete:
        mock_delete.return_value = True
        assert invalidate_cache("test", 1, x="abc") is True
        mock_delete.assert_called_with("test:1:x=abc")
    
    # Test pattern invalidation
    with patch('app.cache.cache.clear_pattern') as mock_clear:
        mock_clear.return_value = True
        assert invalidate_cache("test") is True
        mock_clear.assert_called_with("test:*")
