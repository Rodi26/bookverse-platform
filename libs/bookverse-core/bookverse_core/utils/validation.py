"""
Validation utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize validation functions
across services. Instead of each service implementing its own validation logic,
they can use these shared, tested validation functions.

Key Demo Benefits:
- Consistent validation behavior across all services
- Reusable validation functions with clear error messages
- Single place to update validation logic
- Eliminates duplicate validation code

Focus: Common validation patterns that services need, with demo-friendly error messages.
"""

import re
import uuid
from typing import Optional


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    DEMO PURPOSE: Provides a simple email validation that can be used
    across all services, with clear demo-appropriate validation rules.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Simple email regex for demo purposes
    # Note: This is simplified for demo clarity, not production-grade
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(email_pattern, email.strip()))


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    DEMO PURPOSE: Provides consistent UUID validation across services.
    Many services use UUIDs for IDs, so this eliminates duplicate validation code.
    
    Args:
        uuid_string: UUID string to validate
        
    Returns:
        True if UUID is valid, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        # Try to create UUID object - will raise ValueError if invalid
        uuid.UUID(uuid_string.strip())
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_string(
    input_string: str,
    max_length: int = 1000,
    allow_html: bool = False
) -> str:
    """
    Sanitize string input for safe processing.
    
    DEMO PURPOSE: Provides basic string sanitization that can be used
    across services to prevent common issues with user input.
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If string is too long (with demo-friendly message)
    """
    if not input_string:
        return ""
    
    if not isinstance(input_string, str):
        input_string = str(input_string)
    
    # Strip whitespace
    sanitized = input_string.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise ValueError(
            f"String too long: {len(sanitized)} characters. "
            f"Maximum allowed: {max_length}. "
            f"Demo tip: Consider truncating or splitting long inputs."
        )
    
    # Remove HTML tags if not allowed
    if not allow_html:
        # Simple HTML tag removal for demo purposes
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
    
    # Remove potentially dangerous characters for demo safety
    # Note: This is basic sanitization for demo purposes
    dangerous_chars = ['<script', '</script>', 'javascript:', 'onclick=']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized


def validate_service_name(name: str) -> bool:
    """
    Validate service name format.
    
    DEMO PURPOSE: Ensures service names follow consistent patterns
    across the BookVerse demo environment.
    
    Args:
        name: Service name to validate
        
    Returns:
        True if service name is valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    # Service names should be lowercase, alphanumeric with hyphens
    # Must start and end with alphanumeric character
    pattern = r'^[a-z0-9][a-z0-9-]*[a-z0-9]$'
    
    name = name.strip().lower()
    
    # Check length (reasonable for demo)
    if len(name) < 2 or len(name) > 50:
        return False
    
    return bool(re.match(pattern, name))


def validate_version_string(version: str) -> bool:
    """
    Validate semantic version string.
    
    DEMO PURPOSE: Ensures version strings follow semantic versioning
    patterns used across BookVerse services.
    
    Args:
        version: Version string to validate (e.g., "1.0.0", "2.1.3-beta")
        
    Returns:
        True if version is valid, False otherwise
    """
    if not version or not isinstance(version, str):
        return False
    
    # Basic semantic version pattern for demo
    # Supports: X.Y.Z and X.Y.Z-suffix
    pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9-]+)?$'
    
    return bool(re.match(pattern, version.strip()))


def validate_port_number(port: int) -> bool:
    """
    Validate port number.
    
    DEMO PURPOSE: Validates port numbers used in service configurations.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if port is valid, False otherwise
    """
    if not isinstance(port, int):
        return False
    
    # Valid port range (excluding system ports for demo safety)
    return 1024 <= port <= 65535


def validate_url(url: str, require_https: bool = False) -> bool:
    """
    Validate URL format.
    
    DEMO PURPOSE: Validates URLs used in service configurations
    (like OIDC authority URLs, service endpoints, etc.).
    
    Args:
        url: URL to validate
        require_https: Whether to require HTTPS scheme
        
    Returns:
        True if URL is valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL pattern for demo purposes
    if require_https:
        pattern = r'^https://[a-zA-Z0-9.-]+(?:\:[0-9]+)?(?:/.*)?$'
    else:
        pattern = r'^https?://[a-zA-Z0-9.-]+(?:\:[0-9]+)?(?:/.*)?$'
    
    return bool(re.match(pattern, url.strip()))


def create_validation_error_message(field: str, value: str, reason: str) -> str:
    """
    Create a standardized validation error message.
    
    DEMO PURPOSE: Provides consistent, helpful error messages across all services
    for better demo experience and debugging.
    
    Args:
        field: Name of the field that failed validation
        value: Value that failed validation (will be truncated if long)
        reason: Reason for validation failure
        
    Returns:
        Formatted error message
    """
    # Truncate long values for readability
    if len(str(value)) > 50:
        display_value = str(value)[:47] + "..."
    else:
        display_value = str(value)
    
    return (
        f"Validation failed for '{field}': {reason}. "
        f"Provided value: '{display_value}'. "
        f"Demo tip: Check the field requirements and try again."
    )
