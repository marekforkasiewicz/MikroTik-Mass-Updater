#!/bin/bash
# RouterOS API Test Runner

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== MikroTik Mass Updater - API Tests ===${NC}"
echo ""

# Check for pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio requests
fi

# Parse arguments
INTEGRATION=false
ROUTER_HOST=""
ROUTER_USER="admin"
ROUTER_PASS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--integration)
            INTEGRATION=true
            shift
            ;;
        -h|--host)
            ROUTER_HOST="$2"
            shift 2
            ;;
        -u|--user)
            ROUTER_USER="$2"
            shift 2
            ;;
        -p|--password)
            ROUTER_PASS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -i, --integration     Run integration tests against real router"
            echo "  -h, --host HOST       Router IP address"
            echo "  -u, --user USER       Router username (default: admin)"
            echo "  -p, --password PASS   Router password"
            echo "  --help                Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run unit tests only"
            echo "  $0 -i -h 192.168.1.1 -p mypassword   # Run all tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

cd "$(dirname "$0")"

if [ "$INTEGRATION" = true ]; then
    if [ -z "$ROUTER_HOST" ]; then
        echo -e "${RED}Error: --host required for integration tests${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Running integration tests against ${ROUTER_HOST}${NC}"
    echo ""

    export ROUTEROS_HOST="$ROUTER_HOST"
    export ROUTEROS_USER="$ROUTER_USER"
    export ROUTEROS_PASS="$ROUTER_PASS"

    pytest tests/test_routeros_api.py -v --tb=short
else
    echo -e "${YELLOW}Running unit tests only (use -i for integration tests)${NC}"
    echo ""

    pytest tests/test_routeros_api.py -v --tb=short -m "not integration"
fi

echo ""
echo -e "${GREEN}Tests completed!${NC}"
