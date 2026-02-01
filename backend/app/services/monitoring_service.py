"""Monitoring service for continuous health checks"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import socket

from sqlalchemy.orm import Session

from ..models.monitoring import MonitoringConfig, HealthCheck, AlertHistory
from ..models.router import Router
from ..schemas.monitoring import MonitoringConfigCreate, MonitoringConfigUpdate
from ..core.events import EventType, event_bus

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring router health"""

    def __init__(self, db: Session):
        self.db = db
        self._failure_counts: Dict[int, int] = {}  # router_id -> consecutive failures

    # Config management
    def get_config(self, router_id: Optional[int] = None) -> Optional[MonitoringConfig]:
        """Get monitoring config for router or global default"""
        if router_id:
            config = self.db.query(MonitoringConfig).filter(
                MonitoringConfig.router_id == router_id
            ).first()
            if config:
                return config

        # Return global config
        return self.db.query(MonitoringConfig).filter(
            MonitoringConfig.is_global == True
        ).first()

    def create_config(self, config_data: MonitoringConfigCreate) -> MonitoringConfig:
        """Create monitoring config"""
        config = MonitoringConfig(
            router_id=config_data.router_id,
            is_global=config_data.router_id is None,
            ping_interval=config_data.ping_interval,
            port_check_interval=config_data.port_check_interval,
            full_health_interval=config_data.full_health_interval,
            ping_timeout=config_data.ping_timeout,
            ping_warning_latency=config_data.ping_warning_latency,
            ping_critical_latency=config_data.ping_critical_latency,
            cpu_warning_percent=config_data.cpu_warning_percent,
            cpu_critical_percent=config_data.cpu_critical_percent,
            memory_warning_percent=config_data.memory_warning_percent,
            memory_critical_percent=config_data.memory_critical_percent,
            disk_warning_percent=config_data.disk_warning_percent,
            disk_critical_percent=config_data.disk_critical_percent,
            check_ping=config_data.check_ping,
            check_api_port=config_data.check_api_port,
            check_ssh_port=config_data.check_ssh_port,
            check_resources=config_data.check_resources,
            check_updates=config_data.check_updates,
            alert_on_offline=config_data.alert_on_offline,
            alert_on_online=config_data.alert_on_online,
            offline_threshold=config_data.offline_threshold,
            enabled=config_data.enabled
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_config(
        self,
        config_id: int,
        config_data: MonitoringConfigUpdate
    ) -> Optional[MonitoringConfig]:
        """Update monitoring config"""
        config = self.db.query(MonitoringConfig).filter(
            MonitoringConfig.id == config_id
        ).first()
        if not config:
            return None

        update_data = config_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

        self.db.commit()
        self.db.refresh(config)
        return config

    def ensure_global_config(self) -> MonitoringConfig:
        """Ensure global config exists"""
        config = self.db.query(MonitoringConfig).filter(
            MonitoringConfig.is_global == True
        ).first()

        if not config:
            config = MonitoringConfig(is_global=True)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

        return config

    # Health checks
    async def check_router(self, router: Router, check_type: str = "ping") -> HealthCheck:
        """Perform health check on a router"""
        config = self.get_config(router.id) or self.ensure_global_config()

        health_check = HealthCheck(
            router_id=router.id,
            check_type=check_type,
            status="unknown"
        )

        try:
            if check_type == "ping":
                await self._do_ping_check(health_check, router, config)
            elif check_type == "port":
                await self._do_port_check(health_check, router, config)
            elif check_type == "full":
                await self._do_full_check(health_check, router, config)

            # Determine overall status
            health_check.status = self._determine_status(health_check, config)

            # Handle state changes
            await self._handle_state_change(router, health_check, config)

        except Exception as e:
            health_check.status = "unknown"
            health_check.details = {"error": str(e)}
            logger.error(f"Health check failed for {router.ip}: {e}")

        self.db.add(health_check)
        self.db.commit()
        self.db.refresh(health_check)

        return health_check

    async def _do_ping_check(
        self,
        health_check: HealthCheck,
        router: Router,
        config: MonitoringConfig
    ):
        """Perform ping check"""
        try:
            import aioping
            latency = await aioping.ping(router.ip, timeout=config.ping_timeout)
            health_check.is_online = True
            health_check.latency_ms = latency * 1000
        except Exception:
            health_check.is_online = False
            health_check.latency_ms = None

    async def _do_port_check(
        self,
        health_check: HealthCheck,
        router: Router,
        config: MonitoringConfig
    ):
        """Perform port check"""
        # Check API port
        if config.check_api_port:
            health_check.api_port_open = await self._check_port(router.ip, router.port)

        # Check SSH port
        if config.check_ssh_port:
            health_check.ssh_port_open = await self._check_port(router.ip, 22)

        health_check.is_online = health_check.api_port_open or health_check.ssh_port_open

    async def _do_full_check(
        self,
        health_check: HealthCheck,
        router: Router,
        config: MonitoringConfig
    ):
        """Perform full health check including resources"""
        # First do ping and port checks
        await self._do_ping_check(health_check, router, config)
        await self._do_port_check(health_check, router, config)

        if not health_check.is_online:
            return

        # Get resource info via API
        if config.check_resources:
            try:
                from .router_service import RouterService, HostInfo
                from ..config import settings

                host = HostInfo(
                    ip=router.ip,
                    port=router.port,
                    username=router.username,
                    password=router.password
                )
                api = RouterService.connect(
                    host,
                    default_username=settings.DEFAULT_USERNAME or "",
                    default_password=settings.DEFAULT_PASSWORD or "",
                    timeout=10
                )

                if api:
                    try:
                        # Get resource info
                        resources = list(api.path("/system/resource").select())
                        if resources:
                            res = resources[0]
                            health_check.cpu_usage = float(res.get("cpu-load", 0))

                            # Calculate memory usage
                            total_mem = int(res.get("total-memory", 0))
                            free_mem = int(res.get("free-memory", 0))
                            if total_mem > 0:
                                health_check.memory_usage = ((total_mem - free_mem) / total_mem) * 100
                                # Store total memory in router
                                router.memory_total_mb = total_mem // (1024 * 1024)

                            # Store architecture in router
                            arch = res.get("architecture-name")
                            if arch:
                                router.architecture = arch

                            # Calculate disk usage
                            total_disk = int(res.get("total-hdd-space", 0))
                            free_disk = int(res.get("free-hdd-space", 0))
                            if total_disk > 0:
                                health_check.disk_usage = ((total_disk - free_disk) / total_disk) * 100

                            health_check.uptime_seconds = self._parse_uptime(res.get("uptime", "0s"))

                    finally:
                        api.close()
            except Exception as e:
                health_check.details = {"resource_error": str(e)}

    async def _check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """Check if a port is open"""
        try:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            await asyncio.wait_for(
                loop.sock_connect(sock, (host, port)),
                timeout=timeout
            )
            sock.close()
            return True
        except Exception:
            return False

    def _determine_status(self, health_check: HealthCheck, config: MonitoringConfig) -> str:
        """Determine overall health status"""
        if not health_check.is_online:
            return "critical"

        status = "ok"

        # Check latency
        if health_check.latency_ms:
            if health_check.latency_ms >= config.ping_critical_latency:
                status = "critical"
            elif health_check.latency_ms >= config.ping_warning_latency:
                status = "warning"

        # Check CPU
        if health_check.cpu_usage is not None:
            if health_check.cpu_usage >= config.cpu_critical_percent:
                status = "critical"
            elif health_check.cpu_usage >= config.cpu_warning_percent and status != "critical":
                status = "warning"

        # Check memory
        if health_check.memory_usage is not None:
            if health_check.memory_usage >= config.memory_critical_percent:
                status = "critical"
            elif health_check.memory_usage >= config.memory_warning_percent and status != "critical":
                status = "warning"

        # Check disk
        if health_check.disk_usage is not None:
            if health_check.disk_usage >= config.disk_critical_percent:
                status = "critical"
            elif health_check.disk_usage >= config.disk_warning_percent and status != "critical":
                status = "warning"

        return status

    async def _handle_state_change(
        self,
        router: Router,
        health_check: HealthCheck,
        config: MonitoringConfig
    ):
        """Handle router state changes and create alerts"""
        was_online = router.is_online
        is_online = health_check.is_online

        if is_online:
            self._failure_counts[router.id] = 0

            # Router came back online
            if not was_online and config.alert_on_online:
                await self._create_alert(
                    router_id=router.id,
                    alert_type="router_online",
                    severity="info",
                    title=f"Router {router.identity or router.ip} is back online",
                    message=f"Router reconnected after being offline"
                )

            # Update router status
            router.is_online = True
            router.last_seen = datetime.utcnow()

        else:
            # Increment failure count
            self._failure_counts[router.id] = self._failure_counts.get(router.id, 0) + 1

            # Check if threshold reached
            if self._failure_counts[router.id] >= config.offline_threshold:
                if was_online and config.alert_on_offline:
                    await self._create_alert(
                        router_id=router.id,
                        alert_type="router_offline",
                        severity="critical",
                        title=f"Router {router.identity or router.ip} is offline",
                        message=f"Router unreachable after {config.offline_threshold} checks"
                    )

                router.is_online = False

        # Check for resource alerts
        if health_check.status in ["warning", "critical"]:
            await self._check_resource_alerts(router, health_check, config)

        self.db.commit()

    async def _check_resource_alerts(
        self,
        router: Router,
        health_check: HealthCheck,
        config: MonitoringConfig
    ):
        """Check and create resource-related alerts"""
        alerts = []

        if health_check.cpu_usage and health_check.cpu_usage >= config.cpu_critical_percent:
            alerts.append(("high_cpu", "critical", f"CPU usage at {health_check.cpu_usage:.1f}%"))
        elif health_check.cpu_usage and health_check.cpu_usage >= config.cpu_warning_percent:
            alerts.append(("high_cpu", "warning", f"CPU usage at {health_check.cpu_usage:.1f}%"))

        if health_check.memory_usage and health_check.memory_usage >= config.memory_critical_percent:
            alerts.append(("high_memory", "critical", f"Memory usage at {health_check.memory_usage:.1f}%"))
        elif health_check.memory_usage and health_check.memory_usage >= config.memory_warning_percent:
            alerts.append(("high_memory", "warning", f"Memory usage at {health_check.memory_usage:.1f}%"))

        if health_check.disk_usage and health_check.disk_usage >= config.disk_critical_percent:
            alerts.append(("high_disk", "critical", f"Disk usage at {health_check.disk_usage:.1f}%"))
        elif health_check.disk_usage and health_check.disk_usage >= config.disk_warning_percent:
            alerts.append(("high_disk", "warning", f"Disk usage at {health_check.disk_usage:.1f}%"))

        for alert_type, severity, message in alerts:
            await self._create_alert(
                router_id=router.id,
                alert_type=alert_type,
                severity=severity,
                title=f"{router.identity or router.ip}: {message}",
                message=message
            )

    async def _create_alert(
        self,
        router_id: int,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        details: Dict[str, Any] = None
    ):
        """Create an alert"""
        # Check for duplicate recent alert
        recent = self.db.query(AlertHistory).filter(
            AlertHistory.router_id == router_id,
            AlertHistory.alert_type == alert_type,
            AlertHistory.status == "active",
            AlertHistory.created_at > datetime.utcnow() - timedelta(minutes=5)
        ).first()

        if recent:
            return  # Don't create duplicate

        alert = AlertHistory(
            router_id=router_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details or {}
        )

        self.db.add(alert)
        self.db.commit()

        # Emit event for notification service
        await event_bus.emit_async(
            EventType.ALERT_CREATED,
            {
                "alert_id": alert.id,
                "alert_type": alert_type,
                "severity": severity,
                "title": title,
                "message": message,
                "router_id": router_id
            },
            router_id=router_id
        )

    def _parse_uptime(self, uptime_str: str) -> int:
        """Parse RouterOS uptime string to seconds"""
        total = 0
        parts = uptime_str.lower()

        import re
        weeks = re.search(r'(\d+)w', parts)
        days = re.search(r'(\d+)d', parts)
        hours = re.search(r'(\d+)h', parts)
        minutes = re.search(r'(\d+)m', parts)
        seconds = re.search(r'(\d+)s', parts)

        if weeks:
            total += int(weeks.group(1)) * 7 * 24 * 3600
        if days:
            total += int(days.group(1)) * 24 * 3600
        if hours:
            total += int(hours.group(1)) * 3600
        if minutes:
            total += int(minutes.group(1)) * 60
        if seconds:
            total += int(seconds.group(1))

        return total

    # Alert management
    def get_alerts(
        self,
        router_id: Optional[int] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[AlertHistory], int]:
        """Get alerts with filters"""
        query = self.db.query(AlertHistory)

        if router_id:
            query = query.filter(AlertHistory.router_id == router_id)
        if status:
            query = query.filter(AlertHistory.status == status)
        if severity:
            query = query.filter(AlertHistory.severity == severity)

        total = query.count()
        alerts = query.order_by(AlertHistory.created_at.desc()).offset(skip).limit(limit).all()
        return alerts, total

    def acknowledge_alerts(self, alert_ids: List[int], user_id: int) -> int:
        """Acknowledge alerts"""
        count = self.db.query(AlertHistory).filter(
            AlertHistory.id.in_(alert_ids),
            AlertHistory.status == "active"
        ).update({
            "status": "acknowledged",
            "acknowledged_at": datetime.utcnow(),
            "acknowledged_by": user_id
        }, synchronize_session=False)

        self.db.commit()
        return count

    def resolve_alerts(self, alert_ids: List[int]) -> int:
        """Resolve alerts"""
        count = self.db.query(AlertHistory).filter(
            AlertHistory.id.in_(alert_ids),
            AlertHistory.status.in_(["active", "acknowledged"])
        ).update({
            "status": "resolved",
            "resolved_at": datetime.utcnow()
        }, synchronize_session=False)

        self.db.commit()
        return count

    def get_health_history(
        self,
        router_id: int,
        check_type: Optional[str] = None,
        hours: int = 24
    ) -> List[HealthCheck]:
        """Get health check history for a router"""
        since = datetime.utcnow() - timedelta(hours=hours)
        query = self.db.query(HealthCheck).filter(
            HealthCheck.router_id == router_id,
            HealthCheck.checked_at > since
        )

        if check_type:
            query = query.filter(HealthCheck.check_type == check_type)

        return query.order_by(HealthCheck.checked_at.desc()).all()

    def get_monitoring_overview(self) -> Dict[str, Any]:
        """Get monitoring overview for all routers"""
        routers = self.db.query(Router).all()

        total = len(routers)
        online = sum(1 for r in routers if r.is_online)
        offline = total - online

        # Get active alerts count
        active_alerts = self.db.query(AlertHistory).filter(
            AlertHistory.status == "active"
        ).count()

        # Get recent health status per router
        router_statuses = []
        for router in routers:
            latest_check = self.db.query(HealthCheck).filter(
                HealthCheck.router_id == router.id
            ).order_by(HealthCheck.checked_at.desc()).first()

            active_router_alerts = self.db.query(AlertHistory).filter(
                AlertHistory.router_id == router.id,
                AlertHistory.status == "active"
            ).count()

            router_statuses.append({
                "router_id": router.id,
                "identity": router.identity,
                "ip": router.ip,
                "status": latest_check.status if latest_check else "unknown",
                "is_online": router.is_online,
                "latency_ms": latest_check.latency_ms if latest_check else None,
                "cpu_usage": latest_check.cpu_usage if latest_check else None,
                "memory_usage": latest_check.memory_usage if latest_check else None,
                "memory_total_mb": router.memory_total_mb,
                "architecture": router.architecture,
                "disk_usage": latest_check.disk_usage if latest_check else None,
                "uptime": router.uptime,
                "last_check": latest_check.checked_at if latest_check else None,
                "active_alerts": active_router_alerts
            })

        warning_count = sum(1 for s in router_statuses if s["status"] == "warning")
        critical_count = sum(1 for s in router_statuses if s["status"] == "critical")

        return {
            "total_routers": total,
            "online_routers": online,
            "offline_routers": offline,
            "warning_routers": warning_count,
            "critical_routers": critical_count,
            "active_alerts": active_alerts,
            "routers": router_statuses
        }
