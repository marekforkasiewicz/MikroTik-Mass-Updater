"""
RouterOS API Integration Tests

These tests verify the RouterOS API operations work correctly.
Run against a real router or use mocks for CI/CD.

Usage:
    # Run with real router (set environment variables)
    ROUTEROS_HOST=192.168.1.1 ROUTEROS_USER=admin ROUTEROS_PASS=password pytest tests/test_routeros_api.py -v

    # Run with mocks only
    pytest tests/test_routeros_api.py -v -m "not integration"
"""

import os
import pytest
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock


# Test configuration from environment
TEST_ROUTER_HOST = os.getenv("ROUTEROS_HOST", "192.168.1.1")
TEST_ROUTER_PORT = int(os.getenv("ROUTEROS_PORT", "8728"))
TEST_ROUTER_USER = os.getenv("ROUTEROS_USER", "admin")
TEST_ROUTER_PASS = os.getenv("ROUTEROS_PASS", "")
TEST_ROUTER_REST_PORT = int(os.getenv("ROUTEROS_REST_PORT", "443"))

# Skip integration tests if no router configured
SKIP_INTEGRATION = not os.getenv("ROUTEROS_HOST")


@dataclass
class RouterOSResponse:
    """Standard response from RouterOS API operations"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class RouterOSAPIInterface:
    """
    Abstract interface for RouterOS API operations.
    This defines what operations we need to support.
    Both librouteros and REST implementations should follow this interface.
    """

    def connect(self, host: str, port: int, username: str, password: str, timeout: int = 10) -> bool:
        """Establish connection to router"""
        raise NotImplementedError

    def close(self) -> None:
        """Close connection"""
        raise NotImplementedError

    # System Information
    def get_identity(self) -> RouterOSResponse:
        """Get router identity/hostname"""
        raise NotImplementedError

    def get_resources(self) -> RouterOSResponse:
        """Get system resources (CPU, memory, uptime, etc.)"""
        raise NotImplementedError

    def get_routerboard(self) -> RouterOSResponse:
        """Get routerboard info (model, firmware, etc.)"""
        raise NotImplementedError

    # Update Management
    def get_update_status(self) -> RouterOSResponse:
        """Get current update channel and version info"""
        raise NotImplementedError

    def check_for_updates(self) -> RouterOSResponse:
        """Trigger update check"""
        raise NotImplementedError

    def install_updates(self) -> RouterOSResponse:
        """Install available updates (causes reboot)"""
        raise NotImplementedError

    # Firmware
    def upgrade_firmware(self) -> RouterOSResponse:
        """Upgrade routerboard firmware"""
        raise NotImplementedError

    # Scripts
    def list_scripts(self) -> RouterOSResponse:
        """List all scripts"""
        raise NotImplementedError

    def create_script(self, name: str, source: str, policy: List[str] = None) -> RouterOSResponse:
        """Create a new script"""
        raise NotImplementedError

    def run_script(self, name: str) -> RouterOSResponse:
        """Execute a script by name"""
        raise NotImplementedError

    def delete_script(self, script_id: str) -> RouterOSResponse:
        """Delete a script by ID"""
        raise NotImplementedError

    # Backups
    def list_cloud_backups(self) -> RouterOSResponse:
        """List cloud backups"""
        raise NotImplementedError

    def create_cloud_backup(self, name: str, password: str = None) -> RouterOSResponse:
        """Create and upload cloud backup"""
        raise NotImplementedError

    def get_export(self) -> RouterOSResponse:
        """Get configuration export"""
        raise NotImplementedError


# =============================================================================
# LIBROUTEROS IMPLEMENTATION (Current)
# =============================================================================

class LibrouterosAPI(RouterOSAPIInterface):
    """Current implementation using librouteros"""

    def __init__(self):
        self.api = None

    def connect(self, host: str, port: int, username: str, password: str, timeout: int = 10) -> bool:
        try:
            import librouteros
            self.api = librouteros.connect(
                host=host,
                username=username,
                password=password,
                port=port,
                timeout=timeout
            )
            return True
        except Exception as e:
            return False

    def close(self) -> None:
        if self.api:
            try:
                self.api.close()
            except:
                pass
            self.api = None

    def get_identity(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/identity'))
            if result:
                return RouterOSResponse(success=True, data=result[0])
            return RouterOSResponse(success=False, error="No identity data")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def get_resources(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/resource').select(
                'version', 'uptime', 'total-memory', 'free-memory',
                'cpu-load', 'architecture-name', 'board-name',
                'total-hdd-space', 'free-hdd-space'
            ))
            if result:
                return RouterOSResponse(success=True, data=result[0])
            return RouterOSResponse(success=False, error="No resource data")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def get_routerboard(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/routerboard').select(
                'current-firmware', 'upgrade-firmware', 'model', 'serial-number'
            ))
            if result:
                return RouterOSResponse(success=True, data=result[0])
            return RouterOSResponse(success=False, error="No routerboard data")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def get_update_status(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/package/update').select(
                'channel', 'status', 'installed-version', 'latest-version'
            ))
            if result:
                return RouterOSResponse(success=True, data=result[0])
            return RouterOSResponse(success=False, error="No update data")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def check_for_updates(self) -> RouterOSResponse:
        try:
            self.api.path('/system/package/update')('check-for-updates')
            time.sleep(2)  # Wait for check to complete
            return self.get_update_status()
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def install_updates(self) -> RouterOSResponse:
        try:
            self.api.path('/system/package/update')('install')
            return RouterOSResponse(success=True, data={"message": "Update initiated, router rebooting"})
        except Exception as e:
            # Connection reset is expected during reboot
            if "Connection" in str(e) or "reset" in str(e).lower():
                return RouterOSResponse(success=True, data={"message": "Router rebooting"})
            return RouterOSResponse(success=False, error=str(e))

    def upgrade_firmware(self) -> RouterOSResponse:
        try:
            self.api.path('/system/routerboard')('upgrade')
            return RouterOSResponse(success=True, data={"message": "Firmware upgrade initiated"})
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def list_scripts(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/script'))
            return RouterOSResponse(success=True, data=result)
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def create_script(self, name: str, source: str, policy: List[str] = None) -> RouterOSResponse:
        try:
            params = {'name': name, 'source': source}
            if policy:
                params['policy'] = ','.join(policy)
            self.api.path('/system/script').add(**params)
            return RouterOSResponse(success=True, data={"name": name})
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def run_script(self, name: str) -> RouterOSResponse:
        try:
            script_path = self.api.path('/system/script')
            # Run script by name using librouteros 3.x syntax
            tuple(script_path('run', number=name))
            return RouterOSResponse(success=True, data={"executed": name})
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def delete_script(self, script_id: str) -> RouterOSResponse:
        try:
            script_path = self.api.path('/system/script')
            tuple(script_path('remove', numbers=script_id))
            return RouterOSResponse(success=True)
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def list_cloud_backups(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/system/backup/cloud'))
            return RouterOSResponse(success=True, data=result)
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def create_cloud_backup(self, name: str, password: str = None) -> RouterOSResponse:
        try:
            params = {'name': name}
            if password:
                params['password'] = password
            self.api.path('/system/backup/cloud').call('upload-file', params)
            return RouterOSResponse(success=True, data={"name": name})
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def get_export(self) -> RouterOSResponse:
        try:
            result = list(self.api.path('/export'))
            if result:
                return RouterOSResponse(success=True, data=result[0])
            return RouterOSResponse(success=False, error="No export data")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))


# =============================================================================
# REST API IMPLEMENTATION (New - To be implemented)
# =============================================================================

class RestAPI(RouterOSAPIInterface):
    """New implementation using RouterOS REST API (RouterOS 7+)"""

    def __init__(self):
        self.session = None
        self.base_url = None
        self.auth = None

    def connect(self, host: str, port: int, username: str, password: str, timeout: int = 10) -> bool:
        try:
            import requests
            from requests.auth import HTTPBasicAuth

            self.base_url = f"https://{host}:{port}/rest"
            self.auth = HTTPBasicAuth(username, password)
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.verify = False  # RouterOS self-signed certs
            self.session.timeout = timeout

            # Test connection
            response = self.session.get(f"{self.base_url}/system/identity")
            return response.status_code == 200
        except Exception as e:
            return False

    def close(self) -> None:
        if self.session:
            self.session.close()
            self.session = None

    def _get(self, path: str) -> RouterOSResponse:
        """Generic GET request"""
        try:
            response = self.session.get(f"{self.base_url}{path}")
            if response.status_code == 200:
                data = response.json()
                # REST API returns list, get first item for single resources
                if isinstance(data, list) and len(data) == 1:
                    return RouterOSResponse(success=True, data=data[0])
                return RouterOSResponse(success=True, data=data)
            return RouterOSResponse(success=False, error=f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def _post(self, path: str, data: dict = None) -> RouterOSResponse:
        """Generic POST request"""
        try:
            response = self.session.post(f"{self.base_url}{path}", json=data or {})
            if response.status_code in (200, 201):
                return RouterOSResponse(success=True, data=response.json() if response.text else {})
            return RouterOSResponse(success=False, error=f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def _delete(self, path: str) -> RouterOSResponse:
        """Generic DELETE request"""
        try:
            response = self.session.delete(f"{self.base_url}{path}")
            if response.status_code in (200, 204):
                return RouterOSResponse(success=True)
            return RouterOSResponse(success=False, error=f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            return RouterOSResponse(success=False, error=str(e))

    def get_identity(self) -> RouterOSResponse:
        return self._get("/system/identity")

    def get_resources(self) -> RouterOSResponse:
        return self._get("/system/resource")

    def get_routerboard(self) -> RouterOSResponse:
        return self._get("/system/routerboard")

    def get_update_status(self) -> RouterOSResponse:
        return self._get("/system/package/update")

    def check_for_updates(self) -> RouterOSResponse:
        result = self._post("/system/package/update/check-for-updates")
        if result.success:
            time.sleep(2)
            return self.get_update_status()
        return result

    def install_updates(self) -> RouterOSResponse:
        return self._post("/system/package/update/install")

    def upgrade_firmware(self) -> RouterOSResponse:
        return self._post("/system/routerboard/upgrade")

    def list_scripts(self) -> RouterOSResponse:
        return self._get("/system/script")

    def create_script(self, name: str, source: str, policy: List[str] = None) -> RouterOSResponse:
        data = {"name": name, "source": source}
        if policy:
            data["policy"] = ",".join(policy)
        return self._post("/system/script/add", data)

    def run_script(self, name: str) -> RouterOSResponse:
        # First find the script
        scripts_result = self.list_scripts()
        if not scripts_result.success:
            return scripts_result

        script = next((s for s in scripts_result.data if s.get('name') == name), None)
        if not script:
            return RouterOSResponse(success=False, error=f"Script '{name}' not found")

        return self._post(f"/system/script/{script['.id']}/run")

    def delete_script(self, script_id: str) -> RouterOSResponse:
        return self._delete(f"/system/script/{script_id}")

    def list_cloud_backups(self) -> RouterOSResponse:
        return self._get("/system/backup/cloud")

    def create_cloud_backup(self, name: str, password: str = None) -> RouterOSResponse:
        data = {"name": name}
        if password:
            data["password"] = password
        return self._post("/system/backup/cloud/upload-file", data)

    def get_export(self) -> RouterOSResponse:
        return self._get("/export")


# =============================================================================
# UNIT TESTS (With Mocks)
# =============================================================================

class TestRouterOSAPIInterface:
    """Test the API interface contract"""

    def test_response_success(self):
        """Test successful response structure"""
        response = RouterOSResponse(success=True, data={"name": "Router1"})
        assert response.success is True
        assert response.data == {"name": "Router1"}
        assert response.error is None

    def test_response_error(self):
        """Test error response structure"""
        response = RouterOSResponse(success=False, error="Connection failed")
        assert response.success is False
        assert response.data is None
        assert response.error == "Connection failed"


class TestLibrouterosAPIMocked:
    """Test librouteros implementation with mocks"""

    @pytest.fixture
    def mock_api(self):
        """Create mocked librouteros API"""
        with patch('librouteros.connect') as mock_connect:
            mock_api_obj = MagicMock()
            mock_connect.return_value = mock_api_obj

            api = LibrouterosAPI()
            api.connect("192.168.1.1", 8728, "admin", "password")
            api.api = mock_api_obj

            yield api, mock_api_obj

    def test_get_identity(self, mock_api):
        """Test getting router identity"""
        api, mock = mock_api
        mock.path.return_value = [{"name": "TestRouter"}]

        result = api.get_identity()

        assert result.success is True
        assert result.data["name"] == "TestRouter"

    def test_get_resources(self, mock_api):
        """Test getting system resources"""
        api, mock = mock_api
        mock.path.return_value.select.return_value = [{
            "version": "7.22beta6",
            "uptime": "1d2h3m",
            "total-memory": 1073741824,
            "free-memory": 536870912,
            "cpu-load": 15,
            "architecture-name": "arm64"
        }]

        result = api.get_resources()

        assert result.success is True
        assert "version" in result.data
        assert "uptime" in result.data

    def test_get_routerboard(self, mock_api):
        """Test getting routerboard info"""
        api, mock = mock_api
        mock.path.return_value.select.return_value = [{
            "current-firmware": "7.22beta6",
            "upgrade-firmware": "7.22beta6",
            "model": "hAP ax^3"
        }]

        result = api.get_routerboard()

        assert result.success is True
        assert "current-firmware" in result.data
        assert "model" in result.data

    def test_get_update_status(self, mock_api):
        """Test getting update status"""
        api, mock = mock_api
        mock.path.return_value.select.return_value = [{
            "channel": "development",
            "status": "New version is available",
            "installed-version": "7.21rc6",
            "latest-version": "7.22beta6"
        }]

        result = api.get_update_status()

        assert result.success is True
        assert result.data["channel"] == "development"
        assert result.data["installed-version"] == "7.21rc6"
        assert result.data["latest-version"] == "7.22beta6"

    def test_list_scripts(self, mock_api):
        """Test listing scripts"""
        api, mock = mock_api
        mock.path.return_value = [
            {".id": "*1", "name": "script1", "source": "log info test"},
            {".id": "*2", "name": "script2", "source": "beep"}
        ]

        result = api.list_scripts()

        assert result.success is True
        assert len(result.data) == 2

    def test_connection_error(self, mock_api):
        """Test handling connection errors"""
        api, mock = mock_api
        mock.path.side_effect = Exception("Connection refused")

        result = api.get_identity()

        assert result.success is False
        assert "Connection refused" in result.error


class TestRestAPIMocked:
    """Test REST API implementation with mocks"""

    @pytest.fixture
    def mock_rest_api(self):
        """Create mocked REST API"""
        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            api = RestAPI()
            api.session = mock_session
            api.base_url = "https://192.168.1.1:443/rest"

            yield api, mock_session

    def test_get_identity(self, mock_rest_api):
        """Test getting router identity via REST"""
        api, mock = mock_rest_api
        mock.get.return_value.status_code = 200
        mock.get.return_value.json.return_value = [{"name": "TestRouter"}]

        result = api.get_identity()

        assert result.success is True
        assert result.data["name"] == "TestRouter"
        mock.get.assert_called_with("https://192.168.1.1:443/rest/system/identity")

    def test_get_resources(self, mock_rest_api):
        """Test getting resources via REST"""
        api, mock = mock_rest_api
        mock.get.return_value.status_code = 200
        mock.get.return_value.json.return_value = [{
            "version": "7.22beta6",
            "uptime": "1d2h3m",
            "cpu-load": 15
        }]

        result = api.get_resources()

        assert result.success is True
        assert result.data["version"] == "7.22beta6"

    def test_check_for_updates(self, mock_rest_api):
        """Test triggering update check via REST"""
        api, mock = mock_rest_api

        # Mock POST for check-for-updates
        mock.post.return_value.status_code = 200
        mock.post.return_value.json.return_value = {}
        mock.post.return_value.text = ""

        # Mock GET for status after check
        mock.get.return_value.status_code = 200
        mock.get.return_value.json.return_value = [{
            "channel": "stable",
            "installed-version": "7.21.2",
            "latest-version": "7.21.2"
        }]

        result = api.check_for_updates()

        assert result.success is True

    def test_create_script(self, mock_rest_api):
        """Test creating a script via REST"""
        api, mock = mock_rest_api
        mock.post.return_value.status_code = 201
        mock.post.return_value.json.return_value = {".id": "*1", "name": "test_script"}

        result = api.create_script("test_script", ":log info test", ["read", "write"])

        assert result.success is True
        mock.post.assert_called_once()

    def test_http_error_handling(self, mock_rest_api):
        """Test handling HTTP errors"""
        api, mock = mock_rest_api
        mock.get.return_value.status_code = 401
        mock.get.return_value.text = "Unauthorized"

        result = api.get_identity()

        assert result.success is False
        assert "401" in result.error


# =============================================================================
# INTEGRATION TESTS (Against real router)
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="No router configured for integration tests")
class TestLibrouterosIntegration:
    """Integration tests with real router using librouteros"""

    @pytest.fixture
    def api(self):
        """Create real API connection"""
        api = LibrouterosAPI()
        connected = api.connect(
            TEST_ROUTER_HOST,
            TEST_ROUTER_PORT,
            TEST_ROUTER_USER,
            TEST_ROUTER_PASS
        )
        assert connected, "Failed to connect to router"
        yield api
        api.close()

    def test_get_identity(self, api):
        """Test getting identity from real router"""
        result = api.get_identity()

        assert result.success is True
        assert "name" in result.data
        print(f"Router identity: {result.data['name']}")

    def test_get_resources(self, api):
        """Test getting resources from real router"""
        result = api.get_resources()

        assert result.success is True
        assert "version" in result.data
        assert "uptime" in result.data
        print(f"RouterOS version: {result.data['version']}")
        print(f"Uptime: {result.data['uptime']}")

    def test_get_routerboard(self, api):
        """Test getting routerboard info from real router"""
        result = api.get_routerboard()

        assert result.success is True
        assert "current-firmware" in result.data
        print(f"Firmware: {result.data['current-firmware']}")
        print(f"Model: {result.data.get('model', 'N/A')}")

    def test_get_update_status(self, api):
        """Test getting update status from real router"""
        result = api.get_update_status()

        assert result.success is True
        print(f"Channel: {result.data.get('channel', 'N/A')}")
        print(f"Installed: {result.data.get('installed-version', 'N/A')}")
        print(f"Latest: {result.data.get('latest-version', 'N/A')}")

    def test_list_scripts(self, api):
        """Test listing scripts from real router"""
        result = api.list_scripts()

        assert result.success is True
        print(f"Scripts count: {len(result.data)}")

    def test_script_lifecycle(self, api):
        """Test creating, running, and deleting a script"""
        script_name = "_test_script_mikrotik_updater"
        script_source = ':log info "Test script executed"'

        # Create script
        create_result = api.create_script(script_name, script_source, ["read", "write", "test"])
        assert create_result.success is True, f"Failed to create script: {create_result.error}"

        try:
            # Run script
            run_result = api.run_script(script_name)
            assert run_result.success is True, f"Failed to run script: {run_result.error}"

            # Find script ID for deletion
            list_result = api.list_scripts()
            script = next((s for s in list_result.data if s.get('name') == script_name), None)
            assert script is not None, "Created script not found"

            # Delete script
            delete_result = api.delete_script(script['.id'])
            assert delete_result.success is True, f"Failed to delete script: {delete_result.error}"

        except Exception as e:
            # Cleanup on failure
            list_result = api.list_scripts()
            script = next((s for s in list_result.data if s.get('name') == script_name), None)
            if script:
                api.delete_script(script['.id'])
            raise e


@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="No router configured for integration tests")
class TestRestAPIIntegration:
    """Integration tests with real router using REST API"""

    @pytest.fixture
    def api(self):
        """Create real REST API connection"""
        api = RestAPI()
        connected = api.connect(
            TEST_ROUTER_HOST,
            TEST_ROUTER_REST_PORT,
            TEST_ROUTER_USER,
            TEST_ROUTER_PASS
        )
        if not connected:
            pytest.skip("REST API not available (RouterOS 7+ required with www-ssl enabled)")
        yield api
        api.close()

    def test_get_identity(self, api):
        """Test getting identity via REST"""
        result = api.get_identity()

        assert result.success is True
        assert "name" in result.data
        print(f"Router identity (REST): {result.data['name']}")

    def test_get_resources(self, api):
        """Test getting resources via REST"""
        result = api.get_resources()

        assert result.success is True
        assert "version" in result.data
        print(f"RouterOS version (REST): {result.data['version']}")

    def test_get_routerboard(self, api):
        """Test getting routerboard via REST"""
        result = api.get_routerboard()

        assert result.success is True
        print(f"Firmware (REST): {result.data.get('current-firmware', 'N/A')}")

    def test_get_update_status(self, api):
        """Test getting update status via REST"""
        result = api.get_update_status()

        assert result.success is True
        print(f"Channel (REST): {result.data.get('channel', 'N/A')}")


# =============================================================================
# COMPARISON TESTS (Both APIs should return same data)
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="No router configured for integration tests")
class TestAPIComparison:
    """Test that both APIs return consistent data"""

    @pytest.fixture
    def both_apis(self):
        """Create both API connections"""
        lib_api = LibrouterosAPI()
        rest_api = RestAPI()

        lib_connected = lib_api.connect(
            TEST_ROUTER_HOST, TEST_ROUTER_PORT,
            TEST_ROUTER_USER, TEST_ROUTER_PASS
        )
        rest_connected = rest_api.connect(
            TEST_ROUTER_HOST, TEST_ROUTER_REST_PORT,
            TEST_ROUTER_USER, TEST_ROUTER_PASS
        )

        if not lib_connected:
            pytest.skip("librouteros connection failed")
        if not rest_connected:
            pytest.skip("REST API connection failed")

        yield lib_api, rest_api

        lib_api.close()
        rest_api.close()

    def test_identity_matches(self, both_apis):
        """Test that identity is same from both APIs"""
        lib_api, rest_api = both_apis

        lib_result = lib_api.get_identity()
        rest_result = rest_api.get_identity()

        assert lib_result.success and rest_result.success
        assert lib_result.data["name"] == rest_result.data["name"]

    def test_version_matches(self, both_apis):
        """Test that version is same from both APIs"""
        lib_api, rest_api = both_apis

        lib_result = lib_api.get_resources()
        rest_result = rest_api.get_resources()

        assert lib_result.success and rest_result.success
        assert lib_result.data["version"] == rest_result.data["version"]

    def test_firmware_matches(self, both_apis):
        """Test that firmware info is same from both APIs"""
        lib_api, rest_api = both_apis

        lib_result = lib_api.get_routerboard()
        rest_result = rest_api.get_routerboard()

        assert lib_result.success and rest_result.success
        assert lib_result.data["current-firmware"] == rest_result.data["current-firmware"]


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
