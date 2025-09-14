"""
Common utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize common utilities across services.
Instead of each service implementing its own logging setup, validation functions, and
helper utilities, they can use these shared implementations.

Key Demo Benefits:
- Consistent logging configuration across all services
- Reusable validation functions and patterns
- Standard utility functions that eliminate code duplication
- Single place to update common functionality

Focus: Essential utilities that demonstrate standardization patterns clearly.
"""

from .logging import setup_logging, get_logger, LogConfig
from .validation import validate_email, validate_uuid, sanitize_string

__all__ = [
    # Logging utilities
    "setup_logging",
    "get_logger", 
    "LogConfig",
    
    # Validation utilities
    "validate_email",
    "validate_uuid",
    "sanitize_string",
]
