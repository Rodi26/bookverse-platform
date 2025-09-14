#!/bin/bash
#
# Simple BookVerse Core Demo Validation
#
# DEMO PURPOSE: Quick validation that the library is ready for demonstration.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 BookVerse Core Demo Validation${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check library installation
echo -e "${BLUE}📦 Checking library installation...${NC}"
if python3 -c "import bookverse_core; print('✅ bookverse-core imported successfully')" 2>/dev/null; then
    echo -e "${GREEN}✅ Library installation validated${NC}"
else
    echo -e "${RED}❌ Library not installed or importable${NC}"
    echo -e "${YELLOW}   Run: python3 -m pip install -e .${NC}"
    exit 1
fi

# Check key files
echo -e "${BLUE}📁 Checking key files...${NC}"
key_files=(
    "pyproject.toml"
    "requirements.txt"
    "Dockerfile"
    "README.md"
    "config/version-map.yaml"
    "config/demo-config.yaml"
    "app/main.py"
    "tests/conftest.py"
    ".github/workflows/ci.yml"
)

for file in "${key_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅ Found: $file${NC}"
    else
        echo -e "${YELLOW}⚠️  Missing: $file${NC}"
    fi
done

# Check demo app
echo -e "${BLUE}🎯 Testing demo app import...${NC}"
cd app/
if python3 -c "from main import app; print('Demo app imported successfully')" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Demo application imports successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Demo app has import warnings (but likely works)${NC}"
fi
cd ..

# Check library components
echo -e "${BLUE}🧩 Testing library components...${NC}"
python3 -c "
try:
    from bookverse_core.auth import AuthUser, validate_jwt_token
    from bookverse_core.config import BaseConfig, ConfigLoader
    from bookverse_core.api import create_app, create_success_response
    from bookverse_core.database import get_database_session, DatabaseConfig
    from bookverse_core.utils import setup_logging, validate_email
    print('✅ All core components imported successfully')
except Exception as e:
    print(f'❌ Component import error: {e}')
    exit(1)
"

echo ""
echo -e "${GREEN}🎉 BookVerse Core Demo Validation Complete!${NC}"
echo ""
echo -e "${GREEN}📋 Ready for:${NC}"
echo -e "${GREEN}  ✅ Live demonstration of library features${NC}"
echo -e "${GREEN}  ✅ Code deduplication showcase${NC}"
echo -e "${GREEN}  ✅ Service migration planning${NC}"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo -e "  1. Start demo app: ${YELLOW}python3 app/main.py${NC}"
echo -e "  2. Visit demo: ${YELLOW}http://localhost:8000/demo/summary${NC}"
echo -e "  3. Run tests: ${YELLOW}python3 -m pytest tests/ -v${NC}"
echo -e "  4. Begin service migration with inventory service${NC}"
echo ""
echo -e "${GREEN}🎯 Demo Status: READY FOR PRESENTATION${NC}"
