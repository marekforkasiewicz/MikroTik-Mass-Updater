"""
RouterOS REST API Client

This module provides a REST API client for MikroTik RouterOS 7+.
It replaces librouteros with a simpler, dependency-free implementation
using only the standard requests library.

REST API is available in RouterOS 7+ and must be enabled:
    /ip/service/enable www-ssl
    /certificate/add name=https common-name=router
    /certificate/sign https
    /ip/service/set www-ssl certificate=https

Usage:
    from app.services.routeros_rest import RouterOSClient

    client = RouterOSClient("192.168.1.1", "admin", "password")
    if client.connect():
        identity = client.get_identity()
        resources = client.get_resources()
        client.close()
"""

import time
import logging
import urllib3
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
import requests
from requests.auth import HTTPBasicAuth

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


@dataclass
class RouterOSResponse:
    """Response from RouterOS REST API"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 0


class RouterOSException(Exception):
    """Base exception for RouterOS errors"""
    pass


class RouterOSConnectionError(RouterOSException):
    """Connection failed"""
    pass


class RouterOSTrapError(RouterOSException):
    """RouterOS returned an error (similar to librouteros TrapError)"""
    def __init__(self, message: str, category: str = None):
        self.message = message
        self.category = category
        super().__init__(message)


class RouterOSClient:
    """
    RouterOS REST API Client

    Provides methods to interact with MikroTik RouterOS via REST API.
    Designed as a drop-in replacement for librouteros.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        timeout: int = 10,
        verify_ssl: bool = False
    ):
        """
        Initialize RouterOS REST client.

        Args:
            host: Router IP address or hostname
            username: API username
            password: API password
            port: HTTPS port (default 443)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.base_url = f"https://{host}:{port}/rest"
        self.session: Optional[requests.Session] = None
        self.connected = False

    def connect(self) -> bool:
        """
        Establish connection to router.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.session = requests.Session()
            self.session.auth = HTTPBasicAuth(self.username, self.password)
            self.session.verify = self.verify_ssl
            self.session.timeout = self.timeout

            # Test connection by getting identity
            response = self.session.get(
                f"{self.base_url}/system/identity",
                timeout=self.timeout
            )

            if response.status_code == 200:
                self.connected = True
                logger.debug(f"Connected to {self.host} via REST API")
                return True

            logger.warning(f"Connection test failed: HTTP {response.status_code}")
            return False

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error connecting to {self.host}: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {self.host}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.host}: {e}")
            return False

    def close(self) -> None:
        """Close the connection"""
        if self.session:
            self.session.close()
            self.session = None
        self.connected = False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # =========================================================================
    # LOW-LEVEL API METHODS
    # =========================================================================

    def _request(
        self,
        method: str,
        path: str,
        data: Dict = None,
        params: Dict = None
    ) -> RouterOSResponse:
        """
        Make a REST API request.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (e.g., "/system/identity")
            data: Request body for POST/PUT/PATCH
            params: Query parameters

        Returns:
            RouterOSResponse with result
        """
        if not self.session:
            return RouterOSResponse(
                success=False,
                error="Not connected"
            )

        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )

            if response.status_code in (200, 201):
                result_data = response.json() if response.text else {}
                # REST API returns list for single items, normalize
                if isinstance(result_data, list) and len(result_data) == 1:
                    result_data = result_data[0]
                return RouterOSResponse(
                    success=True,
                    data=result_data,
                    status_code=response.status_code
                )

            if response.status_code == 204:
                return RouterOSResponse(
                    success=True,
                    data=None,
                    status_code=204
                )

            # Error response
            error_msg = response.text
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    error_msg = error_data['detail']
                elif 'message' in error_data:
                    error_msg = error_data['message']
            except:
                pass

            return RouterOSResponse(
                success=False,
                error=f"HTTP {response.status_code}: {error_msg}",
                status_code=response.status_code
            )

        except requests.exceptions.Timeout:
            return RouterOSResponse(
                success=False,
                error="Request timeout"
            )
        except requests.exceptions.ConnectionError as e:
            return RouterOSResponse(
                success=False,
                error=f"Connection error: {e}"
            )
        except Exception as e:
            return RouterOSResponse(
                success=False,
                error=str(e)
            )

    def get(self, path: str, params: Dict = None) -> RouterOSResponse:
        """GET request"""
        return self._request("GET", path, params=params)

    def post(self, path: str, data: Dict = None) -> RouterOSResponse:
        """POST request"""
        return self._request("POST", path, data=data)

    def put(self, path: str, data: Dict = None) -> RouterOSResponse:
        """PUT request"""
        return self._request("PUT", path, data=data)

    def patch(self, path: str, data: Dict = None) -> RouterOSResponse:
        """PATCH request"""
        return self._request("PATCH", path, data=data)

    def delete(self, path: str) -> RouterOSResponse:
        """DELETE request"""
        return self._request("DELETE", path)

    # =========================================================================
    # SYSTEM INFORMATION
    # =========================================================================

    def get_identity(self) -> Dict:
        """
        Get router identity.

        Returns:
            Dict with 'name' key

        Raises:
            RouterOSException on error
        """
        result = self.get("/system/identity")
        if result.success:
            return result.data
        raise RouterOSException(result.error)

    def set_identity(self, name: str) -> bool:
        """Set router identity"""
        result = self.patch("/system/identity", {"name": name})
        return result.success

    def get_resources(self) -> Dict:
        """
        Get system resources.

        Returns:
            Dict with version, uptime, cpu-load, memory, etc.
        """
        result = self.get("/system/resource")
        if result.success:
            return result.data
        raise RouterOSException(result.error)

    def get_routerboard(self) -> Dict:
        """
        Get routerboard information.

        Returns:
            Dict with model, firmware versions, serial number
        """
        result = self.get("/system/routerboard")
        if result.success:
            return result.data
        raise RouterOSException(result.error)

    # =========================================================================
    # UPDATES & FIRMWARE
    # =========================================================================

    def get_update_status(self) -> Dict:
        """
        Get update status.

        Returns:
            Dict with channel, installed-version, latest-version, status
        """
        result = self.get("/system/package/update")
        if result.success:
            return result.data
        raise RouterOSException(result.error)

    def check_for_updates(self, wait: bool = True, timeout: int = 30) -> Dict:
        """
        Trigger update check.

        Args:
            wait: Wait for check to complete
            timeout: Max seconds to wait

        Returns:
            Updated status dict
        """
        # Trigger check
        self.post("/system/package/update/check-for-updates")

        if not wait:
            return self.get_update_status()

        # Wait for check to complete
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            status = self.get_update_status()
            if 'checking' not in status.get('status', '').lower():
                return status

        return self.get_update_status()

    def install_updates(self) -> bool:
        """
        Install available updates.

        Note: This will reboot the router!

        Returns:
            True if command accepted (router will reboot)
        """
        result = self.post("/system/package/update/install")
        # Connection will be lost during reboot
        return result.success or "Connection" in str(result.error)

    def upgrade_firmware(self) -> bool:
        """
        Upgrade routerboard firmware.

        Note: Requires reboot after upgrade!

        Returns:
            True if command accepted
        """
        result = self.post("/system/routerboard/upgrade")
        return result.success

    # =========================================================================
    # SCRIPTS
    # =========================================================================

    def list_scripts(self) -> List[Dict]:
        """
        List all scripts.

        Returns:
            List of script dicts
        """
        result = self.get("/system/script")
        if result.success:
            data = result.data
            if isinstance(data, dict):
                return [data]
            return data if data else []
        raise RouterOSException(result.error)

    def get_script(self, script_id: str) -> Optional[Dict]:
        """Get script by ID"""
        result = self.get(f"/system/script/{script_id}")
        if result.success:
            return result.data
        return None

    def create_script(
        self,
        name: str,
        source: str,
        policy: List[str] = None,
        comment: str = None
    ) -> Dict:
        """
        Create a new script.

        Args:
            name: Script name
            source: Script content
            policy: List of policies (read, write, test, etc.)
            comment: Optional comment

        Returns:
            Created script dict with .id
        """
        data = {
            "name": name,
            "source": source
        }
        if policy:
            data["policy"] = ",".join(policy)
        if comment:
            data["comment"] = comment

        result = self.post("/system/script/add", data)
        if result.success:
            # REST API returns {'ret': '*1'} for add operations
            # Convert to librouteros format {'.id': '*1'}
            if isinstance(result.data, dict) and 'ret' in result.data:
                return {'.id': result.data['ret'], 'name': name}
            return result.data
        raise RouterOSException(result.error)

    def run_script(self, script_id: str = None, name: str = None) -> bool:
        """
        Run a script.

        Args:
            script_id: Script ID (preferred)
            name: Script name (will lookup ID)

        Returns:
            True if executed successfully
        """
        # REST API uses 'number' parameter for script reference
        number = name
        if script_id and not name:
            number = script_id

        if not number:
            raise RouterOSException("Either script_id or name is required")

        # Use POST /system/script/run with number parameter
        result = self.post("/system/script/run", {"number": number})
        return result.success

    def delete_script(self, script_id: str) -> bool:
        """Delete a script by ID"""
        result = self.delete(f"/system/script/{script_id}")
        return result.success

    # =========================================================================
    # BACKUPS
    # =========================================================================

    def list_cloud_backups(self) -> List[Dict]:
        """List cloud backups"""
        result = self.get("/system/backup/cloud")
        if result.success:
            data = result.data
            if isinstance(data, dict):
                return [data]
            return data if data else []
        raise RouterOSException(result.error)

    def create_cloud_backup(
        self,
        name: str = None,
        password: str = None
    ) -> bool:
        """
        Create and upload cloud backup.

        Args:
            name: Backup name (optional)
            password: Encryption password (optional)

        Returns:
            True if backup initiated
        """
        data = {}
        if name:
            data["name"] = name
        if password:
            data["password"] = password

        result = self.post("/system/backup/cloud/upload-file", data)
        return result.success

    def download_cloud_backup(self, backup_id: str) -> bool:
        """Download cloud backup to router"""
        result = self.post(f"/system/backup/cloud/{backup_id}/download-file")
        return result.success

    def delete_cloud_backup(self, backup_id: str) -> bool:
        """Delete a cloud backup"""
        result = self.delete(f"/system/backup/cloud/{backup_id}")
        return result.success

    def create_local_backup(self, name: str, password: str = None) -> bool:
        """
        Create local backup file.

        Args:
            name: Backup filename
            password: Encryption password

        Returns:
            True if backup created
        """
        data = {"name": name}
        if password:
            data["password"] = password

        result = self.post("/system/backup/save", data)
        return result.success

    def restore_local_backup(self, name: str, password: str = None) -> bool:
        """
        Restore from local backup file.

        Args:
            name: Backup filename
            password: Decryption password

        Returns:
            True if restore initiated
        """
        data = {"name": name}
        if password:
            data["password"] = password

        result = self.post("/system/backup/load", data)
        return result.success

    def get_export(self, hide_sensitive: bool = True) -> str:
        """
        Get configuration export.

        Args:
            hide_sensitive: Hide passwords

        Returns:
            Configuration export as string
        """
        params = {}
        if hide_sensitive:
            params["hide-sensitive"] = "true"

        result = self.get("/export", params=params)
        if result.success:
            return result.data
        raise RouterOSException(result.error)

    # =========================================================================
    # REBOOT & SHUTDOWN
    # =========================================================================

    def reboot(self) -> bool:
        """
        Reboot the router.

        Returns:
            True if command accepted
        """
        result = self.post("/system/reboot")
        return result.success or "Connection" in str(result.error)

    def shutdown(self) -> bool:
        """
        Shutdown the router.

        Returns:
            True if command accepted
        """
        result = self.post("/system/shutdown")
        return result.success or "Connection" in str(result.error)

    # =========================================================================
    # SERVICES
    # =========================================================================

    def get_services(self) -> List[Dict]:
        """List all IP services"""
        result = self.get("/ip/service")
        if result.success:
            return result.data if isinstance(result.data, list) else [result.data]
        raise RouterOSException(result.error)

    def enable_service(self, service_name: str) -> bool:
        """Enable a service by name"""
        services = self.get_services()
        service = next((s for s in services if s.get('name') == service_name), None)
        if not service:
            raise RouterOSException(f"Service '{service_name}' not found")

        result = self.patch(f"/ip/service/{service['.id']}", {"disabled": False})
        return result.success

    def disable_service(self, service_name: str) -> bool:
        """Disable a service by name"""
        services = self.get_services()
        service = next((s for s in services if s.get('name') == service_name), None)
        if not service:
            raise RouterOSException(f"Service '{service_name}' not found")

        result = self.patch(f"/ip/service/{service['.id']}", {"disabled": True})
        return result.success

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def path(self, *args) -> 'PathBuilder':
        """
        librouteros compatibility: Create a path builder.

        This provides a librouteros-like interface for those who prefer it.

        Usage:
            client.path('/system/identity')
            client.path('/system/script').select('name', 'source')
        """
        return PathBuilder(self, "/".join(arg.strip("/") for arg in args))

    def run_command(self, path: str, command: str, **kwargs) -> Any:
        """
        Run a RouterOS command.

        Args:
            path: API path (e.g., "/system/package/update")
            command: Command name (e.g., "check-for-updates")
            **kwargs: Command parameters

        Returns:
            Command result
        """
        endpoint = f"{path}/{command}"
        result = self.post(endpoint, kwargs if kwargs else None)
        if result.success:
            return result.data
        raise RouterOSException(result.error)


