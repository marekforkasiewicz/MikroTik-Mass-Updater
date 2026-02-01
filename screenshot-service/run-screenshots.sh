#!/bin/bash
# Script to run screenshot service with Selenium Chrome

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="${SCREENSHOT_DIR:-/tmp/mikrotik-screenshots}"
APP_URL="${APP_URL:-http://192.168.1.14:8000}"
SELENIUM_CONTAINER="mikrotik-selenium-chrome"

echo "=============================================="
echo "MikroTik Mass Updater - Screenshot Capture"
echo "=============================================="

# Create screenshot directory
mkdir -p "$SCREENSHOT_DIR"

# Check if Selenium container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${SELENIUM_CONTAINER}$"; then
    echo "Starting Selenium Chrome container..."
    docker run -d --rm \
        --name "$SELENIUM_CONTAINER" \
        --network host \
        -e SE_NODE_MAX_SESSIONS=2 \
        -e SE_SESSION_REQUEST_TIMEOUT=300 \
        --shm-size=2g \
        selenium/standalone-chrome:latest

    echo "Waiting for Selenium to be ready..."
    sleep 10
    STARTED_SELENIUM=true
else
    echo "Selenium Chrome container already running"
    STARTED_SELENIUM=false
fi

# Check if selenium is available
if ! curl -s http://localhost:4444/status > /dev/null 2>&1; then
    echo "Waiting for Selenium Grid to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:4444/status > /dev/null 2>&1; then
            echo "Selenium Grid is ready"
            break
        fi
        sleep 1
    done
fi

# Install requirements if needed
if ! python3 -c "import selenium" 2>/dev/null; then
    echo "Installing selenium..."
    pip3 install selenium --quiet
fi

# Run screenshots
echo ""
echo "Taking screenshots..."
echo "App URL: $APP_URL"
echo "Output: $SCREENSHOT_DIR"
echo ""

SELENIUM_URL="http://localhost:4444/wd/hub" \
APP_URL="$APP_URL" \
SCREENSHOT_DIR="$SCREENSHOT_DIR" \
python3 "$SCRIPT_DIR/screenshot.py"

EXIT_CODE=$?

# Optionally stop Selenium container
if [ "$STARTED_SELENIUM" = true ] && [ "${KEEP_SELENIUM:-false}" != "true" ]; then
    echo ""
    echo "Stopping Selenium container..."
    docker stop "$SELENIUM_CONTAINER" > /dev/null 2>&1
fi

echo ""
echo "Screenshots saved to: $SCREENSHOT_DIR"
ls -la "$SCREENSHOT_DIR"/*.png 2>/dev/null || echo "No screenshots generated"

exit $EXIT_CODE
