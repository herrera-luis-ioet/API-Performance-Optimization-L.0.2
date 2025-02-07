"""Configuration management for the API service using Pydantic BaseSettings.

This module provides configuration management for database, Redis, and API settings
with environment variable support.
"""
from typing import Optional, Union
from pydantic import BaseSettings, Field, RedisDsn, validator, AnyUrl

class Settings(BaseSettings):
    """Main configuration settings for the application.
    
    Attributes:
        # Database Settings
        DATABASE_URL: PostgreSQL connection string
        DATABASE_POOL_SIZE: Maximum number of database connections in the pool
        DATABASE_POOL_OVERFLOW: Maximum number of overflow connections
        
        # Redis Settings
        REDIS_URL: Redis connection string
        REDIS_TTL: Default TTL for cached items in seconds
        
        # API Settings
        API_TITLE: Name of the API service
        API_VERSION: API version string
        RATE_LIMIT_REQUESTS: Number of requests allowed per window
        RATE_LIMIT_WINDOW: Time window for rate limiting in seconds
    """
    
    # Database Settings
    DATABASE_URL: AnyUrl = Field(
        default="mysql://user:password@localhost:3306/db",
        description="MySQL connection string"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=20,
        description="Maximum number of database connections in the pool"
    )
    DATABASE_POOL_OVERFLOW: int = Field(
        default=10,
        description="Maximum number of overflow connections allowed"
    )
    
    # Redis Settings
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_TTL: int = Field(
        default=3600,
        description="Default TTL for cached items in seconds"
    )
    
    # API Settings
    API_TITLE: str = Field(
        default="API Performance Optimization Service",
        description="Name of the API service"
    )
    API_VERSION: str = Field(
        default="0.2",
        description="API version string"
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        description="Number of requests allowed per window"
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=60,
        description="Time window for rate limiting in seconds"
    )
    RATE_LIMIT_BYPASS_TOKEN: Optional[str] = Field(
        default=None,
        description="Token to bypass rate limiting for authorized clients"
    )
    
    # Environment-specific settings
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    @validator("DATABASE_URL", "REDIS_URL", pre=True)
    def validate_urls(cls, v: Optional[str], field: Field) -> str:
        """Validate and format database and redis URLs.
        
        Args:
            v: The URL value to validate
            field: The field being validated
            
        Returns:
            str: The validated URL
            
        Raises:
            ValueError: If the URL is invalid
        """
        if not v:
            raise ValueError(f"{field.name} must be provided")
        return v
    
    @validator("DATABASE_POOL_SIZE", "DATABASE_POOL_OVERFLOW", "REDIS_TTL", 
              "RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW", pre=True)
    def validate_positive_numbers(cls, v: Union[int, str], field: Field) -> int:
        """Validate numeric fields to ensure they are positive.
        
        Args:
            v: The value to validate (can be int or str)
            field: The field being validated
            
        Returns:
            int: The validated value
            
        Raises:
            ValueError: If the value is negative or invalid
        """
        try:
            value = int(v)
            if value < 0:
                raise ValueError(f"{field.name} must be a positive number")
            return value
        except (TypeError, ValueError):
            raise ValueError(f"{field.name} must be a valid positive number")
    
    class Config:
        """Pydantic model configuration.
        
        This inner class configures the Settings model to:
        1. Load environment variables
        2. Use case-sensitive field names
        3. Allow extra fields in case of future additions
        """
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a global settings instance
settings = Settings()
