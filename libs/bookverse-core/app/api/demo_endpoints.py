"""
Additional demo endpoints showcasing bookverse-core library features.

DEMO PURPOSE: These endpoints demonstrate specific library features in isolation,
making it easy to understand each component's benefits during presentations.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bookverse_core.auth import AuthUser, RequireAuth, get_current_user
from bookverse_core.api.pagination import PaginationParams, create_pagination_params, paginate
from bookverse_core.api.responses import create_success_response, create_error_response
from bookverse_core.utils import get_logger
from bookverse_core.utils.validation import validate_email, sanitize_string

logger = get_logger(__name__)

# Create router for demo endpoints
router = APIRouter(prefix="/demo", tags=["Demo Features"])


# Demo data models
class DemoItem(BaseModel):
    """Demo item model for showcasing API patterns."""
    id: int
    name: str
    description: str
    category: str
    active: bool = True


class CreateDemoItemRequest(BaseModel):
    """Request model for creating demo items."""
    name: str
    description: str
    category: str


# In-memory demo data (normally this would be in a database)
demo_items: List[DemoItem] = [
    DemoItem(id=1, name="Demo Book 1", description="A sample book for demonstration", category="fiction"),
    DemoItem(id=2, name="Demo Book 2", description="Another sample book", category="non-fiction"),
    DemoItem(id=3, name="Demo Book 3", description="Yet another sample book", category="fiction"),
    DemoItem(id=4, name="Demo Book 4", description="Fourth sample book", category="science"),
    DemoItem(id=5, name="Demo Book 5", description="Fifth sample book", category="fiction"),
]


@router.get("/pagination/items")
async def paginated_items_demo(
    pagination: PaginationParams = Depends(create_pagination_params),
    category: str = Query(None, description="Filter by category")
):
    """
    Demonstrate standardized pagination patterns.
    
    DEMO PURPOSE: Shows how the shared pagination utilities work.
    This replaces the create_pagination_meta() function that was only
    in the inventory service, making it available to all services.
    """
    logger.info(f"📄 Pagination demo: page {pagination.page}, per_page {pagination.per_page}")
    
    # Filter items if category specified
    filtered_items = demo_items
    if category:
        filtered_items = [item for item in demo_items if item.category == category]
    
    # Simulate pagination (normally done with database query)
    total = len(filtered_items)
    start_idx = pagination.offset
    end_idx = start_idx + pagination.per_page
    page_items = filtered_items[start_idx:end_idx]
    
    # Use shared pagination utility
    paginated_response = paginate(
        items=page_items,
        total=total,
        pagination=pagination
    )
    
    return {
        **paginated_response.model_dump(),
        "demo_notes": {
            "pagination_source": "bookverse_core.api.pagination",
            "replaces": "Inventory service's create_pagination_meta() function",
            "benefit": "Consistent pagination across all services",
            "try_params": "?page=2&per_page=2&category=fiction"
        }
    }


@router.post("/items")
async def create_demo_item(
    request: CreateDemoItemRequest,
    user: AuthUser = RequireAuth
):
    """
    Demonstrate authenticated item creation with validation.
    
    DEMO PURPOSE: Shows authentication, validation, and response patterns working together.
    """
    logger.info(f"📝 Creating demo item: {request.name} by user {user.email}")
    
    # Validate and sanitize input using shared utilities
    try:
        clean_name = sanitize_string(request.name, max_length=100)
        clean_description = sanitize_string(request.description, max_length=500)
        clean_category = sanitize_string(request.category, max_length=50)
    except ValueError as e:
        logger.warning(f"⚠️ Validation failed: {e}")
        return create_error_response(
            error="Validation failed",
            error_code="validation_error",
            details={"validation_error": str(e)}
        )
    
    # Create new item (simulate database save)
    new_id = max([item.id for item in demo_items]) + 1 if demo_items else 1
    new_item = DemoItem(
        id=new_id,
        name=clean_name,
        description=clean_description,
        category=clean_category
    )
    demo_items.append(new_item)
    
    logger.info(f"✅ Demo item created with ID: {new_id}")
    
    return create_success_response(
        data=new_item,
        message=f"Demo item '{clean_name}' created successfully"
    )


@router.get("/middleware/demo")
async def middleware_demo():
    """
    Demonstrate middleware functionality.
    
    DEMO PURPOSE: Shows how the standardized middleware works.
    Check the logs to see request ID tracking, timing, and error handling.
    """
    logger.info("🔧 Middleware demo endpoint accessed")
    
    # The middleware automatically adds:
    # - Request ID tracking
    # - Request/response logging  
    # - Error handling
    # - CORS headers
    
    return {
        "message": "Middleware demonstration",
        "middleware_features": [
            "Request ID tracking (check X-Request-ID header)",
            "Automatic request/response logging",
            "Centralized error handling", 
            "CORS headers for web frontend integration",
            "Request timing and performance monitoring"
        ],
        "demo_benefits": [
            "Consistent middleware across all services",
            "Standardized request tracking and debugging",
            "Single place to update middleware behavior",
            "Eliminates duplicate middleware implementations"
        ],
        "check_logs": "Look at the console to see the middleware logging in action!",
        "check_headers": "Look at the response headers to see X-Request-ID"
    }


@router.get("/error/demo")
async def error_handling_demo(simulate_error: bool = Query(False, description="Simulate an error")):
    """
    Demonstrate standardized error handling.
    
    DEMO PURPOSE: Shows how the shared error handling middleware works.
    """
    logger.info(f"❌ Error handling demo: simulate_error={simulate_error}")
    
    if simulate_error:
        # This error will be caught by the error handling middleware
        # and returned as a standardized error response
        raise ValueError("This is a simulated error for demonstration purposes")
    
    return create_success_response(
        data={"error_simulated": False},
        message="No error simulated - try ?simulate_error=true to see error handling"
    )


@router.get("/responses/demo")
async def response_patterns_demo():
    """
    Demonstrate standardized response patterns.
    
    DEMO PURPOSE: Shows the consistent response models used across all services.
    """
    logger.info("📋 Response patterns demo accessed")
    
    # Show different response types
    success_example = create_success_response(
        data={"example": "data"},
        message="This is a success response"
    )
    
    error_example = create_error_response(
        error="This is an example error message",
        error_code="demo_error",
        details={"additional": "error context"}
    )
    
    return {
        "message": "Response patterns demonstration",
        "response_types": {
            "success_response": success_example.model_dump(),
            "error_response": error_example.model_dump(),
        },
        "demo_benefits": [
            "Consistent response format across all services",
            "Standardized error responses with codes and details",
            "Automatic timestamp and request ID inclusion",
            "Type-safe response models with Pydantic validation"
        ]
    }


@router.get("/health/detailed")
async def detailed_health_demo():
    """
    Demonstrate detailed health checking capabilities.
    
    DEMO PURPOSE: Shows the comprehensive health check system that can be
    shared across all services.
    """
    from bookverse_core.auth import get_auth_status, check_auth_connection
    
    logger.info("🏥 Detailed health check demo accessed")
    
    # Get authentication service status
    auth_status = get_auth_status()
    auth_connection = await check_auth_connection()
    
    return {
        "message": "Detailed health check demonstration",
        "health_components": {
            "service": {
                "status": "healthy",
                "uptime_seconds": "calculated_automatically",
                "version": "0.1.0"
            },
            "authentication": {
                "config_status": auth_status,
                "connection_status": auth_connection
            },
            "configuration": {
                "status": "healthy",
                "sources_loaded": ["defaults", "yaml", "environment"]
            },
            "logging": {
                "status": "healthy", 
                "level": "INFO",
                "format": "standardized"
            }
        },
        "demo_benefits": [
            "Comprehensive health checks for all service components",
            "Standardized health check format across services",
            "Integration with authentication service monitoring",
            "Ready for Kubernetes liveness and readiness probes"
        ],
        "standard_endpoints": {
            "/health": "Basic health check",
            "/health/live": "Kubernetes liveness probe",
            "/health/ready": "Kubernetes readiness probe", 
            "/health/auth": "Authentication service health"
        }
    }
