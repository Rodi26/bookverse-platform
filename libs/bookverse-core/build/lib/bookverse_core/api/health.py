"""
Health check endpoints and utilities for BookVerse Demo.

DEMO PURPOSE: This module demonstrates how to standardize health checks across services.
Instead of each service implementing different health check patterns, they can use this
shared, consistent implementation.

Key Demo Benefits:
- Consistent health check format across all services
- Standard endpoints for Kubernetes probes (/health/live, /health/ready)
- Integrated authentication service health checking
- Single place to update health check behavior

Focus: Essential health checks that demonstrate the pattern, kept simple for demo clarity.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import check_auth_connection, get_auth_status
from .responses import HealthResponse, create_health_response

logger = logging.getLogger(__name__)

# Global service start time for uptime calculation
_service_start_time = time.time()


def create_health_router(
    service_name: str = "BookVerse Service",
    service_version: str = "1.0.0",
    health_checks: Optional[List[str]] = None
) -> APIRouter:
    """
    Create a health check router with standard endpoints.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        health_checks: List of health check types to enable
        
    Returns:
        FastAPI router with health endpoints
    """
    router = APIRouter(tags=["health"])
    health_checks = health_checks or ["basic"]
    
    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        """
        Basic health check endpoint.
        
        Returns service status and basic health information.
        """
        checks = {}
        overall_status = "healthy"
        
        # Run enabled health checks
        for check_type in health_checks:
            try:
                if check_type == "basic":
                    checks["basic"] = {"status": "healthy", "message": "Service is running"}
                elif check_type == "auth":
                    auth_status = await check_auth_connection()
                    checks["auth"] = auth_status
                    if auth_status.get("status") != "healthy":
                        overall_status = "degraded"
                elif check_type == "database":
                    # Database check will be implemented when database dependency is available
                    checks["database"] = {"status": "not_implemented", "message": "Database check not implemented"}
                else:
                    checks[check_type] = {"status": "unknown", "message": f"Unknown check type: {check_type}"}
            except Exception as e:
                logger.error(f"Health check failed for {check_type}: {e}")
                checks[check_type] = {"status": "unhealthy", "error": str(e)}
                overall_status = "unhealthy"
        
        # Calculate uptime
        uptime = time.time() - _service_start_time
        
        return create_health_response(
            status=overall_status,
            service=service_name,
            version=service_version,
            checks=checks,
            uptime=uptime
        )
    
    @router.get("/health/live")
    async def liveness_check():
        """
        Kubernetes liveness probe endpoint.
        
        Returns 200 if service is alive, 503 if not.
        """
        return {"status": "alive", "timestamp": time.time()}
    
    @router.get("/health/ready")
    async def readiness_check():
        """
        Kubernetes readiness probe endpoint.
        
        Returns 200 if service is ready to accept traffic, 503 if not.
        """
        # Check if service is ready (basic checks)
        try:
            # Add readiness checks here (database connections, etc.)
            return {"status": "ready", "timestamp": time.time()}
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            raise HTTPException(status_code=503, detail="Service not ready")
    
    @router.get("/health/auth")
    async def auth_health_check():
        """
        Authentication service health check.
        
        Returns detailed authentication service status.
        """
        if "auth" not in health_checks:
            raise HTTPException(status_code=404, detail="Auth health check not enabled")
        
        try:
            auth_status = get_auth_status()
            auth_connection = await check_auth_connection()
            
            return {
                "auth_config": auth_status,
                "auth_connection": auth_connection,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Auth health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Auth health check failed: {str(e)}")
    
    return router


def create_database_health_check(get_db: Callable[[], Session]):
    """
    Create a database health check function.
    
    Args:
        get_db: Database session dependency function
        
    Returns:
        Database health check function
    """
    async def check_database_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            # Simple query to test database connection
            from sqlalchemy import text
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    return check_database_health


def create_custom_health_check(
    name: str,
    check_function: Callable[[], Dict[str, Any]]
):
    """
    Create a custom health check endpoint.
    
    Args:
        name: Name of the health check
        check_function: Function that performs the health check
        
    Returns:
        Health check endpoint function
    """
    async def custom_health_check():
        """Custom health check endpoint."""
        try:
            result = await check_function() if callable(check_function) else check_function()
            return {
                "check": name,
                "result": result,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Custom health check '{name}' failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Health check '{name}' failed: {str(e)}"
            )
    
    return custom_health_check


def get_service_uptime() -> float:
    """
    Get service uptime in seconds.
    
    Returns:
        Uptime in seconds since service start
    """
    return time.time() - _service_start_time


def reset_service_start_time():
    """
    Reset the service start time.
    
    Useful for testing or service restarts.
    """
    global _service_start_time
    _service_start_time = time.time()


# Note: Removed HealthCheckRegistry for demo simplicity
# Focus on basic health checks that demonstrate the standardization pattern
