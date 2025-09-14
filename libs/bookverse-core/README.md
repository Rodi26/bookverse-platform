# BookVerse Core Library Demo

## 🎯 Demo Purpose

This repository demonstrates how the **bookverse-core** library eliminates code duplication and standardizes patterns across BookVerse services. Instead of each service implementing its own authentication, configuration, API patterns, and utilities, they can all use this shared library.

## 📊 Code Duplication Eliminated

### Before bookverse-core:
- **Authentication**: 281 lines × 4 services = **1,124 lines of duplicate code**
- **Configuration**: 4 completely different approaches across services
- **API Patterns**: Each service implements its own FastAPI setup and middleware
- **Database Utilities**: Repeated session management and pagination logic
- **Logging**: Basic `logging.basicConfig()` calls in each service

### After bookverse-core:
- **Authentication**: Single shared implementation (281 lines total)
- **Configuration**: Unified system supporting YAML, env vars, and defaults
- **API Patterns**: Standardized app factory with consistent middleware
- **Database Utilities**: Shared session management and pagination
- **Logging**: Comprehensive, standardized logging setup

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip or poetry

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install the library in development mode
pip install -e .
```

### Running the Demo
```bash
# Start the demo application
python app/main.py

# Or use uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The demo application will be available at: http://localhost:8000

## 📚 Demo Endpoints

### Core Demonstrations

| Endpoint | Purpose | Demo Benefit |
|----------|---------|--------------|
| `/demo/summary` | Complete overview of library benefits | Shows all eliminated duplication |
| `/demo/info` | Service information and configuration | Demonstrates unified config system |
| `/demo/auth/protected` | JWT authentication | Shows shared auth (eliminates 1,124 lines) |
| `/demo/config/current` | Configuration display | Shows unified config (replaces 4 approaches) |
| `/demo/logging/test` | Logging patterns | Shows standardized logging |
| `/demo/pagination/items` | Pagination demo | Shows shared pagination utilities |

### Authentication Demonstrations

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/demo/auth/public` | No | Public endpoint |
| `/demo/auth/protected` | Yes | Protected endpoint requiring JWT |
| `/demo/auth/optional` | Optional | Works with or without auth |

### Technical Demonstrations

| Endpoint | Feature | Benefit |
|----------|---------|---------|
| `/demo/middleware/demo` | Middleware patterns | Consistent request handling |
| `/demo/error/demo` | Error handling | Standardized error responses |
| `/demo/responses/demo` | Response patterns | Consistent API responses |
| `/demo/validation/test` | Validation utilities | Shared validation functions |

### Standard Endpoints (Available in all services)

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic health check |
| `/health/live` | Kubernetes liveness probe |
| `/health/ready` | Kubernetes readiness probe |
| `/health/auth` | Authentication service health |
| `/info` | Service information |
| `/docs` | Interactive API documentation |

## 🔧 Configuration

The demo supports multiple configuration sources with clear precedence:

1. **Default values** (lowest priority)
2. **YAML file** (`config/demo-config.yaml`)
3. **Environment variables** (with `DEMO_` prefix)
4. **Direct overrides** (highest priority)

### Environment Variables

```bash
# Service configuration
DEMO_SERVICE_NAME="My Custom Demo Service"
DEMO_LOG_LEVEL="DEBUG"
DEMO_DEBUG="true"

# Authentication configuration
DEMO_AUTH_ENABLED="true"
DEMO_DEVELOPMENT_MODE="true"
DEMO_OIDC_AUTHORITY="https://your-auth-server.com"

