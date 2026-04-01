"""RouterOS version checking API"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Annotated, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
import httpx
from ..core.deps import OperatorUser, require_permission
from ..core.permissions import Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/versions", tags=["versions"])

# Cache for versions (refresh every 5 minutes)
_versions_cache: Optional[Dict] = None
_cache_time: Optional[datetime] = None
CACHE_TTL = timedelta(minutes=5)

MIKROTIK_VERSION_URLS = {
    "stable": "https://upgrade.mikrotik.com/routeros/NEWESTa7.stable",
    "long-term": "https://upgrade.mikrotik.com/routeros/NEWESTa7.long-term",
    "testing": "https://upgrade.mikrotik.com/routeros/NEWESTa7.testing",
    "development": "https://upgrade.mikrotik.com/routeros/NEWESTa7.development",
}

CHANNEL_INFO = {
    "stable": {
        "name": "Stable",
        "description": "Production-ready stable releases",
        "color": "success"
    },
    "long-term": {
        "name": "Long-term",
        "description": "Extended support releases (LTS)",
        "color": "info"
    },
    "testing": {
        "name": "Testing",
        "description": "Beta testing releases",
        "color": "warning"
    },
    "development": {
        "name": "Development",
        "description": "Alpha development releases",
        "color": "danger"
    },
}


async def fetch_version(client: httpx.AsyncClient, channel: str, url: str) -> Dict:
    """Fetch version info for a single channel"""
    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()

        # Parse response: "7.21.2 1769680488"
        parts = response.text.strip().split()
        version = parts[0] if parts else "unknown"

        # Convert timestamp to date if available
        release_date = None
        if len(parts) > 1:
            try:
                timestamp = int(parts[1])
                release_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        return {
            "channel": channel,
            "version": version,
            "release_date": release_date,
            "available": True,
            **CHANNEL_INFO.get(channel, {})
        }
    except Exception as e:
        logger.warning(f"Failed to fetch {channel} version: {e}")
        return {
            "channel": channel,
            "version": "N/A",
            "release_date": None,
            "available": False,
            "error": str(e),
            **CHANNEL_INFO.get(channel, {})
        }


async def fetch_all_versions() -> Dict:
    """Fetch all RouterOS versions from MikroTik"""
    global _versions_cache, _cache_time

    # Check cache
    if _versions_cache and _cache_time:
        if datetime.now() - _cache_time < CACHE_TTL:
            return _versions_cache

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_version(client, channel, url)
            for channel, url in MIKROTIK_VERSION_URLS.items()
        ]
        results = await asyncio.gather(*tasks)

    versions = {r["channel"]: r for r in results}

    # Update cache
    _versions_cache = {
        "versions": versions,
        "fetched_at": datetime.now().isoformat(),
        "cache_ttl_seconds": CACHE_TTL.total_seconds()
    }
    _cache_time = datetime.now()

    return _versions_cache


@router.get("")
async def get_routeros_versions(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_VERSIONS))]
):
    """Get current RouterOS versions for all channels from MikroTik"""
    try:
        return await fetch_all_versions()
    except Exception as e:
        logger.error(f"Error fetching versions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch versions: {str(e)}")


@router.get("/refresh")
async def refresh_versions(current_user: OperatorUser):
    """Force refresh versions cache"""
    global _versions_cache, _cache_time
    _versions_cache = None
    _cache_time = None
    return await fetch_all_versions()


def get_cached_versions() -> Dict:
    """
    Get cached versions synchronously (for use in background tasks).
    Returns dict mapping channel -> version info, or empty dict if cache empty.
    """
    if _versions_cache and "versions" in _versions_cache:
        return _versions_cache["versions"]
    return {}
