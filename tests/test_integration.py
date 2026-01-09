"""
Integration tests for NoxRunner backends.

This file contains both local and HTTP backend tests:
- Local backend tests (TestLocalBackendIntegration, test_client_local_mode):
  Run with `make test` - no external services needed
- HTTP backend tests (TestHTTPSandboxBackendIntegration, test_client_http_mode):
  Run with `make test-integration` - requires real HTTP backend service

To run all tests:
    make test              # Local backend tests only
    make test-integration  # HTTP backend tests only
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from noxrunner import NoxRunnerClient
from noxrunner.backend.http import HTTPSandboxBackend
from noxrunner.backend.local import LocalBackend

# Get base URL from environment
BASE_URL = os.environ.get("NOXRUNNER_BASE_URL", "http://127.0.0.1:8080")


class TestLocalBackendIntegration:
    """Integration tests for LocalBackend."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_base = tempfile.mkdtemp(prefix="noxrunner_integration_")
        self.backend = LocalBackend(base_dir=self.test_base)
        self.session_id = f"test-local-{os.getpid()}"

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            self.backend.delete_sandbox(self.session_id)
        except Exception:
            pass
        if os.path.exists(self.test_base):
            shutil.rmtree(self.test_base)

    def test_full_workflow(self):
        """Test complete workflow: create, exec, upload, download, delete."""
        # Create sandbox
        result = self.backend.create_sandbox(self.session_id)
        assert "podName" in result

        # Execute command
        result = self.backend.exec(self.session_id, ["echo", "test"])
        assert result["exitCode"] == 0
        assert "test" in result["stdout"]

        # Upload files
        files = {
            "test.txt": "Hello, World!",
            "script.py": "print('test')",
        }
        result = self.backend.upload_files(self.session_id, files)
        assert result is True

        # Verify files exist
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        workspace = sandbox_path / "workspace"
        assert (workspace / "test.txt").exists()
        assert (workspace / "script.py").exists()

        # Download files
        tar_data = self.backend.download_files(self.session_id)
        assert len(tar_data) > 0

        # Extract and verify
        import io
        import tarfile

        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            members = tar.getnames()
            assert "test.txt" in members
            assert "script.py" in members

        # Delete sandbox
        result = self.backend.delete_sandbox(self.session_id)
        assert result is True
        assert not sandbox_path.exists()

    def test_python_execution(self):
        """Test executing Python code."""
        self.backend.create_sandbox(self.session_id)

        # Upload Python script
        files = {
            "script.py": "print('Hello from Python!')\nprint(2 + 2)",
        }
        self.backend.upload_files(self.session_id, files)

        # Execute script
        result = self.backend.exec(self.session_id, ["python3", "script.py"], workdir="/workspace")

        assert result["exitCode"] == 0
        assert "Hello from Python!" in result["stdout"]
        assert "4" in result["stdout"]

    def test_file_operations(self):
        """Test file operations workflow."""
        self.backend.create_sandbox(self.session_id)

        # Create files
        files = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "subdir/file3.txt": "Content 3",
        }
        self.backend.upload_files(self.session_id, files)

        # List files (use relative path since workdir is already /workspace)
        result = self.backend.exec(self.session_id, ["ls", "-R", "."], workdir="/workspace")
        assert result["exitCode"] == 0
        assert "file1.txt" in result["stdout"]
        assert "file2.txt" in result["stdout"]
        assert "subdir" in result["stdout"]

        # Read file
        result = self.backend.exec(self.session_id, ["cat", "file1.txt"], workdir="/workspace")
        assert result["exitCode"] == 0
        assert "Content 1" in result["stdout"]

    def test_workspace_sync(self):
        """Test workspace synchronization."""
        self.backend.create_sandbox(self.session_id)

        # Upload files
        files = {
            "test1.txt": "Test 1",
            "test2.txt": "Test 2",
        }
        self.backend.upload_files(self.session_id, files)

        # Download and extract to local directory
        tar_data = self.backend.download_files(self.session_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)

            from noxrunner.fileops.tar_handler import TarHandler

            tar_handler = TarHandler()
            tar_handler.extract_tar(tar_data, dest)

            assert (dest / "test1.txt").exists()
            assert (dest / "test2.txt").exists()
            assert (dest / "test1.txt").read_text() == "Test 1"
            assert (dest / "test2.txt").read_text() == "Test 2"


