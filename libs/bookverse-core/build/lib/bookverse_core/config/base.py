"""
Base configuration classes for BookVerse services.

Provides Pydantic-based configuration with type safety and validation.
"""

import os
from typing import Any, Dict, Optional, Type, TypeVar
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T', bound='BaseConfig')


class BaseConfig(BaseModel):
    """
    Base configuration class for BookVerse services.
    
    Provides common configuration fields and utilities that all services need.
    """
    
    model_config = ConfigDict(
        # Allow environment variables to override config
        env_file=".env",
        env_file_encoding="utf-8",
        # Case sensitive environment variables
        case_sensitive=False,
        # Validate assignment
        validate_assignment=True,
        # Extra fields are forbidden by default
        extra="forbid"
    )
    
    # Common service metadata
    service_name: str = Field(
        default="BookVerse Service",
        description="Name of the service"
    )
    
    service_version: str = Field(
        default="1.0.0",
        description="Version of the service"
    )
    
    service_description: str = Field(
        default="A BookVerse microservice",
        description="Description of the service"
    )
    
    # API configuration
    api_version: str = Field(
        default="v1",
        description="API version"
    )
    
    api_prefix: str = Field(
        default="/api/v1",
        description="API path prefix"
    )
    
    # Environment and logging
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Database configuration (optional)
    database_url: Optional[str] = Field(
        default=None,
        description="Database connection URL"
    )
    
    # Authentication configuration
    auth_enabled: bool = Field(
        default=True,
        description="Enable authentication"
    )
    
    development_mode: bool = Field(
        default=False,
        description="Enable development mode"
    )
    
    oidc_authority: str = Field(
        default="https://dev-auth.bookverse.com",
        description="OIDC authority URL"
    )
    
    oidc_audience: str = Field(
        default="bookverse:api",
        description="OIDC audience"
    )
    
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT algorithm"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug or self.is_development
    
    def get_api_prefix(self) -> str:
        """Get the full API prefix."""
        if self.api_prefix.startswith("/"):
            return self.api_prefix
        return f"/api/{self.api_version}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create configuration from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_env(cls: Type[T], prefix: str = "") -> T:
        """
        Create configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix (e.g., "INVENTORY_")
            
        Returns:
            Configuration instance
        """
        env_vars = {}
        
        # Get all environment variables with the prefix
        for key, value in os.environ.items():
            if prefix and key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                env_vars[config_key] = value
            elif not prefix:
                env_vars[key.lower()] = value
        
        return cls(**env_vars)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(service={self.service_name}, version={self.service_version})"
    
    def __repr__(self) -> str:
        return self.__str__()
