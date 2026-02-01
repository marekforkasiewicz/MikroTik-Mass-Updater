"""Router service for MikroTik operations"""

import logging
import socket
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import librouteros
from librouteros.query import Key

from ..core.constants import (
    MIN_CONNECTION_TIMEOUT, MAX_RETRY_ATTEMPTS, RETRY_DELAY_SECONDS,
    DEFAULT_API_PORT
)
from ..core.enums import RouterOSCommand

logger = logging.getLogger(__name__)


@dataclass
class HostInfo:
    """Host connection information"""
    ip: str
    port: int = 8728
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class RouterInfo:
    """Collected information about a router"""
    ip: str
    identity: str = "N/A"
    model: str = "N/A"
    os_version: str = "N/A"
    current_firmware: str = "N/A"
    upgrade_firmware: str = "N/A"
    update_channel: str = "N/A"
    installed_version: str = "N/A"
    latest_version: str = "N/A"
    uptime: str = "N/A"
    memory_total_mb: Optional[int] = None
    architecture: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


class RouterService:
    """Service for router operations via API"""

    @staticmethod
    def parse_host_line(line: str, default_port: int = DEFAULT_API_PORT) -> Optional[HostInfo]:
        """Parse a single line from IP list file."""
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            return None

        try:
            parts = stripped_line.split('|')
            ip_port_str = parts[0]

            if not ip_port_str:
                return None

            ip_port_parts = ip_port_str.split(':')
            ip = ip_port_parts[0]

            if not ip:
                return None

            port_str = ip_port_parts[1] if len(ip_port_parts) > 1 else str(default_port)
            port = int(port_str)

            if not (1 <= port <= 65535):
                logger.warning(f"Port number {port} out of range for line: {stripped_line}")
                return None

            username = parts[1] if len(parts) > 1 else None
            password = parts[2] if len(parts) > 2 else None

            return HostInfo(ip=ip, port=port, username=username, password=password)

        except (ValueError, IndexError) as e:
            logger.warning(f"Skipping malformed line: '{stripped_line}'. Error: {e}")
            return None

    @staticmethod
    def parse_host_file(content: str, default_port: int = DEFAULT_API_PORT) -> List[HostInfo]:
        """Parse content of host list file."""
        hosts = []
        for line in content.split('\n'):
            host = RouterService.parse_host_line(line, default_port)
            if host:
                hosts.append(host)
        return hosts

    @staticmethod
    def connect(
        host: HostInfo,
        default_username: str,
        default_password: str,
        timeout: int = MIN_CONNECTION_TIMEOUT
    ) -> Any:
        """Establish connection to MikroTik router using librouteros."""
        username = host.username or default_username
        password = host.password or default_password
        effective_timeout = max(MIN_CONNECTION_TIMEOUT, timeout)

        api = librouteros.connect(
            host=host.ip,
            username=username,
            password=password,
            port=host.port,
            timeout=effective_timeout
        )
        return api

    @staticmethod
    def execute_with_retry(
        api: Any,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = MAX_RETRY_ATTEMPTS,
        retry_delay: float = RETRY_DELAY_SECONDS
    ) -> List[Dict[str, Any]]:
        """Execute RouterOS API command with automatic retry on failure."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                if params is not None:
                    return list(api(command, **params))
                return list(api(command))
            except (TimeoutError, socket.error) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue

        raise last_exception

    @staticmethod
    def get_router_info(api: Any, ip: str) -> RouterInfo:
        """Gather comprehensive router information."""
        info = RouterInfo(ip=ip)

        try:
            # Get Identity
            identity_response = list(api.path('/system/identity').select('name'))
            if identity_response:
                info.identity = identity_response[0].get('name', 'N/A')
        except Exception as e:
            logger.debug(f"Identity query failed for {ip}: {e}")

        try:
            # Get Routerboard info
            rb_response = list(api.path('/system/routerboard').select(
                'board-name', 'current-firmware', 'upgrade-firmware'
            ))
            if rb_response:
                rb = rb_response[0]
                info.model = rb.get('board-name', rb.get('model', 'N/A'))
                info.current_firmware = rb.get('current-firmware', 'N/A')
                info.upgrade_firmware = rb.get('upgrade-firmware', 'N/A')
        except Exception as e:
            logger.debug(f"Routerboard query failed for {ip}: {e}")

        try:
            # Get System Resource
            res_response = list(api.path('/system/resource').select('version', 'uptime', 'total-memory', 'architecture-name'))
            if res_response:
                res = res_response[0]
                info.os_version = res.get('version', 'N/A')
                info.uptime = res.get('uptime', 'N/A')
                total_mem = int(res.get('total-memory', 0))
                info.memory_total_mb = total_mem // (1024 * 1024) if total_mem > 0 else None
                info.architecture = res.get('architecture-name')
        except Exception as e:
            logger.debug(f"Resource query failed for {ip}: {e}")

        try:
            # Get Package Update Info
            update_response = list(api.path('/system/package/update').select(
                'channel', 'installed-version', 'latest-version', 'status'
            ))
            if update_response:
                upd = update_response[0]
                info.update_channel = upd.get('channel', upd.get('status', 'N/A'))
                info.installed_version = upd.get('installed-version', 'N/A')
                info.latest_version = upd.get('latest-version', 'N/A')
        except Exception as e:
            logger.debug(f"Package update query failed for {ip}: {e}")

        info.success = True
        return info

    @staticmethod
    def check_port(ip: str, port: int, timeout: int = 2) -> bool:
        """Check if a TCP port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Port check failed for {ip}:{port}: {e}")
            return False
