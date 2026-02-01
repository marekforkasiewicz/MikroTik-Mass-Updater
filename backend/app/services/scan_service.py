"""Scan service for network discovery"""

import logging
import subprocess
import socket
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass

# REST API client (replaces librouteros)
from .routeros_rest import RouterOSClient, RouterOSException

from ..core.constants import PING_TIMEOUT, PORT_CHECK_TIMEOUT, DEFAULT_API_PORT, SSH_PORT
from .router_service import HostInfo

# Default REST API port
DEFAULT_REST_PORT = 443

logger = logging.getLogger(__name__)


@dataclass
class QuickScanResult:
    """Result of a quick scan"""
    ip: str
    ping_ok: bool = False
    ping_ms: float = 0.0
    port_api_open: bool = False
    port_ssh_open: bool = False
    ros_version: Optional[str] = None
    identity: Optional[str] = None
    memory_total_mb: Optional[int] = None
    architecture: Optional[str] = None
    status: str = "Checking..."
    has_credentials: bool = False


@dataclass
class FullScanResult:
    """Result of a full scan"""
    ip: str
    identity: Optional[str] = None
    model: Optional[str] = None
    ros_version: Optional[str] = None
    firmware: Optional[str] = None
    upgrade_firmware: Optional[str] = None
    update_channel: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    uptime: Optional[str] = None
    memory_total_mb: Optional[int] = None
    architecture: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


class ScanService:
    """Service for network scanning operations"""

    @staticmethod
    def ping_host(ip: str, timeout: int = PING_TIMEOUT) -> Tuple[bool, float]:
        """
        Ping a host and return (success, latency_ms).

        Args:
            ip: IP address to ping
            timeout: Ping timeout in seconds

        Returns:
            Tuple of (success, latency in ms)
        """
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), ip],
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )

            if result.returncode == 0:
                output = result.stdout
                if 'time=' in output:
                    time_str = output.split('time=')[1].split()[0]
                    latency = float(time_str.replace('ms', ''))
                    return True, latency
                return True, 0.0
            return False, 0.0

        except subprocess.TimeoutExpired:
            return False, 0.0
        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {e}")
            return False, 0.0

    @staticmethod
    def check_port(ip: str, port: int, timeout: int = PORT_CHECK_TIMEOUT) -> bool:
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

    @staticmethod
    def quick_scan_host(
        host: HostInfo,
        default_username: Optional[str] = None,
        default_password: Optional[str] = None
    ) -> QuickScanResult:
        """
        Perform quick scan on a single host.

        Checks:
        - Ping reachability
        - API port (8728)
        - SSH port (22)
        - If credentials available, gets RouterOS version and identity
        """
        result = QuickScanResult(ip=host.ip)
        result.has_credentials = bool(
            (host.username or default_username) and
            (host.password or default_password)
        )

        # Ping check
        ping_ok, ping_ms = ScanService.ping_host(host.ip)
        result.ping_ok = ping_ok
        result.ping_ms = ping_ms

        if not ping_ok:
            result.status = "Offline"
            return result

        # Check ports
        result.port_api_open = ScanService.check_port(host.ip, host.port or DEFAULT_API_PORT)
        result.port_ssh_open = ScanService.check_port(host.ip, SSH_PORT)

        if not result.port_api_open:
            result.status = "Online (API closed)"
            return result

        if not result.has_credentials:
            result.status = "Online (no credentials)"
            return result

        # Try to get RouterOS info via REST API
        client = None
        try:
            username = host.username or default_username
            password = host.password or default_password

            client = RouterOSClient(
                host=host.ip,
                username=username,
                password=password,
                port=DEFAULT_REST_PORT,
                timeout=5
            )

            if not client.connect():
                result.status = "Online (REST API unavailable)"
                return result

            # Get identity
            try:
                identity_data = client.get_identity()
                result.identity = identity_data.get('name')
            except Exception:
                pass

            # Get version, memory and architecture
            try:
                res_data = client.get_resources()
                result.ros_version = res_data.get('version')
                total_mem = int(res_data.get('total-memory', 0))
                result.memory_total_mb = total_mem // (1024 * 1024) if total_mem > 0 else None
                result.architecture = res_data.get('architecture-name')
            except Exception:
                pass

            result.status = "Online"

        except Exception as e:
            error_msg = str(e)[:30]
            result.status = f"API error: {error_msg}"
            logger.debug(f"API connection failed for {host.ip}: {e}")

        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass

        return result

    @staticmethod
    def full_scan_host(
        host: HostInfo,
        default_username: str,
        default_password: str,
        timeout: int = 30
    ) -> FullScanResult:
        """Perform full scan on a single host to gather all router information."""
        result = FullScanResult(ip=host.ip)
        client = None

        try:
            username = host.username or default_username
            password = host.password or default_password

            client = RouterOSClient(
                host=host.ip,
                username=username,
                password=password,
                port=DEFAULT_REST_PORT,
                timeout=timeout
            )

            if not client.connect():
                result.error = "Failed to connect via REST API"
                return result

            # Get Identity
            try:
                identity_data = client.get_identity()
                result.identity = identity_data.get('name')
            except Exception as e:
                logger.debug(f"Identity query failed for {host.ip}: {e}")

            # Get Routerboard info
            try:
                rb = client.get_routerboard()
                result.model = rb.get('board-name', rb.get('model'))
                result.firmware = rb.get('current-firmware')
                result.upgrade_firmware = rb.get('upgrade-firmware')
            except Exception as e:
                logger.debug(f"Routerboard query failed for {host.ip}: {e}")

            # Get System Resource
            try:
                res = client.get_resources()
                result.ros_version = res.get('version')
                result.uptime = res.get('uptime')
                total_mem = int(res.get('total-memory', 0))
                result.memory_total_mb = total_mem // (1024 * 1024) if total_mem > 0 else None
                result.architecture = res.get('architecture-name')
            except Exception as e:
                logger.debug(f"Resource query failed for {host.ip}: {e}")

            # Get Package Update Info
            try:
                # Trigger update check and wait for result
                upd = client.check_for_updates(wait=True, timeout=10)
                result.update_channel = upd.get('channel')
                result.installed_version = upd.get('installed-version')
                result.latest_version = upd.get('latest-version')
                # Log status for debugging
                status = upd.get('status', '')
                if status:
                    logger.debug(f"Update status for {host.ip}: {status}")
            except Exception as e:
                logger.debug(f"Package update query failed for {host.ip}: {e}")

            result.success = True

        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)[:50]}"
            logger.debug(f"Full scan failed for {host.ip}: {e}")

        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass

        return result

    @staticmethod
    def scan_hosts_parallel(
        hosts: List[HostInfo],
        scan_func: Callable,
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        **kwargs
    ) -> List:
        """
        Scan multiple hosts in parallel.

        Args:
            hosts: List of hosts to scan
            scan_func: Function to call for each host
            max_workers: Maximum concurrent workers
            progress_callback: Optional callback(current, total, ip)
            **kwargs: Additional arguments to pass to scan_func

        Returns:
            List of scan results
        """
        results = []
        total = len(hosts)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scan_func, host, **kwargs): host
                for host in hosts
            }

            for i, future in enumerate(futures):
                host = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Scan failed for {host.ip}: {e}")

                if progress_callback:
                    progress_callback(i + 1, total, host.ip)

        # Sort by IP
        results.sort(key=lambda x: tuple(map(int, x.ip.split('.'))))
        return results
