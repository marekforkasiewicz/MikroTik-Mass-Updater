from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.core.rate_limit import InMemoryRateLimiter
from app.models.router import Router
from app.models.task import Task
from app.models.monitoring import AlertHistory
from app.schemas.report import ReportFilter
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService


class QueryStub:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)


class DatabaseStub:
    def __init__(self, mapping):
        self.mapping = mapping

    def query(self, model):
        rows = self.mapping.get(model, [])
        return QueryStub(rows)


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()

    for _ in range(3):
        status = limiter.check("login:client", limit=3, window_seconds=60)
        assert status.allowed is True

    blocked = limiter.check("login:client", limit=3, window_seconds=60)

    assert blocked.allowed is False
    assert blocked.retry_after_seconds > 0
    assert blocked.remaining == 0


def test_dashboard_recent_activity_uses_task_type_and_results():
    created_at = datetime.now(UTC)
    tasks = [
        SimpleNamespace(
            id="task-1",
            type="update",
            status="completed",
            config={"router_id": 10},
            results={"identity": "Core"},
            created_at=created_at,
        )
    ]
    alerts = [
        SimpleNamespace(
            id=7,
            title="Router offline",
            message="Ping failed",
            status="active",
            router_id=22,
            created_at=created_at - timedelta(minutes=1),
        )
    ]
    routers = [SimpleNamespace(id=22, identity="Edge")]

    db = DatabaseStub({
        Task: tasks,
        AlertHistory: alerts,
        Router: routers,
    })

    activity = DashboardService(db)._get_recent_activity(limit=10)

    assert activity[0]["id"] == "task-1"
    assert activity[0]["type"] == "update"
    assert activity[0]["router_identity"] == "Core"
    assert activity[1]["router_identity"] == "Edge"


def test_export_service_uses_task_type_results_and_completed_at(tmp_path):
    task = SimpleNamespace(
        id="task-2",
        type="update",
        status="completed",
        config={"router_id": 5},
        results={
            "identity": "JAJ",
            "ip": "192.168.1.10",
            "from_version": "7.14",
            "to_version": "7.15",
        },
        created_at=datetime.now(UTC) - timedelta(minutes=5),
        completed_at=datetime.now(UTC),
    )
    db = DatabaseStub({Task: [task]})

    service = ExportService(db)
    service.export_dir = tmp_path
    data = service._get_update_data(ReportFilter())

    assert data["total_updates"] == 1
    assert data["updates"][0]["update_type"] == "update"
    assert data["updates"][0]["router_identity"] == "JAJ"
    assert data["updates"][0]["completed_at"] == task.completed_at.isoformat()
