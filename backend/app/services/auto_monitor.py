"""Automatic router monitoring service"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Set

from ..database import SessionLocal
from ..models.router import Router
from ..config import settings
from .mndp_service import discover_async

logger = logging.getLogger(__name__)

# Global flag for monitoring status
_monitoring_active = False
_monitoring_task: Optional[asyncio.Task] = None


async def check_all_routers():
    """
    Check online status of all routers using MNDP discovery.
    MNDP is the source of truth - if router responds to MNDP, it's online.
    """
    db = SessionLocal()
    try:
        routers = db.query(Router).all()
        if not routers:
            return

        logger.debug(f"Auto-monitoring: checking {len(routers)} routers via MNDP")

        # Run MNDP discovery to find all online MikroTik devices
        discovered = await discover_async(timeout=5)

        # Build set of discovered IPs for fast lookup
        discovered_ips: Set[str] = {d.ipv4_address for d in discovered if d.ipv4_address}

        logger.debug(f"MNDP discovered {len(discovered_ips)} devices: {discovered_ips}")

        # Update router statuses based on MNDP results
        updated = 0
        for router in routers:
            is_online = router.ip in discovered_ips

            if router.is_online != is_online:
                router.is_online = is_online
                updated += 1
                status = 'ONLINE (MNDP)' if is_online else 'OFFLINE'
                logger.info(f"Router {router.identity or router.ip} is now {status}")

            if is_online:
                router.last_seen = datetime.utcnow()

        if updated > 0:
            db.commit()
            logger.info(f"Auto-monitoring: updated {updated} router(s)")

    except Exception as e:
        logger.error(f"Auto-monitoring error: {e}")
    finally:
        db.close()


async def monitoring_loop(interval: int = 60):
    """Main monitoring loop"""
    global _monitoring_active

    logger.info(f"Auto-monitoring started (interval: {interval}s)")

    while _monitoring_active:
        try:
            await check_all_routers()
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")

        await asyncio.sleep(interval)

    logger.info("Auto-monitoring stopped")


def start_auto_monitoring(interval: int = 60):
    """Start the auto-monitoring background task"""
    global _monitoring_active, _monitoring_task

    if _monitoring_active:
        logger.warning("Auto-monitoring already running")
        return

    _monitoring_active = True

    loop = asyncio.get_event_loop()
    _monitoring_task = loop.create_task(monitoring_loop(interval))

    logger.info("Auto-monitoring task created")


def stop_auto_monitoring():
    """Stop the auto-monitoring background task"""
    global _monitoring_active, _monitoring_task

    _monitoring_active = False

    if _monitoring_task:
        _monitoring_task.cancel()
        _monitoring_task = None

    logger.info("Auto-monitoring stopped")


def is_monitoring_active() -> bool:
    """Check if monitoring is active"""
    return _monitoring_active