class PathBuilder:
    """
    librouteros compatibility: Path builder for fluent API.

    Allows using librouteros-style code:
        list(client.path('/system/script').select('name'))
    """

    def __init__(self, client: RouterOSClient, path: str):
        self.client = client
        self.path = "/" + path.strip("/")
        self._select_fields: List[str] = []
        self._where_conditions: Dict[str, Any] = {}

    def select(self, *fields) -> 'PathBuilder':
        """Select specific fields"""
        self._select_fields = list(fields)
        return self

    def where(self, **conditions) -> 'PathBuilder':
        """Filter results"""
        self._where_conditions.update(conditions)
        return self

    def __iter__(self):
        """Execute query and return results"""
        params = {}
        if self._select_fields:
            params[".proplist"] = ",".join(self._select_fields)
        if self._where_conditions:
            for key, value in self._where_conditions.items():
                params[f"?{key}"] = str(value)

        result = self.client.get(self.path, params)
        if result.success:
            data = result.data
            if isinstance(data, dict):
                yield data
            elif isinstance(data, list):
                yield from data
        else:
            raise RouterOSException(result.error)

    def __call__(self, command: str = None, **kwargs):
        """Execute command on path"""
        if command:
            endpoint = f"{self.path}/{command}"
            result = self.client.post(endpoint, kwargs if kwargs else None)
            if not result.success:
                raise RouterOSException(result.error)
            return result.data
        else:
            # Just get the path
            return list(self)

    def add(self, **kwargs) -> Dict:
        """Add new item"""
        result = self.client.post(f"{self.path}/add", kwargs)
        if result.success:
            # REST API returns {'ret': '*1'} for add operations
            if isinstance(result.data, dict) and 'ret' in result.data:
                return {'.id': result.data['ret'], **kwargs}
            return result.data
        raise RouterOSException(result.error)

    def remove(self, item_id: str) -> bool:
        """Remove item by ID"""
        result = self.client.delete(f"{self.path}/{item_id}")
        return result.success


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def connect(
    host: str,
    username: str,
    password: str,
    port: int = 443,
    timeout: int = 10
) -> RouterOSClient:
    """
    Connect to RouterOS (librouteros-compatible function).

    Usage:
        api = connect(host='192.168.1.1', username='admin', password='pass')
        identity = api.get_identity()
        api.close()
    """
    client = RouterOSClient(
        host=host,
        username=username,
        password=password,
        port=port,
        timeout=timeout
    )

    if client.connect():
        return client

    raise RouterOSConnectionError(f"Failed to connect to {host}:{port}")
