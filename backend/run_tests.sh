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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

if [ -x "$REPO_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$REPO_DIR/venv/bin/python"
else
    PYTHON_BIN="$(command -v python3)"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}python3 not found.${NC}"
    exit 1
fi

PYTEST_CMD=("$PYTHON_BIN" -m pytest)

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

cd "$SCRIPT_DIR"

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

    "${PYTEST_CMD[@]}" tests/test_routeros_api.py -v --tb=short
else
    echo -e "${YELLOW}Running unit tests only (use -i for integration tests)${NC}"
    echo ""

    "${PYTEST_CMD[@]}" tests/test_routeros_api.py -v --tb=short -m "not integration"
fi

echo ""
echo -e "${GREEN}Tests completed!${NC}"
