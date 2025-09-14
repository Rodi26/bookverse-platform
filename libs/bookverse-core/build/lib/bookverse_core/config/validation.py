"""
Configuration validation utilities.

Provides validation functions and custom validators for configuration.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import ValidationError


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_config(config_data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> None:
    """
    Validate configuration data.
    
    Args:
        config_data: Configuration dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ConfigValidationError: If validation fails
    """
    errors = []
    
    # Check required fields
    if required_fields:
        for field in required_fields:
            if field not in config_data or config_data[field] is None:
                errors.append(f"Missing required field: {field}")
    
    # Validate specific fields
    if "database_url" in config_data and config_data["database_url"]:
        if not validate_database_url(config_data["database_url"]):
            errors.append("Invalid database URL format")
    
    if "oidc_authority" in config_data and config_data["oidc_authority"]:
        if not validate_url(config_data["oidc_authority"]):
            errors.append("Invalid OIDC authority URL format")
    
    if "log_level" in config_data and config_data["log_level"]:
        if not validate_log_level(config_data["log_level"]):
            errors.append("Invalid log level")
    
    if "environment" in config_data and config_data["environment"]:
        if not validate_environment(config_data["environment"]):
            errors.append("Invalid environment")
    
    if errors:
        raise ConfigValidationError("; ".join(errors))


def validate_database_url(url: str) -> bool:
    """
    Validate database URL format.
    
    Args:
        url: Database URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        # Must have scheme and some path/host
        return bool(parsed.scheme and (parsed.netloc or parsed.path))
    except Exception:
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def validate_log_level(level: str) -> bool:
    """
    Validate logging level.
    
    Args:
        level: Log level to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    return level.upper() in valid_levels


def validate_environment(env: str) -> bool:
    """
    Validate environment name.
    
    Args:
        env: Environment name to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_environments = {"development", "staging", "production", "test"}
    return env.lower() in valid_environments


def validate_service_name(name: str) -> bool:
    """
    Validate service name format.
    
    Args:
        name: Service name to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Service name should be alphanumeric with hyphens/underscores
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$"
    return bool(re.match(pattern, name)) and len(name) >= 2


def validate_version(version: str) -> bool:
    """
    Validate semantic version format.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Basic semver pattern
    pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?(?:\+[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?$"
    return bool(re.match(pattern, version))


def validate_api_prefix(prefix: str) -> bool:
    """
    Validate API prefix format.
    
    Args:
        prefix: API prefix to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Should start with / and contain valid path characters
    pattern = r"^/[a-zA-Z0-9/_-]*$"
    return bool(re.match(pattern, prefix))


def sanitize_config_for_logging(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize configuration data for safe logging.
    
    Removes or masks sensitive information like passwords, tokens, etc.
    
    Args:
        config_data: Configuration dictionary
        
    Returns:
        Sanitized configuration dictionary
    """
    sensitive_keys = {
        "password", "passwd", "secret", "token", "key", "auth",
        "database_url", "db_url", "connection_string"
    }
    
    sanitized = {}
    
    for key, value in config_data.items():
        key_lower = key.lower()
        
        # Check if key contains sensitive information
        is_sensitive = any(sensitive_word in key_lower for sensitive_word in sensitive_keys)
        
        if is_sensitive:
            if isinstance(value, str) and len(value) > 0:
                # Show first and last character with asterisks in between
                if len(value) <= 2:
                    sanitized[key] = "*" * len(value)
                else:
                    sanitized[key] = f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"
            else:
                sanitized[key] = "***"
        else:
            sanitized[key] = value
    
    return sanitized
