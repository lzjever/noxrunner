"""
Comprehensive tests for HTTPSandboxBackend.

Tests all functionality of the HTTP backend implementation.
Note: These tests require mocking HTTP requests.
"""

import io
import json
import tarfile
from unittest.mock import Mock, patch

import pytest

from noxrunner.backend.http import HTTPSandboxBackend
from noxrunner.exceptions import NoxRunnerError, NoxRunnerHTTPError


class TestHTTPSandboxBackend:
    """Comprehensive tests for HTTPSandboxBackend."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://127.0.0.1:8080"
        self.backend = HTTPSandboxBackend(self.base_url, timeout=30)
        self.session_id = "test-session-http"

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_health_check_success(self, mock_urlopen):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b"OK"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.health_check()
        assert result is True

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_health_check_failure(self, mock_urlopen):
        """Test failed health check."""
        mock_urlopen.side_effect = Exception("Connection error")

        result = self.backend.health_check()
        assert result is False

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_create_sandbox(self, mock_urlopen):
        """Test creating sandbox."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {"podName": "test-pod", "expiresAt": "2026-01-01T00:00:00Z"}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.create_sandbox(
            self.session_id,
            ttl_seconds=300,
            image="test-image",
            cpu_limit="1",
            memory_limit="1Gi",
        )

        assert "podName" in result
        assert "expiresAt" in result

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_touch(self, mock_urlopen):
        """Test extending sandbox TTL."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.touch(self.session_id)
        assert result is True

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_exec(self, mock_urlopen):
        """Test executing command."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {
                "exitCode": 0,
                "stdout": "hello",
                "stderr": "",
                "durationMs": 100,
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.exec(self.session_id, ["echo", "hello"])

        assert result["exitCode"] == 0
        assert result["stdout"] == "hello"

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_exec_with_env(self, mock_urlopen):
        """Test executing command with environment variables."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {
                "exitCode": 0,
                "stdout": "test_value",
                "stderr": "",
                "durationMs": 100,
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.exec(
            self.session_id,
            ["echo", "$TEST_VAR"],
            env={"TEST_VAR": "test_value"},
        )

        assert result["exitCode"] == 0

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_upload_files(self, mock_urlopen):
        """Test uploading files."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        files = {
            "test1.txt": "Hello, World!",
            "test2.txt": b"Binary data",
        }

        result = self.backend.upload_files(self.session_id, files)

        assert result is True

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_download_files(self, mock_urlopen):
        """Test downloading files."""
        # Create tar archive
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="test.txt")
            info.size = 11
            tar.addfile(info, io.BytesIO(b"Hello World"))

        tar_data = tar_buffer.getvalue()

        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = tar_data
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.download_files(self.session_id)

        assert len(result) > 0
        assert result == tar_data

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_download_files_error(self, mock_urlopen):
        """Test downloading files with error."""
        mock_response = Mock()
        mock_response.getcode.return_value = 404
        mock_response.read.return_value = b"Not found"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(NoxRunnerHTTPError):
            self.backend.download_files(self.session_id)

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_delete_sandbox(self, mock_urlopen):
        """Test deleting sandbox."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.delete_sandbox(self.session_id)
        assert result is True

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_wait_for_pod_ready(self, mock_urlopen):
        """Test waiting for pod ready."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {
                "exitCode": 0,
                "stdout": "ready",
                "stderr": "",
                "durationMs": 100,
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.wait_for_pod_ready(self.session_id, timeout=5, interval=1)
        assert result is True

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_wait_for_pod_ready_timeout(self, mock_urlopen):
        """Test waiting for pod ready with timeout."""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {
                "exitCode": 1,
                "stdout": "",
                "stderr": "not ready",
                "durationMs": 100,
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.backend.wait_for_pod_ready(self.session_id, timeout=1, interval=0.5)
        assert result is False

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """Test HTTP error handling."""
        from urllib.error import HTTPError

        mock_error = HTTPError(
            url="http://127.0.0.1:8080/v1/sandboxes/test",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )
        mock_urlopen.side_effect = mock_error

        with pytest.raises(NoxRunnerHTTPError) as exc_info:
            self.backend.create_sandbox(self.session_id)

        assert exc_info.value.status_code == 500

    @patch("noxrunner.backend.http.urllib.request.urlopen")
    def test_network_error_handling(self, mock_urlopen):
        """Test network error handling."""
        from urllib.error import URLError

        mock_error = URLError("Network error")
        mock_urlopen.side_effect = mock_error

        with pytest.raises(NoxRunnerError) as exc_info:
            self.backend.create_sandbox(self.session_id)

        assert "Network error" in str(exc_info.value)
