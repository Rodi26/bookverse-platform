"""
Configuration loaders for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to unify the 4 different configuration approaches
currently used across services:
- Inventory: Hardcoded constants  
- Recommendations: YAML + caching + env overrides
- Checkout: Dataclass + env mapping
- Platform: Mixed YAML + env

Key Demo Benefits:
- Single, flexible configuration system for all services
- Support for multiple sources (YAML, env vars, defaults) with clear precedence
- Type-safe configuration with Pydantic validation
- Eliminates configuration pattern inconsistencies

Focus: Clear, practical configuration loading that works for all service types.
"""

import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

try:
    import yaml
except ImportError:
    yaml = None

from .base import BaseConfig

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseConfig)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Unified configuration loader supporting multiple sources.
    
    Supports loading from YAML files, environment variables, and defaults
    with proper precedence and validation.
    """
    
    def __init__(self, config_class: Type[T]):
        """
        Initialize configuration loader.
        
        Args:
            config_class: Pydantic configuration class to load into
        """
        self.config_class = config_class
    
    def load_from(
        self,
        yaml_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "",
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> T:
        """
        Load configuration from multiple sources with precedence.
        
        Precedence order (highest to lowest):
        1. Keyword arguments
        2. Environment variables
        3. YAML file
        4. Defaults
        
        Args:
            yaml_file: Path to YAML configuration file
            env_prefix: Prefix for environment variables
            defaults: Default configuration values
            **kwargs: Direct configuration overrides
            
        Returns:
            Configuration instance
            
        Raises:
            ConfigValidationError: If configuration validation fails
        """
        config_data = {}
        
        # 1. Start with defaults
        if defaults:
            config_data.update(defaults)
            logger.debug(f"Loaded {len(defaults)} default values")
        
        # 2. Load from YAML file
        if yaml_file:
            yaml_data = self._load_yaml_file(yaml_file)
            if yaml_data:
                config_data = self._deep_merge(config_data, yaml_data)
                logger.debug(f"Loaded configuration from {yaml_file}")
        
        # 3. Load from environment variables
        env_data = self._load_env_vars(env_prefix)
        if env_data:
            config_data = self._deep_merge(config_data, env_data)
            logger.debug(f"Loaded {len(env_data)} environment variables")
        
        # 4. Apply direct overrides
        if kwargs:
            config_data = self._deep_merge(config_data, kwargs)
            logger.debug(f"Applied {len(kwargs)} direct overrides")
        
        try:
            return self.config_class(**config_data)
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}") from e
    
    def _load_yaml_file(self, yaml_file: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if yaml is None:
            logger.warning("PyYAML not available, skipping YAML file loading")
            return {}
        
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            logger.warning(f"YAML file not found: {yaml_path}")
            return {}
        
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            if not isinstance(data, dict):
                logger.warning(f"YAML file {yaml_path} does not contain a dictionary")
                return {}
            
            return data
        except Exception as e:
            logger.error(f"Failed to load YAML file {yaml_path}: {e}")
            return {}
    
    def _load_env_vars(self, prefix: str) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_data = {}
        
        for key, value in os.environ.items():
            config_key = None
            
            if prefix and key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
            elif not prefix:
                # Use all environment variables if no prefix
                config_key = key.lower()
            
            if config_key:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value)
                env_data[config_key] = converted_value
        
        return env_data
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Handle boolean values
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        elif value.lower() in ("false", "no", "0", "off"):
            return False
        
        # Handle numeric values
        try:
            # Try integer first
            if "." not in value:
                return int(value)
            else:
                return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, similar to recommendations service pattern.
        
        DEMO PURPOSE: This implements the same deep merging logic as the recommendations
        service, allowing nested configuration sections to be properly merged instead
        of completely replaced.
        
        Example:
            base = {"features": {"cache": True, "ttl": 60}}
            update = {"features": {"cache": False}}
            result = {"features": {"cache": False, "ttl": 60}}  # ttl preserved
        
        Args:
            base: Base dictionary
            update: Dictionary to merge into base
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in update.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Replace or add the value
                result[key] = value
        
        return result
    
    def _load_env_vars_with_nesting(self, prefix: str) -> Dict[str, Any]:
        """
        Load environment variables with support for nested configuration.
        
        DEMO PURPOSE: Enhanced environment variable loading that supports
        nested configuration like the recommendations service.
        
        Supports patterns like:
        - SERVICE_FEATURES__CACHE=true -> {"features": {"cache": true}}
        - SERVICE_WEIGHTS__GENRE=1.5 -> {"weights": {"genre": 1.5}}
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            Nested configuration dictionary
        """
        env_data = {}
        
        for key, value in os.environ.items():
            if not prefix or not key.startswith(prefix):
                continue
            
            # Remove prefix
            config_key = key[len(prefix):] if prefix else key
            
            # Handle nested keys (double underscore separator)
            if "__" in config_key:
                parts = config_key.lower().split("__")
                converted_value = self._convert_env_value(value)
                
                # Build nested structure
                current = env_data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = converted_value
            else:
                # Simple key
                config_key = config_key.lower()
                env_data[config_key] = self._convert_env_value(value)
        
        return env_data


@lru_cache(maxsize=32)
def load_config_with_defaults(
    config_class: Type[T],
    yaml_file: Optional[str] = None,
    env_prefix: str = "",
    defaults: Optional[Dict[str, Any]] = None
) -> T:
    """
    Cached configuration loader with defaults support.
    
    DEMO PURPOSE: Provides the same caching pattern as the recommendations service
    for efficient configuration loading with proper cache invalidation.
    
    Args:
        config_class: Configuration class
        yaml_file: YAML configuration file path
        env_prefix: Environment variable prefix
        defaults: Default configuration values
        
    Returns:
        Cached configuration instance
    """
    loader = ConfigLoader(config_class)
    return loader.load_from(
        yaml_file=yaml_file,
        env_prefix=env_prefix,
        defaults=defaults
    )


# Note: Enhanced configuration loading inspired by recommendations service patterns
# Provides deep merging, nested environment variables, and caching for production use.
