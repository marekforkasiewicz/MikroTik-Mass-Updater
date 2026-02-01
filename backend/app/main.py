"""FastAPI main application entry point"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .database import init_db, SessionLocal
from .api import (
    routers_router, tasks_router, scan_router, versions_router,
    auth_router, users_router, groups_router, schedules_router,
    notifications_router, backups_router, scripts_router,
    monitoring_router, reports_router, dashboard_router, webhooks_router
)
from .api.websocket import router as websocket_router
from .services.auth_service import AuthService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    logger.info("Database initialized")

    # Ensure admin user exists
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        auth_service.ensure_admin_exists()
    finally:
        db.close()

    # Start scheduler if enabled
    if settings.FEATURE_SCHEDULING:
        try:
            from .core.scheduler import get_scheduler
            from .services.scheduler_service import SchedulerService

            scheduler = get_scheduler()
            scheduler.start()
            logger.info("Scheduler started")

            # Sync schedules
            db = SessionLocal()
            try:
                scheduler_service = SchedulerService(db)
                scheduler_service.sync_all_schedules()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to start scheduler: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop scheduler
    if settings.FEATURE_SCHEDULING:
        try:
            from .core.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.shutdown()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.warning(f"Error stopping scheduler: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Web-based MikroTik router management and mass update tool",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers - Original
app.include_router(routers_router, prefix=settings.API_PREFIX)
app.include_router(tasks_router, prefix=settings.API_PREFIX)
app.include_router(scan_router, prefix=settings.API_PREFIX)
app.include_router(versions_router, prefix=settings.API_PREFIX)
app.include_router(websocket_router)

# Include API routers - New features
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(groups_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)

if settings.FEATURE_SCHEDULING:
    app.include_router(schedules_router, prefix=settings.API_PREFIX)

if settings.FEATURE_NOTIFICATIONS:
    app.include_router(notifications_router, prefix=settings.API_PREFIX)

app.include_router(backups_router, prefix=settings.API_PREFIX)

if settings.FEATURE_SCRIPTS:
    app.include_router(scripts_router, prefix=settings.API_PREFIX)

if settings.FEATURE_MONITORING:
    app.include_router(monitoring_router, prefix=settings.API_PREFIX)

if settings.FEATURE_REPORTS:
    app.include_router(reports_router, prefix=settings.API_PREFIX)

if settings.FEATURE_WEBHOOKS:
    app.include_router(webhooks_router, prefix=settings.API_PREFIX)


# API info endpoint
@app.get("/api")
async def api_info():
    """API information endpoint"""
    endpoints = {
        "routers": "/api/routers",
        "tasks": "/api/tasks",
        "scan": "/api/scan",
        "versions": "/api/versions",
        "auth": "/api/auth",
        "users": "/api/users",
        "groups": "/api/groups",
        "dashboard": "/api/dashboard",
    }

    if settings.FEATURE_SCHEDULING:
        endpoints["schedules"] = "/api/schedules"
    if settings.FEATURE_NOTIFICATIONS:
        endpoints["notifications"] = "/api/notifications"
    if settings.FEATURE_SCRIPTS:
        endpoints["scripts"] = "/api/scripts"
    if settings.FEATURE_MONITORING:
        endpoints["monitoring"] = "/api/monitoring"
    if settings.FEATURE_REPORTS:
        endpoints["reports"] = "/api/reports"
    if settings.FEATURE_WEBHOOKS:
        endpoints["webhooks"] = "/api/webhooks"

    endpoints["backups"] = "/api/backups"

    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "endpoints": endpoints,
        "features": {
            "scheduling": settings.FEATURE_SCHEDULING,
            "monitoring": settings.FEATURE_MONITORING,
            "notifications": settings.FEATURE_NOTIFICATIONS,
            "scripts": settings.FEATURE_SCRIPTS,
            "webhooks": settings.FEATURE_WEBHOOKS,
            "reports": settings.FEATURE_REPORTS,
        }
    }


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


# Serve static files (Vue.js build)
static_dir = settings.STATIC_DIR
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = static_dir / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    # Catch-all route for SPA
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve Vue.js SPA for all non-API routes"""
        # Skip API routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend not built. Run 'npm run build' in frontend directory."}
        )
else:
    @app.get("/")
    async def root():
        """Root endpoint when frontend is not built"""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "api_docs": "/api/docs",
            "note": "Frontend not built. Run 'npm run build' in frontend directory."
        }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