# Database configuration
DEMO_DATABASE_URL="sqlite:///./custom_demo.db"
```

## 🧪 Testing the Demo

### 1. Basic Health Check
```bash
curl http://localhost:8000/health
```

### 2. Demo Summary
```bash
curl http://localhost:8000/demo/summary
```

### 3. Configuration Demo
```bash
curl http://localhost:8000/demo/config/current
```

### 4. Authentication Demo (Public)
```bash
curl http://localhost:8000/demo/auth/public
```

### 5. Pagination Demo
```bash
curl "http://localhost:8000/demo/pagination/items?page=1&per_page=2"
```

### 6. Logging Demo
```bash
curl http://localhost:8000/demo/logging/test
# Check console output for standardized logging
```

### 7. Validation Demo
```bash
curl http://localhost:8000/demo/validation/test
```

## 📋 Library Components

### Authentication (`bookverse_core.auth`)
- **JWT token validation** with OIDC support
- **FastAPI dependencies** for different auth scenarios
- **Middleware** for automatic authentication
- **Health checks** for auth service connectivity

**Replaces**: Identical 281-line auth modules in all 4 services

### Configuration (`bookverse_core.config`)
- **Unified configuration system** supporting multiple sources
- **Pydantic-based validation** with type safety
- **Environment variable support** with prefixes
- **YAML configuration** with defaults merging

**Replaces**: 4 different configuration approaches across services

### API Utilities (`bookverse_core.api`)
- **FastAPI app factory** with standard middleware
- **Response models** for consistent API responses
- **Pagination utilities** for database queries
- **Health check endpoints** with service integration

**Replaces**: Repeated FastAPI setup and middleware in each service

### Database Utilities (`bookverse_core.database`)
- **Session management** with FastAPI integration
- **Pagination helpers** for SQLAlchemy queries
- **Database configuration** and connection handling

**Replaces**: Duplicate database session management across services

### Common Utilities (`bookverse_core.utils`)
- **Standardized logging** setup and patterns
- **Validation functions** for common data types
- **Demo-specific helpers** for presentations

**Replaces**: Basic logging setup and duplicate validation code

## 🔄 Migration Path

### Phase 1: Library Validation (Current)
- ✅ Create bookverse-core library with all components
- ✅ Build comprehensive demo application
- ✅ Validate all functionality works correctly
- ✅ Performance testing and optimization

### Phase 2: Service Migration (Next)
1. **Inventory Service** (pilot migration)
   - Replace auth module with `bookverse_core.auth`
   - Replace config with `bookverse_core.config`
   - Update FastAPI setup to use app factory

2. **Recommendations Service**
   - Migrate complex YAML config to unified system
   - Replace auth module
   - Update worker components

3. **Checkout Service**
   - Careful migration preserving complex patterns
   - Replace auth and config modules
   - Maintain idempotency and outbox patterns

4. **Platform Service**
   - Replace auth and config modules
   - Preserve specialized aggregation logic

### Phase 3: Validation & Cleanup
- Remove old duplicate code
- Measure actual code reduction
- Performance validation
- Documentation updates

## 📈 Expected Results

### Code Reduction
- **Total codebase**: ~6,200 lines → ~4,870 lines (**21% reduction**)
- **Authentication duplication**: 1,124 lines → 0 lines (**100% elimination**)
- **Configuration consistency**: 4 approaches → 1 approach (**unified**)

### Maintenance Benefits
- **Security updates**: 4 places → 1 place
- **Configuration changes**: 4 different patterns → 1 pattern
- **API consistency**: Variable → Standardized
- **Debugging**: Inconsistent logs → Standardized logs

## 🛠️ Development

### Project Structure
```
bookverse-core/
├── bookverse_core/           # Python library
│   ├── auth/                # Authentication components
│   ├── config/              # Configuration management
│   ├── api/                 # FastAPI utilities
│   ├── database/            # Database utilities
│   └── utils/               # Common utilities
├── app/                     # Demo FastAPI application
│   ├── main.py             # Main demo application
│   └── api/                # Additional demo endpoints
├── tests/                   # Test suite (80% coverage target)
├── config/                  # Configuration files
├── pyproject.toml          # Python package configuration
└── README.md               # This file
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bookverse_core --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Code Quality
```bash
# Format code
black bookverse_core/ app/

# Sort imports
isort bookverse_core/ app/

# Lint code
flake8 bookverse_core/ app/

# Type checking
mypy bookverse_core/
```

## 📖 Documentation

### Interactive API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Library Documentation
Each module includes comprehensive docstrings explaining:
- **Demo Purpose**: Why this eliminates duplication
- **Usage Examples**: How to use in services
- **Benefits**: What problems it solves
- **Migration Notes**: How to migrate from existing code

## 🤝 Contributing

This is a demo library showcasing code deduplication patterns. For production use:

1. **Extend validation** for production requirements
2. **Add comprehensive error handling** for edge cases
3. **Implement production-grade security** features
4. **Add performance optimizations** for scale
5. **Create migration tools** for existing services

## 📞 Support

For questions about the demo or library usage:
- Check the interactive documentation at `/docs`
- Review the demo endpoints for usage examples
- Examine the source code for implementation details
- Test different configuration scenarios

---

**Demo Status**: ✅ Ready for presentation and validation  
**Next Phase**: Service migration and integration testing
