"""Dashboard service for aggregating data"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import Counter

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.router import Router
from ..models.task import Task
from ..models.schedule import ScheduledTask
from ..models.monitoring import HealthCheck, AlertHistory
from ..models.backup import RouterBackup
from ..core.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation"""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return {
            "router_stats": self._get_router_stats(),
            "version_distribution": self._get_version_distribution(),
            "model_distribution": self._get_model_distribution(),
            "channel_distribution": self._get_channel_distribution(),
            "health_summary": self._get_health_summary(),
            "recent_activity": self._get_recent_activity(),
            "upcoming_schedules": self._get_upcoming_schedules(),
            "alert_summary": self._get_alert_summary(),
            "system_status": self._get_system_status()
        }

    def _get_router_stats(self) -> Dict[str, int]:
        """Get router statistics"""
        routers = self.db.query(Router).all()

        return {
            "total": len(routers),
            "online": sum(1 for r in routers if r.is_online),
            "offline": sum(1 for r in routers if not r.is_online),
            "needs_update": sum(1 for r in routers if r.has_updates),
            "firmware_update": sum(1 for r in routers if r.has_firmware_update)
        }

    def _get_version_distribution(self) -> List[Dict[str, Any]]:
        """Get RouterOS version distribution"""
        routers = self.db.query(Router).filter(Router.ros_version != None).all()
        total = len(routers)

        if total == 0:
            return []

        version_counts = Counter(r.ros_version for r in routers)

        return [
            {
                "version": version,
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for version, count in version_counts.most_common(10)
        ]

    def _get_model_distribution(self) -> List[Dict[str, Any]]:
        """Get router model distribution"""
        routers = self.db.query(Router).filter(Router.model != None).all()
        total = len(routers)

        if total == 0:
            return []

        model_counts = Counter(r.model for r in routers)

        return [
            {
                "model": model,
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for model, count in model_counts.most_common(10)
        ]

    def _get_channel_distribution(self) -> List[Dict[str, Any]]:
        """Get update channel distribution"""
        routers = self.db.query(Router).filter(Router.update_channel != None).all()
        total = len(routers)

        if total == 0:
            return []

        channel_counts = Counter(r.update_channel for r in routers)

        return [
            {
                "channel": channel,
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for channel, count in channel_counts.items()
        ]

    def _get_health_summary(self) -> Dict[str, int]:
        """Get health status summary"""
        # Get latest health check for each router
        subquery = self.db.query(
            HealthCheck.router_id,
            func.max(HealthCheck.checked_at).label("latest")
        ).group_by(HealthCheck.router_id).subquery()

        latest_checks = self.db.query(HealthCheck).join(
            subquery,
            (HealthCheck.router_id == subquery.c.router_id) &
            (HealthCheck.checked_at == subquery.c.latest)
        ).all()

        status_counts = Counter(c.status for c in latest_checks)

        return {
            "healthy": status_counts.get("ok", 0),
            "warning": status_counts.get("warning", 0),
            "critical": status_counts.get("critical", 0),
            "unknown": status_counts.get("unknown", 0)
        }

    def _get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity feed"""
        activities = []

        # Get recent tasks
        tasks = self.db.query(Task).order_by(
            Task.created_at.desc()
        ).limit(limit).all()

        for task in tasks:
            activities.append({
                "id": task.id,
                "type": task.task_type,
                "title": f"{task.task_type.replace('_', ' ').title()}",
                "description": f"Status: {task.status}",
                "status": task.status,
                "router_id": task.config.get("router_id") if task.config else None,
                "router_identity": task.result.get("identity") if task.result else None,
                "user_id": None,
                "username": None,
                "created_at": task.created_at.isoformat()
            })

        # Get recent alerts
        alerts = self.db.query(AlertHistory).order_by(
            AlertHistory.created_at.desc()
        ).limit(5).all()

        for alert in alerts:
            router = self.db.query(Router).filter(Router.id == alert.router_id).first()
            activities.append({
                "id": alert.id,
                "type": "alert",
                "title": alert.title,
                "description": alert.message,
                "status": alert.status,
                "router_id": alert.router_id,
                "router_identity": router.identity if router else None,
                "user_id": None,
                "username": None,
                "created_at": alert.created_at.isoformat()
            })

        # Sort by date and limit
        activities.sort(key=lambda x: x["created_at"], reverse=True)
        return activities[:limit]

    def _get_upcoming_schedules(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get upcoming scheduled tasks"""
        schedules = self.db.query(ScheduledTask).filter(
            ScheduledTask.enabled == True,
            ScheduledTask.next_run != None
        ).order_by(ScheduledTask.next_run).limit(limit).all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "task_type": s.task_type,
                "enabled": s.enabled,
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "next_run": s.next_run.isoformat() if s.next_run else None,
                "last_status": s.last_status
            }
            for s in schedules
        ]

    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        active_alerts = self.db.query(AlertHistory).filter(
            AlertHistory.status == "active"
        ).all()

        severity_counts = Counter(a.severity for a in active_alerts)

        recent = self.db.query(AlertHistory).order_by(
            AlertHistory.created_at.desc()
        ).limit(5).all()

        return {
            "active_alerts": len(active_alerts),
            "critical_alerts": severity_counts.get("critical", 0),
            "warning_alerts": severity_counts.get("warning", 0),
            "info_alerts": severity_counts.get("info", 0),
            "recent_alerts": [
                {
                    "id": a.id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "created_at": a.created_at.isoformat()
                }
                for a in recent
            ]
        }

    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        scheduler = get_scheduler()

        # Count pending and running tasks
        pending = self.db.query(Task).filter(Task.status == "pending").count()
        running = self.db.query(Task).filter(Task.status == "running").count()

        return {
            "scheduler_running": scheduler.scheduler.running if scheduler._scheduler else False,
            "monitoring_active": True,  # Placeholder
            "websocket_connections": 0,  # Would need WebSocket manager reference
            "pending_tasks": pending,
            "running_tasks": running
        }

    def get_uptime_history(
        self,
        router_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get uptime history for a router"""
        since = datetime.utcnow() - timedelta(hours=hours)

        checks = self.db.query(HealthCheck).filter(
            HealthCheck.router_id == router_id,
            HealthCheck.checked_at > since
        ).order_by(HealthCheck.checked_at).all()

        router = self.db.query(Router).filter(Router.id == router_id).first()

        entries = [
            {
                "router_id": router_id,
                "identity": router.identity if router else None,
                "timestamp": c.checked_at.isoformat(),
                "is_online": c.is_online,
                "latency_ms": c.latency_ms
            }
            for c in checks
        ]

        total = len(checks)
        online = sum(1 for c in checks if c.is_online)
        uptime_pct = (online / total * 100) if total > 0 else 0

        return {
            "router_id": router_id,
            "entries": entries,
            "uptime_percentage": round(uptime_pct, 2),
            "start_time": since.isoformat(),
            "end_time": datetime.utcnow().isoformat()
        }

    def get_chart_data(self, chart_type: str) -> Dict[str, Any]:
        """Get data for a specific chart type"""
        if chart_type == "version_pie":
            data = self._get_version_distribution()
            return {
                "chart_type": "pie",
                "title": "RouterOS Version Distribution",
                "data": [
                    {"label": d["version"], "value": d["count"]}
                    for d in data
                ],
                "labels": [d["version"] for d in data]
            }

        elif chart_type == "model_bar":
            data = self._get_model_distribution()
            return {
                "chart_type": "bar",
                "title": "Router Model Distribution",
                "data": [
                    {"label": d["model"], "value": d["count"]}
                    for d in data
                ],
                "labels": [d["model"] for d in data]
            }

        elif chart_type == "status_doughnut":
            stats = self._get_router_stats()
            return {
                "chart_type": "doughnut",
                "title": "Router Status",
                "data": [
                    {"label": "Online", "value": stats["online"], "color": "#28a745"},
                    {"label": "Offline", "value": stats["offline"], "color": "#dc3545"},
                    {"label": "Updates", "value": stats["needs_update"], "color": "#ffc107"}
                ],
                "labels": ["Online", "Offline", "Updates"]
            }

        elif chart_type == "health_pie":
            health = self._get_health_summary()
            return {
                "chart_type": "pie",
                "title": "Health Status Distribution",
                "data": [
                    {"label": "Healthy", "value": health["healthy"], "color": "#28a745"},
                    {"label": "Warning", "value": health["warning"], "color": "#ffc107"},
                    {"label": "Critical", "value": health["critical"], "color": "#dc3545"},
                    {"label": "Unknown", "value": health["unknown"], "color": "#6c757d"}
                ],
                "labels": ["Healthy", "Warning", "Critical", "Unknown"]
            }

        return {"chart_type": chart_type, "title": "Unknown Chart", "data": [], "labels": []}

    def get_time_series(
        self,
        metric: str,
        router_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get time series data for a metric"""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(HealthCheck).filter(
            HealthCheck.checked_at > since
        )

        if router_id:
            query = query.filter(HealthCheck.router_id == router_id)

        checks = query.order_by(HealthCheck.checked_at).all()

        data = []
        for check in checks:
            value = None
            if metric == "latency":
                value = check.latency_ms
            elif metric == "cpu":
                value = check.cpu_usage
            elif metric == "memory":
                value = check.memory_usage
            elif metric == "disk":
                value = check.disk_usage

            if value is not None:
                data.append({
                    "timestamp": check.checked_at.isoformat(),
                    "value": value
                })

        return {
            "metric": metric,
            "router_id": router_id,
            "data": data,
            "start_time": since.isoformat(),
            "end_time": datetime.utcnow().isoformat()
        }
