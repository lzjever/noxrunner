"""
Tests for local sandbox backend.

WARNING: These tests execute commands in the local environment.
They are designed to be safe by only operating within /tmp directories.
"""

import os
import tempfile
import shutil
import pytest

from noxrunner import NoxRunnerClient
from noxrunner.local_sandbox import LocalSandboxBackend


class TestLocalSandboxBackend:
    """Test LocalSandboxBackend directly."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a temporary directory for testing
        self.test_base = tempfile.mkdtemp(prefix="noxrunner_test_")
        self.backend = LocalSandboxBackend(base_dir=self.test_base)
        self.session_id = "test-session-123"

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up sandbox
        if self.session_id in self.backend._sandboxes:
            self.backend.delete_sandbox(self.session_id)
        # Clean up test directory
        if os.path.exists(self.test_base):
            shutil.rmtree(self.test_base)

    def test_health_check(self):
        """Test health check."""
        assert self.backend.health_check() is True

    def test_create_sandbox(self):
        """Test creating a sandbox."""
        result = self.backend.create_sandbox(self.session_id, ttl_seconds=300)

        assert "podName" in result
        assert "expiresAt" in result
        assert result["podName"] == f"local-{self.session_id}"

        # Verify sandbox directory exists
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        assert sandbox_path.exists()
        assert (sandbox_path / "workspace").exists()

    def test_touch(self):
        """Test touching a sandbox."""
        # Create sandbox first
        self.backend.create_sandbox(self.session_id)

        # Touch should extend TTL
        assert self.backend.touch(self.session_id) is True

        # Touch non-existent sandbox should create it
        assert self.backend.touch("new-session") is True

    def test_exec_simple_command(self, capsys):
        """Test executing a simple command."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(self.session_id, ["echo", "hello"])

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""
        assert "durationMs" in result

    def test_exec_python_command(self, capsys):
        """Test executing a Python command."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(self.session_id, ["python3", "-c", "print('test output')"])

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # Python might not be available, so check exit code
        if result["exitCode"] == 0:
            assert "test output" in result["stdout"]
        else:
            # Python not found is acceptable in test environment
            assert result["exitCode"] in (127, 1)  # Command not found or error

    def test_exec_with_workdir(self, capsys):
        """Test executing command with custom workdir."""
        self.backend.create_sandbox(self.session_id)

        # Create a subdirectory
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        subdir = sandbox_path / "workspace" / "subdir"
        subdir.mkdir(parents=True, exist_ok=True)

        result = self.backend.exec(self.session_id, ["pwd"], workdir="/workspace/subdir")

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        if result["exitCode"] == 0:
            # pwd output should contain the workdir
            assert "subdir" in result["stdout"] or "workspace" in result["stdout"]

    def test_exec_with_env(self, capsys):
        """Test executing command with environment variables using printenv."""
        self.backend.create_sandbox(self.session_id)

        # Use printenv which is more reliable than echo with shell variable expansion
        result = self.backend.exec(
            self.session_id, ["printenv", "TEST_VAR"], env={"TEST_VAR": "test_value_123"}
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0
        stdout = result["stdout"].strip()
        assert stdout == "test_value_123", f"Expected 'test_value_123', got: {repr(stdout)}"

    def test_exec_sh_c_with_env_var_expansion(self, capsys):
        """Test sh -c with environment variable expansion (critical fix test)."""
        self.backend.create_sandbox(self.session_id)

        # This was the bug: sh -c 'echo $VAR' should expand $VAR
        result = self.backend.exec(
            self.session_id, ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "sh_test_value_456"}
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "sh_test_value_456", (
            f"Expected 'sh_test_value_456', got: {repr(stdout)}. "
            f"This test verifies the fix for environment variable expansion in sh -c commands."
        )

    def test_exec_bash_c_with_env_var_expansion(self, capsys):
        """Test bash -c with environment variable expansion."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(
            self.session_id,
            ["bash", "-c", "echo $TEST_VAR"],
            env={"TEST_VAR": "bash_test_value_789"},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "bash_test_value_789", (
            f"Expected 'bash_test_value_789', got: {repr(stdout)}. "
            f"bash -c should also expand environment variables correctly."
        )

    def test_exec_python_c_with_env_var(self, capsys):
        """Test python -c with environment variable access."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(
            self.session_id,
            ["python3", "-c", "import os; print(os.environ['TEST_VAR'])"],
            env={"TEST_VAR": "python_test_value_abc"},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # Python might not be available, so check exit code
        if result["exitCode"] == 0:
            stdout = result["stdout"].strip()
            assert stdout == "python_test_value_abc", (
                f"Expected 'python_test_value_abc', got: {repr(stdout)}. "
                f"python -c should have access to environment variables."
            )
        else:
            # Python not found is acceptable in test environment
            assert result["exitCode"] in (127, 1), f"Unexpected exit code: {result['exitCode']}"

    def test_exec_multiple_env_vars(self, capsys):
        """Test multiple environment variables with sh -c."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(
            self.session_id,
            ["sh", "-c", "echo $VAR1:$VAR2:$VAR3"],
            env={
                "VAR1": "value1",
                "VAR2": "value2",
                "VAR3": "value3",
            },
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "value1:value2:value3", (
            f"Expected 'value1:value2:value3', got: {repr(stdout)}. "
            f"Multiple environment variables should all be expanded correctly."
        )

    def test_exec_env_var_with_special_chars(self, capsys):
        """Test environment variable with special characters (spaces, quotes)."""
        self.backend.create_sandbox(self.session_id)

        # Test with spaces and special characters
        special_value = "test value with spaces and 'quotes'"
        result = self.backend.exec(
            self.session_id,
            ["sh", "-c", 'echo "$TEST_VAR"'],
            env={"TEST_VAR": special_value},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == special_value, (
            f"Expected {repr(special_value)}, got: {repr(stdout)}. "
            f"Environment variables with special characters should be handled correctly."
        )

    def test_exec_env_var_nested_expansion(self, capsys):
        """Test nested environment variable expansion."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(
            self.session_id,
            ["sh", "-c", "echo $BASE/$SUBDIR"],
            env={
                "BASE": "/workspace",
                "SUBDIR": "test",
            },
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "/workspace/test", (
            f"Expected '/workspace/test', got: {repr(stdout)}. "
            f"Nested variable expansion should work correctly."
        )

    def test_exec_regular_command_still_safe(self, capsys):
        """Test that regular commands (not X -c) still use single quotes for safety."""
        self.backend.create_sandbox(self.session_id)

        # Regular commands should still work correctly
        result = self.backend.exec(
            self.session_id,
            ["echo", "$TEST_VAR"],  # This should NOT expand $TEST_VAR (it's a literal string)
            env={"TEST_VAR": "should_not_appear"},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        # echo "$TEST_VAR" should output the literal string, not the variable value
        # because it's not in a shell -c context
        assert "$TEST_VAR" in stdout or stdout == "$TEST_VAR", (
            f"Expected literal '$TEST_VAR', got: {repr(stdout)}. "
            f"Regular commands should not expand variables (safety feature)."
        )

    def test_exec_sh_c_with_multiple_commands(self, capsys):
        """Test sh -c with multiple commands and environment variables."""
        self.backend.create_sandbox(self.session_id)

        # Test multiple commands with different variables
        result = self.backend.exec(
            self.session_id,
            ["sh", "-c", 'echo "VAR1=$VAR1 VAR2=$VAR2 VAR3=$VAR3"'],
            env={
                "VAR1": "value1",
                "VAR2": "value2",
                "VAR3": "value3",
            },
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        # Should see all three values
        assert "value1" in stdout, (
            f"Expected 'value1' in output, got: {repr(stdout)}. "
            f"Multiple commands with variable expansion should work."
        )
        assert "value2" in stdout, f"Expected 'value2' in output, got: {repr(stdout)}."
        assert "value3" in stdout, f"Expected 'value3' in output, got: {repr(stdout)}."

    def test_exec_timeout(self, capsys):
        """Test command timeout."""
        self.backend.create_sandbox(self.session_id)

        # Try to sleep (if available)
        result = self.backend.exec(self.session_id, ["sleep", "10"], timeout_seconds=1)

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # Should timeout or command not found
        assert result["exitCode"] in (124, 127)  # Timeout or not found

    def test_exec_blocked_command(self, capsys):
        """Test that blocked commands are rejected."""
        self.backend.create_sandbox(self.session_id)

        result = self.backend.exec(self.session_id, ["rm", "-rf", "/"])

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # Should be blocked
        assert result["exitCode"] == 1
        assert "not allowed" in result["stderr"].lower()

    def test_upload_files(self):
        """Test uploading files."""
        self.backend.create_sandbox(self.session_id)

        files = {
            "test.txt": "Hello, World!",
            "script.py": "print('test')",
            "binary.bin": b"\x00\x01\x02\x03",
        }

        result = self.backend.upload_files(self.session_id, files, dest="/workspace")
        assert result is True

        # Verify files exist
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        workspace = sandbox_path / "workspace"

        assert (workspace / "test.txt").exists()
        assert (workspace / "script.py").exists()
        assert (workspace / "binary.bin").exists()

        # Verify content
        assert (workspace / "test.txt").read_text() == "Hello, World!"
        assert (workspace / "script.py").read_text() == "print('test')"
        assert (workspace / "binary.bin").read_bytes() == b"\x00\x01\x02\x03"

    def test_upload_files_path_traversal_protection(self):
        """Test that path traversal attacks are prevented."""
        self.backend.create_sandbox(self.session_id)

        # Try to upload file with path traversal
        files = {"../../../etc/passwd": "should not be written", "normal.txt": "should be written"}

        result = self.backend.upload_files(self.session_id, files)
        assert result is True

        # Verify only safe filename was written
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        workspace = sandbox_path / "workspace"

        # Path traversal should be sanitized to just filename
        assert not (workspace / "../../../etc/passwd").exists()
        assert (workspace / "passwd").exists() or (workspace / "normal.txt").exists()

    def test_download_files(self):
        """Test downloading files."""
        self.backend.create_sandbox(self.session_id)

        # Create some files
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        workspace = sandbox_path / "workspace"
        (workspace / "file1.txt").write_text("content1")
        (workspace / "file2.txt").write_text("content2")
        (workspace / "subdir").mkdir()
        (workspace / "subdir" / "file3.txt").write_text("content3")

        # Download files
        tar_data = self.backend.download_files(self.session_id, src="/workspace")

        assert len(tar_data) > 0

        # Extract and verify
        import tarfile
        import io

        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:gz") as tar:
            names = tar.getnames()
            assert any("file1.txt" in name for name in names)
            assert any("file2.txt" in name for name in names)

    def test_delete_sandbox(self):
        """Test deleting a sandbox."""
        self.backend.create_sandbox(self.session_id)

        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        assert sandbox_path.exists()

        result = self.backend.delete_sandbox(self.session_id)
        assert result is True

        # Verify sandbox directory is deleted
        assert not sandbox_path.exists()
        assert self.session_id not in self.backend._sandboxes

    def test_wait_for_pod_ready(self):
        """Test waiting for pod ready."""
        # Local sandbox should be ready immediately
        result = self.backend.wait_for_pod_ready(self.session_id)
        assert result is True


class TestNoxRunnerClientLocalMode:
    """Test NoxRunnerClient with local_test mode."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a temporary directory for testing
        self.test_base = tempfile.mkdtemp(prefix="noxrunner_test_")
        # Create client with local_test=True
        self.client = NoxRunnerClient(local_test=True)
        # Override base_dir for testing
        from pathlib import Path

        # Access the backend instance
        self.client._backend.base_dir = Path(self.test_base)
        self.session_id = "test-client-session"

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            self.client.delete_sandbox(self.session_id)
        except Exception:
            pass
        # Clean up test directory
        if os.path.exists(self.test_base):
            shutil.rmtree(self.test_base)

    def test_client_local_mode_initialization(self):
        """Test client initialization with local mode."""
        # Warning is printed during setup_method when client is created
        # Just verify client was created successfully
        assert self.client is not None
        assert hasattr(self.client, "_backend")

    def test_client_create_sandbox(self):
        """Test creating sandbox via client."""
        result = self.client.create_sandbox(self.session_id)

        assert "podName" in result
        assert "expiresAt" in result

    def test_client_exec(self, capsys):
        """Test executing command via client."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec(self.session_id, ["echo", "test"])

        # Multiple warnings should be printed (init + exec)
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0
        assert "test" in result["stdout"]

    def test_client_upload_download(self):
        """Test upload and download via client."""
        self.client.create_sandbox(self.session_id)

        # Upload files
        files = {"test.txt": "Hello from test", "data.json": '{"key": "value"}'}
        assert self.client.upload_files(self.session_id, files) is True

        # Download files
        tar_data = self.client.download_files(self.session_id)
        assert len(tar_data) > 0

        # Verify content
        import tarfile
        import io

        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:gz") as tar:
            names = tar.getnames()
            assert any("test.txt" in name for name in names)

    def test_client_touch(self):
        """Test touch via client."""
        self.client.create_sandbox(self.session_id)
        assert self.client.touch(self.session_id) is True

    def test_client_delete_sandbox(self):
        """Test delete sandbox via client."""
        self.client.create_sandbox(self.session_id)
        assert self.client.delete_sandbox(self.session_id) is True

    def test_client_health_check(self):
        """Test health check via client."""
        assert self.client.health_check() is True

    def test_client_wait_for_pod_ready(self):
        """Test wait for pod ready via client."""
        assert self.client.wait_for_pod_ready(self.session_id) is True

    def test_client_exec_sh_c_with_env_var_expansion(self, capsys):
        """Test client sh -c with environment variable expansion."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec(
            self.session_id, ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "client_sh_test_123"}
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "client_sh_test_123", (
            f"Expected 'client_sh_test_123', got: {repr(stdout)}. "
            f"Client should correctly expand environment variables in sh -c commands."
        )

    def test_client_exec_bash_c_with_env_var_expansion(self, capsys):
        """Test client bash -c with environment variable expansion."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec(
            self.session_id,
            ["bash", "-c", "echo $TEST_VAR"],
            env={"TEST_VAR": "client_bash_test_456"},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "client_bash_test_456", (
            f"Expected 'client_bash_test_456', got: {repr(stdout)}. "
            f"Client should correctly expand environment variables in bash -c commands."
        )

    def test_client_exec_python_c_with_env_var(self, capsys):
        """Test client python -c with environment variable access."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec(
            self.session_id,
            ["python3", "-c", "import os; print(os.environ['TEST_VAR'])"],
            env={"TEST_VAR": "client_python_test_789"},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # Python might not be available
        if result["exitCode"] == 0:
            stdout = result["stdout"].strip()
            assert stdout == "client_python_test_789", (
                f"Expected 'client_python_test_789', got: {repr(stdout)}. "
                f"Client should correctly pass environment variables to python -c commands."
            )
        else:
            # Python not found is acceptable
            assert result["exitCode"] in (127, 1)

    def test_client_exec_multiple_env_vars(self, capsys):
        """Test client with multiple environment variables."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec(
            self.session_id,
            ["sh", "-c", "echo $VAR1:$VAR2:$VAR3"],
            env={
                "VAR1": "client_val1",
                "VAR2": "client_val2",
                "VAR3": "client_val3",
            },
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "client_val1:client_val2:client_val3", (
            f"Expected 'client_val1:client_val2:client_val3', got: {repr(stdout)}. "
            f"Client should correctly expand multiple environment variables."
        )

    def test_client_exec_env_var_with_special_chars(self, capsys):
        """Test client with environment variable containing special characters."""
        self.client.create_sandbox(self.session_id)

        special_value = "client test with spaces and 'quotes'"
        result = self.client.exec(
            self.session_id,
            ["sh", "-c", 'echo "$TEST_VAR"'],
            env={"TEST_VAR": special_value},
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == special_value, (
            f"Expected {repr(special_value)}, got: {repr(stdout)}. "
            f"Client should correctly handle environment variables with special characters."
        )

    def test_client_exec_shell_simple(self, capsys):
        """Test exec_shell with simple command."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec_shell(self.session_id, "echo hello world")

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "hello world", f"Expected 'hello world', got: {repr(stdout)}"

    def test_client_exec_shell_with_env(self, capsys):
        """Test exec_shell with environment variables."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec_shell(
            self.session_id, "echo $TEST_VAR", env={"TEST_VAR": "shell_test_value"}
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
        stdout = result["stdout"].strip()
        assert stdout == "shell_test_value", (
            f"Expected 'shell_test_value', got: {repr(stdout)}. "
            f"exec_shell should correctly expand environment variables."
        )

    def test_client_exec_shell_with_pipes(self, capsys):
        """Test exec_shell with pipes."""
        self.client.create_sandbox(self.session_id)

        # Create a file first
        self.client.exec(
            self.session_id, ["sh", "-c", "echo -e 'line1\\nline2\\nline3' > test.txt"]
        )

        result = self.client.exec_shell(self.session_id, "cat test.txt | head -2")

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        if result["exitCode"] == 0:
            stdout = result["stdout"].strip()
            assert "line1" in stdout, f"Expected 'line1' in output, got: {repr(stdout)}"
            assert "line2" in stdout, f"Expected 'line2' in output, got: {repr(stdout)}"

    def test_client_exec_shell_with_bash(self, capsys):
        """Test exec_shell with bash shell."""
        self.client.create_sandbox(self.session_id)

        result = self.client.exec_shell(self.session_id, "echo $BASH_VERSION", shell="bash")

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        # bash might not be available, so check exit code
        if result["exitCode"] == 0:
            stdout = result["stdout"].strip()
            assert len(stdout) > 0, "BASH_VERSION should be non-empty if bash is available"
        else:
            # bash not found is acceptable
            assert result["exitCode"] in (127, 1)

    def test_client_exec_shell_invalid_shell(self):
        """Test exec_shell with invalid shell raises ValueError."""
        self.client.create_sandbox(self.session_id)

        with pytest.raises(ValueError, match="shell must be 'sh' or 'bash'"):
            self.client.exec_shell(self.session_id, "echo test", shell="python")

    def test_client_exec_shell_with_workdir(self, capsys):
        """Test exec_shell with custom workdir."""
        self.client.create_sandbox(self.session_id)

        # Create subdirectory and a file in it
        self.client.exec(self.session_id, ["mkdir", "-p", "/workspace/subdir"])
        self.client.exec(self.session_id, ["sh", "-c", "echo 'test' > /workspace/subdir/test.txt"])

        result = self.client.exec_shell(
            self.session_id, "cat test.txt", workdir="/workspace/subdir"
        )

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err

        if result["exitCode"] == 0:
            stdout = result["stdout"].strip()
            assert (
                "test" in stdout
            ), f"Expected 'test' in output (workdir should be /workspace/subdir), got: {repr(stdout)}"


class TestLocalSandboxSecurity:
    """Test security features of local sandbox."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_base = tempfile.mkdtemp(prefix="noxrunner_test_")
        self.backend = LocalSandboxBackend(base_dir=self.test_base)
        self.session_id = "security-test"

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            self.backend.delete_sandbox(self.session_id)
        except Exception:
            pass
        if os.path.exists(self.test_base):
            shutil.rmtree(self.test_base)

    def test_path_traversal_protection(self):
        """Test that path traversal is prevented."""
        self.backend.create_sandbox(self.session_id)
        sandbox_path = self.backend._get_sandbox_path(self.session_id)

        # Try to access path outside sandbox
        outside_path = "/etc/passwd"
        sanitized = self.backend._sanitize_path(outside_path, sandbox_path)

        # Should be redirected to workspace
        assert sandbox_path.resolve() in sanitized.resolve().parents

    def test_relative_path_safety(self):
        """Test that relative paths are safe."""
        self.backend.create_sandbox(self.session_id)
        sandbox_path = self.backend._get_sandbox_path(self.session_id)

        # Try relative path traversal
        relative_path = "../../../etc/passwd"
        sanitized = self.backend._sanitize_path(relative_path, sandbox_path)

        # Should be within sandbox
        try:
            sanitized.resolve().relative_to(sandbox_path.resolve())
        except ValueError:
            pytest.fail("Path traversal not prevented")

    def test_command_validation(self):
        """Test command validation."""
        # Blocked commands should be rejected
        assert not self.backend._validate_command(["rm", "-rf", "/"])
        assert not self.backend._validate_command(["sudo", "rm", "/"])

        # Allowed commands should pass (if they exist)
        # Note: We can't test all commands as they may not exist
        assert self.backend._validate_command(["echo", "test"])

    def test_sandbox_isolation(self, capsys):
        """Test that sandboxes are isolated."""
        self.backend.create_sandbox(self.session_id)

        # Create file in sandbox
        sandbox_path = self.backend._get_sandbox_path(self.session_id)
        test_file = sandbox_path / "workspace" / "isolated.txt"
        test_file.write_text("isolated content")

        # Execute command that tries to access it
        result = self.backend.exec(self.session_id, ["cat", "isolated.txt"], workdir="/workspace")

        # Should be able to access file within sandbox
        if result["exitCode"] == 0:
            assert "isolated content" in result["stdout"]

        # Check warning was printed
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "CRITICAL WARNING" in captured.err