@pytest.mark.integration
class TestHTTPSandboxBackendIntegration:
    """Integration tests for HTTPSandboxBackend.

    These tests require a running backend service at BASE_URL.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.backend = HTTPSandboxBackend(BASE_URL, timeout=30)
        self.session_id = f"test-http-{os.getpid()}"

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            self.backend.delete_sandbox(self.session_id)
        except Exception:
            pass

    def test_health_check(self):
        """Test health check."""
        result = self.backend.health_check()
        assert result is True, f"Backend at {BASE_URL} should be healthy"

    def test_full_workflow(self):
        """Test complete workflow with HTTP backend."""
        # Create sandbox
        result = self.backend.create_sandbox(self.session_id)
        assert "podName" in result

        # Wait for ready
        ready = self.backend.wait_for_pod_ready(self.session_id, timeout=30)
        assert ready is True

        # Execute command
        result = self.backend.exec(self.session_id, ["echo", "test"])
        assert result["exitCode"] == 0
        assert "test" in result["stdout"]

        # Upload files
        files = {
            "test.txt": "Hello, World!",
        }
        result = self.backend.upload_files(self.session_id, files)
        assert result is True

        # Download files
        tar_data = self.backend.download_files(self.session_id)
        assert len(tar_data) > 0

        # Delete sandbox
        result = self.backend.delete_sandbox(self.session_id)
        assert result is True


class TestNoxRunnerClientIntegration:
    """Integration tests for NoxRunnerClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_base = tempfile.mkdtemp(prefix="noxrunner_client_")
        self.session_id = f"test-client-{os.getpid()}"

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_base):
            shutil.rmtree(self.test_base)

    def test_client_local_mode(self):
        """Test client in local mode."""
        client = NoxRunnerClient(local_test=True)

        # Override base_dir for testing
        client._backend.base_dir = Path(self.test_base)

        # Create sandbox
        result = client.create_sandbox(self.session_id)
        assert "podName" in result

        # Execute command
        result = client.exec(self.session_id, ["echo", "hello"])
        assert result["exitCode"] == 0
        assert "hello" in result["stdout"]

        # Upload files
        files = {"test.txt": "content"}
        result = client.upload_files(self.session_id, files)
        assert result is True

        # Download files
        tar_data = client.download_files(self.session_id)
        assert len(tar_data) > 0

        # Download workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            result = client.download_workspace(self.session_id, tmpdir)
            assert result is True
            assert (Path(tmpdir) / "test.txt").exists()

        # Delete sandbox
        result = client.delete_sandbox(self.session_id)
        assert result is True

    @pytest.mark.integration
    def test_client_http_mode(self):
        """Test client in HTTP mode."""
        client = NoxRunnerClient(BASE_URL, timeout=30)
        session_id = f"test-client-http-{os.getpid()}"

        try:
            # Create sandbox
            result = client.create_sandbox(session_id)
            assert "podName" in result

            # Wait for ready
            ready = client.wait_for_pod_ready(session_id, timeout=30)
            assert ready is True

            # Execute command
            result = client.exec(session_id, ["echo", "hello"])
            assert result["exitCode"] == 0

            # Upload files
            files = {"test.txt": "content"}
            result = client.upload_files(session_id, files)
            assert result is True

            # Download workspace
            with tempfile.TemporaryDirectory() as tmpdir:
                result = client.download_workspace(session_id, tmpdir)
                assert result is True

        finally:
            # Cleanup
            try:
                client.delete_sandbox(session_id)
            except Exception:
                pass
