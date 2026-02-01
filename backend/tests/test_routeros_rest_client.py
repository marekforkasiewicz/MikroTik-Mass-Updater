"""
Tests for the RouterOS REST API Client module.

Tests both unit tests (mocked) and integration tests (real router).
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'services'))
from routeros_rest import (
    RouterOSClient, RouterOSResponse, RouterOSException,
    RouterOSConnectionError, RouterOSTrapError, PathBuilder, connect
)


# Test configuration from environment
TEST_ROUTER_HOST = os.getenv("ROUTEROS_HOST", "192.168.1.1")
TEST_ROUTER_PORT = int(os.getenv("ROUTEROS_REST_PORT", "443"))
TEST_ROUTER_USER = os.getenv("ROUTEROS_USER", "admin")
TEST_ROUTER_PASS = os.getenv("ROUTEROS_PASS", "")

SKIP_INTEGRATION = not os.getenv("ROUTEROS_HOST")


class TestRouterOSResponse:
    """Test RouterOSResponse dataclass"""

    def test_success_response(self):
        """Test successful response"""
        resp = RouterOSResponse(success=True, data={"name": "Router"})
        assert resp.success is True
        assert resp.data == {"name": "Router"}
        assert resp.error is None

    def test_error_response(self):
        """Test error response"""
        resp = RouterOSResponse(success=False, error="Connection failed")
        assert resp.success is False
        assert resp.error == "Connection failed"

    def test_with_status_code(self):
        """Test response with status code"""
        resp = RouterOSResponse(success=True, data={}, status_code=200)
        assert resp.status_code == 200


class TestRouterOSClientMocked:
    """Test RouterOSClient with mocked requests"""

    @pytest.fixture
    def mock_session(self):
        """Create mocked requests session"""
        with patch('requests.Session') as mock_class:
            session = MagicMock()
            mock_class.return_value = session
            yield session

    @pytest.fixture
    def client(self, mock_session):
        """Create client with mocked session"""
        client = RouterOSClient("192.168.1.1", "admin", "password")
        client.session = mock_session
        client.connected = True
        return client

    def test_init(self):
        """Test client initialization"""
        client = RouterOSClient(
            host="192.168.1.1",
            username="admin",
            password="secret",
            port=8443,
            timeout=30
        )
        assert client.host == "192.168.1.1"
        assert client.port == 8443
        assert client.username == "admin"
        assert client.base_url == "https://192.168.1.1:8443/rest"
        assert client.timeout == 30

    def test_connect_success(self, mock_session):
        """Test successful connection"""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = {"name": "Router"}

        client = RouterOSClient("192.168.1.1", "admin", "password")
        result = client.connect()

        assert result is True
        assert client.connected is True

    def test_connect_failure(self, mock_session):
        """Test failed connection"""
        mock_session.get.return_value.status_code = 401

        client = RouterOSClient("192.168.1.1", "admin", "wrong")
        result = client.connect()

        assert result is False
        assert client.connected is False

    def test_get_identity(self, client, mock_session):
        """Test getting identity"""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = '{"name": "TestRouter"}'
        mock_session.request.return_value.json.return_value = {"name": "TestRouter"}

        identity = client.get_identity()

        assert identity["name"] == "TestRouter"

    def test_get_resources(self, client, mock_session):
        """Test getting resources"""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = '{"version": "7.22", "uptime": "1d"}'
        mock_session.request.return_value.json.return_value = {
            "version": "7.22",
            "uptime": "1d",
            "cpu-load": 15
        }

        resources = client.get_resources()

        assert resources["version"] == "7.22"
        assert "uptime" in resources

    def test_get_routerboard(self, client, mock_session):
        """Test getting routerboard info"""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = '{}'
        mock_session.request.return_value.json.return_value = {
            "current-firmware": "7.22beta6",
            "upgrade-firmware": "7.22beta6",
            "model": "hAP ax^3"
        }

        rb = client.get_routerboard()

        assert rb["current-firmware"] == "7.22beta6"
        assert rb["model"] == "hAP ax^3"

    def test_list_scripts(self, client, mock_session):
        """Test listing scripts"""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = '[]'
        mock_session.request.return_value.json.return_value = [
            {".id": "*1", "name": "script1"},
            {".id": "*2", "name": "script2"}
        ]

        scripts = client.list_scripts()

        assert len(scripts) == 2
        assert scripts[0]["name"] == "script1"

    def test_create_script(self, client, mock_session):
        """Test creating a script"""
        mock_session.request.return_value.status_code = 201
        mock_session.request.return_value.text = '{}'
        mock_session.request.return_value.json.return_value = {
            ".id": "*3",
            "name": "new_script"
        }

        result = client.create_script(
            name="new_script",
            source=":log info test",
            policy=["read", "write"]
        )

        assert result[".id"] == "*3"

    def test_run_script_by_id(self, client, mock_session):
        """Test running script by ID"""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = ''
        mock_session.request.return_value.json.return_value = {}

        result = client.run_script(script_id="*1")

        assert result is True

    def test_delete_script(self, client, mock_session):
        """Test deleting script"""
        mock_session.request.return_value.status_code = 204

        result = client.delete_script("*1")

        assert result is True

    def test_error_handling(self, client, mock_session):
        """Test error handling"""
        mock_session.request.return_value.status_code = 500
        mock_session.request.return_value.text = "Internal error"

        result = client._request("GET", "/test")

        assert result.success is False
        assert "500" in result.error

    def test_context_manager(self, mock_session):
        """Test context manager usage"""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = {"name": "Router"}

        with RouterOSClient("192.168.1.1", "admin", "pass") as client:
            assert client.connected is True

        # Should be closed after exiting context
        assert client.connected is False


class TestPathBuilder:
    """Test PathBuilder for librouteros compatibility"""

    @pytest.fixture
    def mock_client(self):
        """Create mocked client"""
        client = MagicMock(spec=RouterOSClient)
        return client

    def test_path_construction(self, mock_client):
        """Test path building"""
        path = PathBuilder(mock_client, "/system/script")
        assert path.path == "/system/script"

    def test_select_fields(self, mock_client):
        """Test field selection"""
        path = PathBuilder(mock_client, "/system/script").select("name", "source")
        assert path._select_fields == ["name", "source"]

    def test_iteration(self, mock_client):
        """Test iterating over results"""
        mock_client.get.return_value = RouterOSResponse(
            success=True,
            data=[{"name": "script1"}, {"name": "script2"}]
        )

        path = PathBuilder(mock_client, "/system/script")
        results = list(path)

        assert len(results) == 2

    def test_add(self, mock_client):
        """Test adding item"""
        mock_client.post.return_value = RouterOSResponse(
            success=True,
            data={".id": "*1", "name": "new"}
        )

        path = PathBuilder(mock_client, "/system/script")
        result = path.add(name="new", source="test")

        assert result[".id"] == "*1"

    def test_remove(self, mock_client):
        """Test removing item"""
        mock_client.delete.return_value = RouterOSResponse(success=True)

        path = PathBuilder(mock_client, "/system/script")
        result = path.remove("*1")

        assert result is True


class TestConnectFunction:
    """Test the connect() helper function"""

    def test_connect_success(self):
        """Test successful connect"""
        with patch.object(RouterOSClient, 'connect', return_value=True):
            api = connect("192.168.1.1", "admin", "pass")
            assert isinstance(api, RouterOSClient)

    def test_connect_failure(self):
        """Test failed connect raises exception"""
        with patch.object(RouterOSClient, 'connect', return_value=False):
            with pytest.raises(RouterOSConnectionError):
                connect("192.168.1.1", "admin", "wrong")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="No router configured")
class TestRouterOSClientIntegration:
    """Integration tests with real router"""

    @pytest.fixture
    def client(self):
        """Create real client"""
        client = RouterOSClient(
            host=TEST_ROUTER_HOST,
            username=TEST_ROUTER_USER,
            password=TEST_ROUTER_PASS,
            port=TEST_ROUTER_PORT
        )
        if not client.connect():
            pytest.skip("Could not connect to router")
        yield client
        client.close()

    def test_get_identity(self, client):
        """Test getting identity from real router"""
        identity = client.get_identity()
        assert "name" in identity
        print(f"Identity: {identity['name']}")

    def test_get_resources(self, client):
        """Test getting resources from real router"""
        resources = client.get_resources()
        assert "version" in resources
        assert "uptime" in resources
        print(f"Version: {resources['version']}")

    def test_get_routerboard(self, client):
        """Test getting routerboard from real router"""
        rb = client.get_routerboard()
        assert "current-firmware" in rb
        print(f"Firmware: {rb['current-firmware']}")

    def test_get_update_status(self, client):
        """Test getting update status"""
        status = client.get_update_status()
        assert "channel" in status or "installed-version" in status
        print(f"Update status: {status}")

    def test_list_scripts(self, client):
        """Test listing scripts"""
        scripts = client.list_scripts()
        assert isinstance(scripts, list)
        print(f"Scripts: {len(scripts)}")

    def test_script_lifecycle(self, client):
        """Test create, run, delete script"""
        script_name = "_test_rest_api_script"

        # Create
        script = client.create_script(
            name=script_name,
            source=':log info "REST API test"',
            policy=["read", "write", "test"]
        )
        assert ".id" in script
        script_id = script[".id"]

        try:
            # Run
            result = client.run_script(script_id=script_id)
            assert result is True

            # Delete
            deleted = client.delete_script(script_id)
            assert deleted is True

        except Exception as e:
            # Cleanup on failure
            client.delete_script(script_id)
            raise e

    def test_path_builder_compatibility(self, client):
        """Test librouteros-style path builder"""
        # Test iteration
        identity = list(client.path('/system/identity'))
        assert len(identity) == 1
        assert "name" in identity[0]

        # Test select
        resources = list(client.path('/system/resource').select('version', 'uptime'))
        assert len(resources) == 1

    def test_services(self, client):
        """Test service management"""
        services = client.get_services()
        assert isinstance(services, list)
        assert len(services) > 0
        print(f"Services: {[s.get('name') for s in services]}")


@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="No router configured")
class TestMigrationCompatibility:
    """Test that REST client is compatible with librouteros usage patterns"""

    @pytest.fixture
    def rest_client(self):
        """Create REST client"""
        client = RouterOSClient(
            host=TEST_ROUTER_HOST,
            username=TEST_ROUTER_USER,
            password=TEST_ROUTER_PASS,
            port=TEST_ROUTER_PORT
        )
        if not client.connect():
            pytest.skip("Could not connect to router")
        yield client
        client.close()

    @pytest.fixture
    def lib_client(self):
        """Create librouteros client"""
        import librouteros
        try:
            api = librouteros.connect(
                host=TEST_ROUTER_HOST,
                username=TEST_ROUTER_USER,
                password=TEST_ROUTER_PASS,
                port=8728,
                timeout=10
            )
            yield api
            api.close()
        except Exception as e:
            pytest.skip(f"Could not connect with librouteros: {e}")

    def test_identity_compatibility(self, rest_client, lib_client):
        """Test identity results match"""
        rest_identity = rest_client.get_identity()
        lib_identity = list(lib_client.path('/system/identity'))[0]

        assert rest_identity["name"] == lib_identity["name"]

    def test_resources_compatibility(self, rest_client, lib_client):
        """Test resources results match"""
        rest_resources = rest_client.get_resources()
        lib_resources = list(lib_client.path('/system/resource'))[0]

        assert rest_resources["version"] == lib_resources["version"]

    def test_routerboard_compatibility(self, rest_client, lib_client):
        """Test routerboard results match"""
        rest_rb = rest_client.get_routerboard()
        lib_rb = list(lib_client.path('/system/routerboard'))[0]

        assert rest_rb["current-firmware"] == lib_rb["current-firmware"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
