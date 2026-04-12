#!/usr/bin/env python3
"""
MikroTik Mass Updater - Startup Script

This script provides a convenient way to run the application.
It can run in development mode or production mode.

Usage:
    python run.py              # Development mode (with auto-reload)
    python run.py --prod       # Production mode
    python run.py --host 0.0.0.0 --port 8080  # Custom host/port
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import librouteros
        print("All Python dependencies are installed.")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e.name}")
        print("Please install dependencies: pip install -r backend/requirements.txt")
        return False


def check_frontend_build():
    """Check if frontend is built."""
    static_dir = Path(__file__).parent / "backend" / "static" / "index.html"
    return static_dir.exists()


def build_frontend():
    """Build the frontend."""
    frontend_dir = Path(__file__).parent / "frontend"

    print("Installing frontend dependencies with npm ci...")
    result = subprocess.run(
        ["npm", "ci"],
        cwd=frontend_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Failed to install dependencies: {result.stderr}")
        return False

    print("Building frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Failed to build frontend: {result.stderr}")
        return False

    print("Frontend built successfully.")
    return True


def run_dev_server(host: str, port: int):
    """Run development server with auto-reload."""
    import uvicorn

    print(f"\nStarting development server at http://{host}:{port}")
    print(f"API documentation: http://{host}:{port}/api/docs")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["backend"]
    )


def run_prod_server(host: str, port: int, workers: int):
    """Run production server."""
    import uvicorn

    print(f"\nStarting production server at http://{host}:{port}")
    print(f"Workers: {workers}")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        workers=workers,
        access_log=True
    )


def main():
    parser = argparse.ArgumentParser(
        description="MikroTik Mass Updater - Web Application"
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run in production mode"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of workers for production mode (default: 4)"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build frontend before starting"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check dependencies and exit"
    )

    args = parser.parse_args()

    # Change to script directory
    os.chdir(Path(__file__).parent)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    if args.check:
        print("Dependency check passed.")
        sys.exit(0)

    # Build frontend if requested or not built
    if args.build or (args.prod and not check_frontend_build()):
        if not build_frontend():
            if args.prod:
                print("Frontend build failed. Refusing to start production server.")
                sys.exit(1)
            print("Warning: Frontend build failed. API will still work.")

    # Run server
    if args.prod:
        run_prod_server(args.host, args.port, args.workers)
    else:
        run_dev_server(args.host, args.port)


if __name__ == "__main__":
    main()
