from .routers import router as routers_router
from .tasks import router as tasks_router
from .scan import router as scan_router
from .versions import router as versions_router
from .auth import router as auth_router
from .users import router as users_router
from .groups import router as groups_router
from .schedules import router as schedules_router
from .notifications import router as notifications_router
from .backups import router as backups_router
from .scripts import router as scripts_router
from .monitoring import router as monitoring_router
from .reports import router as reports_router
from .dashboard import router as dashboard_router
from .webhooks import router as webhooks_router
from .discovery import router as discovery_router

__all__ = [
    "routers_router",
    "tasks_router",
    "scan_router",
    "versions_router",
    "auth_router",
    "users_router",
    "groups_router",
    "schedules_router",
    "notifications_router",
    "backups_router",
    "scripts_router",
    "monitoring_router",
    "reports_router",
    "dashboard_router",
    "webhooks_router",
    "discovery_router",
]
