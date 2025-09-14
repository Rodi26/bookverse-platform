"""
BookVerse Core Library

Core libraries and utilities for BookVerse services, providing:
- Authentication and authorization
- Configuration management
- FastAPI utilities and patterns
- Database utilities
- Common utilities and helpers
"""

__version__ = "0.1.0"
__author__ = "BookVerse Team"
__email__ = "team@bookverse.com"

# Import main components for easy access
from .auth import AuthUser
from .config import BaseConfig, ConfigLoader

__all__ = [
    "AuthUser",
    "BaseConfig", 
    "ConfigLoader",
    "__version__",
]
