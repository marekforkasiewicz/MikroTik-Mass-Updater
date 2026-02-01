"""Automatic router monitoring service"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..database import SessionLocal
from ..models.router import Router
from ..config import settings

logger = logging.getLogger(__name__)

# Global flag for monitoring status
_monitoring_active = False
_monitoring_task: Optional[asyncio.Task] = None


async def ping_router(ip: str, timeout: float = 2.0) -> bool:
    """Ping a router to check if it's online"""
    try:
        # Try TCP connection to API port (faster than ICMP ping)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 8728),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        # Fallback: try SSH port
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 22),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False


async def check_all_routers():
    """Check online status of all routers"""
    db = SessionLocal()
    try:
        routers = db.query(Router).all()
        if not routers:
            return

        logger.debug(f"Auto-monitoring: checking {len(routers)} routers")

        # Check all routers concurrently
        tasks = []
        for router in routers:
            tasks.append(ping_router(router.ip))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update router statuses
        updated = 0
        for router, is_online in zip(routers, results):
            if isinstance(is_online, Exception):
                is_online = False

            if router.is_online != is_online:
                router.is_online = is_online
                updated += 1
                logger.info(f"Router {router.identity or router.ip} is now {'online' if is_online else 'offline'}")

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
