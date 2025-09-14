"""
Logging utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize logging across services.
Instead of each service setting up its own logging configuration (like the basic
logging.basicConfig() calls in main.py files), all services can use this
shared, consistent logging setup.

Key Demo Benefits:
- Consistent log format across all services
- Standardized log levels and configuration
- Easy to update logging behavior for all services at once
- Proper structured logging for demo purposes

Focus: Simple, clear logging setup that works well for demo environments.
"""

import logging
import sys
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LogConfig(BaseModel):
    """
    Logging configuration for demo services.
    
    DEMO PURPOSE: Provides a simple way to configure logging consistently
    across all services, replacing the various logging setups currently used.
    """
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    include_request_id: bool = True
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    
    model_config = ConfigDict(env_prefix="LOG_")  # Allow LOG_LEVEL, LOG_FORMAT, etc.


def setup_logging(config: LogConfig = None, service_name: str = "bookverse") -> None:
    """
    Set up logging configuration for a BookVerse service.
    
    DEMO PURPOSE: Replaces the basic logging.basicConfig() calls in each service
    with a standardized, more comprehensive logging setup.
    
    Previously: Each service had basic logging setup like:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s...')
    
    Now: Single, consistent logging setup with better formatting and options
    
    Args:
        config: Logging configuration (uses defaults if None)
        service_name: Name of the service for log identification
    """
    if config is None:
        config = LogConfig()
    
    # Convert string level to logging constant
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    
    # Create formatter with service name
    log_format = f"[{service_name}] {config.format}"
    formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if config.log_to_file and config.log_file_path:
        try:
            file_handler = logging.FileHandler(config.log_file_path)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Log to console if file logging fails
            logging.error(f"Failed to set up file logging: {e}")
    
    # Log the setup completion
    logging.info(f"✅ Logging configured for {service_name} (level: {config.level})")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with consistent configuration.
    
    DEMO PURPOSE: Provides a simple way to get loggers that are consistent
    with the service's logging configuration.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("This is a log message")
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_request_start(logger: logging.Logger, method: str, path: str, request_id: str = None):
    """
    Log the start of a request with consistent format.
    
    DEMO PURPOSE: Provides standardized request logging that can be used
    across all services for consistent request tracking.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        request_id: Optional request ID for tracking
    """
    request_info = f"{method} {path}"
    if request_id:
        request_info += f" [ID: {request_id}]"
    
    logger.info(f"📥 Request started: {request_info}")


def log_request_end(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str = None
):
    """
    Log the end of a request with consistent format.
    
    DEMO PURPOSE: Provides standardized request completion logging.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        request_id: Optional request ID for tracking
    """
    request_info = f"{method} {path}"
    if request_id:
        request_info += f" [ID: {request_id}]"
    
    # Choose emoji based on status code
    if status_code >= 500:
        emoji = "❌"
        log_level = logging.ERROR
    elif status_code >= 400:
        emoji = "⚠️"
        log_level = logging.WARNING
    else:
        emoji = "✅"
        log_level = logging.INFO
    
    logger.log(
        log_level,
        f"{emoji} Request completed: {request_info} - {status_code} ({duration_ms:.1f}ms)"
    )


def log_service_startup(logger: logging.Logger, service_name: str, version: str, port: int = None):
    """
    Log service startup with consistent format.
    
    DEMO PURPOSE: Provides standardized service startup logging.
    
    Args:
        logger: Logger instance
        service_name: Name of the service
        version: Service version
        port: Port number (if applicable)
    """
    startup_msg = f"🚀 {service_name} v{version} starting up"
    if port:
        startup_msg += f" on port {port}"
    
    logger.info(startup_msg)


def log_service_shutdown(logger: logging.Logger, service_name: str):
    """
    Log service shutdown with consistent format.
    
    DEMO PURPOSE: Provides standardized service shutdown logging.
    
    Args:
        logger: Logger instance
        service_name: Name of the service
    """
    logger.info(f"🛑 {service_name} shutting down")


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str = None,
    request_id: str = None
):
    """
    Log an error with additional context information.
    
    DEMO PURPOSE: Provides consistent error logging with context
    that helps with debugging in demo environments.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context about where the error occurred
        request_id: Optional request ID for tracking
    """
    error_msg = f"❌ {type(error).__name__}: {str(error)}"
    
    if context:
        error_msg += f" (Context: {context})"
    
    if request_id:
        error_msg += f" [ID: {request_id}]"
    
    logger.error(error_msg, exc_info=True)


# Demo-specific logging helpers
def log_demo_info(logger: logging.Logger, message: str):
    """
    Log demo-specific information with special formatting.
    
    DEMO PURPOSE: Helps identify demo-specific log messages during presentations.
    
    Args:
        logger: Logger instance
        message: Demo information to log
    """
    logger.info(f"🎯 DEMO: {message}")


def log_duplication_eliminated(logger: logging.Logger, component: str, lines_saved: int):
    """
    Log information about code duplication elimination.
    
    DEMO PURPOSE: Specifically for logging the benefits of the commons library.
    
    Args:
        logger: Logger instance
        component: Component where duplication was eliminated
        lines_saved: Number of lines of code saved
    """
    logger.info(f"♻️ COMMONS: {component} - eliminated {lines_saved} lines of duplicate code")
