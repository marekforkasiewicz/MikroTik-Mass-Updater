"""
MNDP (MikroTik Neighbor Discovery Protocol) Service
====================================================
Discovers MikroTik devices on the local network using Layer 2 broadcast.
MNDP uses UDP port 5678.
"""

import socket
import struct
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# MNDP constants
MNDP_PORT = 5678
MNDP_TIMEOUT = 5  # seconds
MNDP_BROADCAST = "255.255.255.255"

# TLV Type IDs used in MNDP
TLV_MAC_ADDRESS = 1
TLV_IDENTITY = 5
TLV_VERSION = 7
TLV_PLATFORM = 8
TLV_UPTIME = 10
TLV_SOFTWARE_ID = 11
TLV_BOARD = 12
TLV_UNPACK = 14
TLV_IPV6_ADDRESS = 15
TLV_INTERFACE_NAME = 16
TLV_IPV4_ADDRESS = 17


@dataclass
class DiscoveredRouter:
    """Represents a discovered MikroTik router via MNDP"""
    mac_address: str
    identity: str = ""
    version: str = ""
    platform: str = ""
    board: str = ""
    uptime: int = 0
    software_id: str = ""
    interface_name: str = ""
    ipv4_address: str = ""
    ipv6_address: str = ""
    discovered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mac_address": self.mac_address,
            "identity": self.identity,
            "version": self.version,
            "platform": self.platform,
            "board": self.board,
            "uptime_seconds": self.uptime,
            "uptime_formatted": self._format_uptime(),
            "software_id": self.software_id,
            "interface_name": self.interface_name,
            "ipv4_address": self.ipv4_address,
            "ipv6_address": self.ipv6_address,
            "discovered_at": self.discovered_at.isoformat()
        }

    def _format_uptime(self) -> str:
        """Format uptime in human-readable format"""
        if self.uptime == 0:
            return ""

        seconds = self.uptime
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return "".join(parts)


def parse_mndp_packet(data: bytes, source_ip: str) -> Optional[DiscoveredRouter]:
    """Parse an MNDP response packet"""
    try:
        if len(data) < 4:
            return None

        # Skip first 4 bytes (header)
        pos = 4
        router = DiscoveredRouter(mac_address="")

        while pos < len(data) - 4:
            # Read TLV: Type (2 bytes), Length (2 bytes), Value
            if pos + 4 > len(data):
                break

            tlv_type = struct.unpack(">H", data[pos:pos+2])[0]
            tlv_length = struct.unpack(">H", data[pos+2:pos+4])[0]
            pos += 4

            if pos + tlv_length > len(data):
                break

            value = data[pos:pos+tlv_length]
            pos += tlv_length

            # Parse based on TLV type
            if tlv_type == TLV_MAC_ADDRESS and tlv_length == 6:
                router.mac_address = ":".join(f"{b:02X}" for b in value)
            elif tlv_type == TLV_IDENTITY:
                router.identity = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_VERSION:
                router.version = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_PLATFORM:
                router.platform = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_BOARD:
                router.board = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_UPTIME and tlv_length == 4:
                router.uptime = struct.unpack(">I", value)[0]
            elif tlv_type == TLV_SOFTWARE_ID:
                router.software_id = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_INTERFACE_NAME:
                router.interface_name = value.decode("utf-8", errors="ignore").rstrip("\x00")
            elif tlv_type == TLV_IPV4_ADDRESS and tlv_length == 4:
                router.ipv4_address = socket.inet_ntoa(value)
            elif tlv_type == TLV_IPV6_ADDRESS and tlv_length == 16:
                router.ipv6_address = socket.inet_ntop(socket.AF_INET6, value)

        # Use source IP if no IP was in packet
        if not router.ipv4_address and source_ip:
            router.ipv4_address = source_ip

        if router.mac_address:
            return router
        return None

    except Exception as e:
        logger.debug(f"Failed to parse MNDP packet: {e}")
        return None


def discover_sync(timeout: float = MNDP_TIMEOUT, interface: str = None) -> List[DiscoveredRouter]:
    """
    Synchronous MNDP discovery.
    Listens for MNDP broadcasts from MikroTik devices.
    """
    discovered: Dict[str, DiscoveredRouter] = {}

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)  # Short timeout for responsive loop

        # Bind to MNDP port to receive broadcasts
        try:
            sock.bind(("0.0.0.0", MNDP_PORT))
        except OSError as e:
            logger.warning(f"Cannot bind to MNDP port {MNDP_PORT}: {e}")
            # Try binding to any port and send discovery request
            sock.bind(("0.0.0.0", 0))

        # Send discovery request (empty packet to broadcast)
        # MikroTik devices will respond to any packet on port 5678
        try:
            sock.sendto(b"\x00\x00\x00\x00", (MNDP_BROADCAST, MNDP_PORT))
        except Exception as e:
            logger.debug(f"Broadcast send failed: {e}")

        # Listen for responses
        start_time = datetime.utcnow()
        while True:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout:
                break

            try:
                data, addr = sock.recvfrom(1500)
                source_ip = addr[0]

                router = parse_mndp_packet(data, source_ip)
                if router and router.mac_address:
                    # Use MAC as unique key (same device might respond multiple times)
                    if router.mac_address not in discovered:
                        logger.info(f"Discovered: {router.identity} ({router.ipv4_address}) - {router.mac_address}")
                        discovered[router.mac_address] = router

            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"Receive error: {e}")
                continue

        sock.close()

    except Exception as e:
        logger.error(f"MNDP discovery error: {e}")

    return list(discovered.values())


async def discover_async(timeout: float = MNDP_TIMEOUT) -> List[DiscoveredRouter]:
    """
    Async wrapper for MNDP discovery.
    Runs the synchronous discovery in a thread pool.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, discover_sync, timeout)
    return result


class MNDPService:
    """Service for managing MNDP discovery"""

    def __init__(self):
        self._last_discovery: List[DiscoveredRouter] = []
        self._last_discovery_time: Optional[datetime] = None
        self._cache_seconds = 30  # Cache results for 30 seconds

    async def discover(self, timeout: float = MNDP_TIMEOUT, force: bool = False) -> List[DiscoveredRouter]:
        """
        Discover MikroTik devices on the network.

        Args:
            timeout: Discovery timeout in seconds
            force: Force new discovery even if cache is valid

        Returns:
            List of discovered routers
        """
        # Check cache
        if not force and self._last_discovery_time:
            cache_age = (datetime.utcnow() - self._last_discovery_time).total_seconds()
            if cache_age < self._cache_seconds:
                logger.debug(f"Using cached discovery results ({cache_age:.1f}s old)")
                return self._last_discovery

        logger.info(f"Starting MNDP discovery (timeout: {timeout}s)")
        self._last_discovery = await discover_async(timeout)
        self._last_discovery_time = datetime.utcnow()
        logger.info(f"MNDP discovery complete: found {len(self._last_discovery)} devices")

        return self._last_discovery

    def get_cached(self) -> List[DiscoveredRouter]:
        """Get last discovery results without triggering new scan"""
        return self._last_discovery

    def clear_cache(self):
        """Clear cached discovery results"""
        self._last_discovery = []
        self._last_discovery_time = None


# Singleton instance
_mndp_service: Optional[MNDPService] = None


def get_mndp_service() -> MNDPService:
    """Get the MNDP service singleton"""
    global _mndp_service
    if _mndp_service is None:
        _mndp_service = MNDPService()
    return _mndp_service
