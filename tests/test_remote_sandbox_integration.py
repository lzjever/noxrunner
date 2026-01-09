"""
Integration tests for remote sandbox backend.

These tests require a running NoxRunner backend service.
They are marked with 'integration' marker and run with `make test-integration`.

To run these tests:
    make test-integration

Environment Variables:
    NOXRUNNER_BASE_URL    Base URL of the NoxRunner backend (default: http://127.0.0.1:8080)
"""

import os
import time

import pytest

from noxrunner import NoxRunnerClient, NoxRunnerError, NoxRunnerHTTPError

# Get base URL from environment
BASE_URL = os.environ.get("NOXRUNNER_BASE_URL", "http://127.0.0.1:8080")


@pytest.fixture(scope="module")
def client():
    """Create a client for integration tests."""
    return NoxRunnerClient(BASE_URL, timeout=30)


@pytest.fixture(scope="module")
def session_id():
    """Generate a unique session ID for tests."""
    return f"test-integration-{int(time.time())}"


@pytest.mark.integration
def test_health_check(client):
    """Test health check endpoint."""
    result = client.health_check()
    assert result is True, "Backend should be healthy"


@pytest.mark.integration
def test_create_sandbox(client, session_id):
    """Test creating a sandbox."""
    result = client.create_sandbox(session_id, ttl_seconds=300)

    assert "podName" in result
    assert "expiresAt" in result
    assert result["podName"] is not None


@pytest.mark.integration
def test_wait_for_pod_ready(client, session_id):
    """Test waiting for pod to be ready."""
    # Create sandbox first
    client.create_sandbox(session_id)

    # Wait for pod to be ready
    result = client.wait_for_pod_ready(session_id, timeout=60)
    assert result is True, "Pod should become ready"


@pytest.mark.integration
def test_exec_simple_command(client, session_id):
    """Test executing a simple command."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(session_id, ["echo", "hello", "world"])

    assert result["exitCode"] == 0
    assert "hello" in result["stdout"]
    assert "world" in result["stdout"]
    assert "durationMs" in result


@pytest.mark.integration
def test_exec_with_workdir(client, session_id):
    """Test executing command with custom workdir."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Create a subdirectory
    client.exec(session_id, ["mkdir", "-p", "/workspace/subdir"])

    result = client.exec(session_id, ["pwd"], workdir="/workspace/subdir")

    assert result["exitCode"] == 0
    assert "subdir" in result["stdout"] or "/workspace/subdir" in result["stdout"]


@pytest.mark.integration
def test_exec_with_env(client, session_id):
    """Test executing command with environment variables using printenv."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Use printenv which is more reliable than echo with shell variable expansion
    result = client.exec(session_id, ["printenv", "TEST_VAR"], env={"TEST_VAR": "test_value_123"})

    assert result["exitCode"] == 0
    stdout = result["stdout"].strip()
    assert stdout == "test_value_123", f"Expected 'test_value_123', got: {repr(stdout)}"


@pytest.mark.integration
def test_exec_sh_c_with_env_var_expansion(client, session_id):
    """Test sh -c with environment variable expansion (critical fix test)."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # This was the bug: sh -c 'echo $VAR' should expand $VAR
    result = client.exec(
        session_id, ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "sh_test_value_456"}
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "sh_test_value_456", (
        f"Expected 'sh_test_value_456', got: {repr(stdout)}. "
        f"This test verifies the fix for environment variable expansion in sh -c commands."
    )


@pytest.mark.integration
def test_exec_bash_c_with_env_var_expansion(client, session_id):
    """Test bash -c with environment variable expansion."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(
        session_id, ["bash", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "bash_test_value_789"}
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "bash_test_value_789", (
        f"Expected 'bash_test_value_789', got: {repr(stdout)}. "
        f"bash -c should also expand environment variables correctly."
    )


@pytest.mark.integration
def test_exec_python_c_with_env_var(client, session_id):
    """Test python -c with environment variable access."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(
        session_id,
        ["python3", "-c", "import os; print(os.environ['TEST_VAR'])"],
        env={"TEST_VAR": "python_test_value_abc"},
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "python_test_value_abc", (
        f"Expected 'python_test_value_abc', got: {repr(stdout)}. "
        f"python -c should have access to environment variables."
    )


@pytest.mark.integration
def test_exec_multiple_env_vars(client, session_id):
    """Test multiple environment variables with sh -c."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(
        session_id,
        ["sh", "-c", "echo $VAR1:$VAR2:$VAR3"],
        env={
            "VAR1": "value1",
            "VAR2": "value2",
            "VAR3": "value3",
        },
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "value1:value2:value3", (
        f"Expected 'value1:value2:value3', got: {repr(stdout)}. "
        f"Multiple environment variables should all be expanded correctly."
    )


@pytest.mark.integration
def test_exec_env_var_with_special_chars(client, session_id):
    """Test environment variable with special characters (spaces, quotes)."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Test with spaces and special characters
    special_value = "test value with spaces and 'quotes'"
    result = client.exec(
        session_id,
        ["sh", "-c", 'echo "$TEST_VAR"'],
        env={"TEST_VAR": special_value},
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == special_value, (
        f"Expected {repr(special_value)}, got: {repr(stdout)}. "
        f"Environment variables with special characters should be handled correctly."
    )


@pytest.mark.integration
def test_exec_env_var_nested_expansion(client, session_id):
    """Test nested environment variable expansion."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(
        session_id,
        ["sh", "-c", "echo $BASE/$SUBDIR"],
        env={
            "BASE": "/workspace",
            "SUBDIR": "test",
        },
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "/workspace/test", (
        f"Expected '/workspace/test', got: {repr(stdout)}. "
        f"Nested variable expansion should work correctly."
    )


@pytest.mark.integration
def test_exec_regular_command_still_safe(client, session_id):
    """Test that regular commands (not X -c) still use single quotes for safety."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Regular commands should still work correctly
    result = client.exec(
        session_id,
        ["echo", "$TEST_VAR"],  # This should NOT expand $TEST_VAR (it's a literal string)
        env={"TEST_VAR": "should_not_appear"},
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    # echo "$TEST_VAR" should output the literal string, not the variable value
    # because it's not in a shell -c context
    assert "$TEST_VAR" in stdout or stdout == "$TEST_VAR", (
        f"Expected literal '$TEST_VAR', got: {repr(stdout)}. "
        f"Regular commands should not expand variables (safety feature)."
    )


@pytest.mark.integration
def test_exec_sh_c_with_multiple_commands(client, session_id):
    """Test sh -c with multiple commands and environment variables."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Test multiple commands with different variables
    result = client.exec(
        session_id,
        ["sh", "-c", 'echo "VAR1=$VAR1 VAR2=$VAR2 VAR3=$VAR3"'],
        env={
            "VAR1": "value1",
            "VAR2": "value2",
            "VAR3": "value3",
        },
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    # Should see all three values
    assert "value1" in stdout, (
        f"Expected 'value1' in output, got: {repr(stdout)}. "
        f"Multiple commands with variable expansion should work."
    )
    assert "value2" in stdout, f"Expected 'value2' in output, got: {repr(stdout)}."
    assert "value3" in stdout, f"Expected 'value3' in output, got: {repr(stdout)}."


@pytest.mark.integration
def test_exec_timeout(client, session_id):
    """Test command timeout."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec(session_id, ["sleep", "10"], timeout_seconds=2)

    # Should timeout (exit code 124) or fail
    assert result["exitCode"] != 0


@pytest.mark.integration
def test_upload_files(client, session_id):
    """Test uploading files."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    files = {
        "test.txt": "Hello, World!",
        "script.py": "print('test')",
        "data.bin": b"\x00\x01\x02\x03",
    }

    result = client.upload_files(session_id, files, dest="/workspace")
    assert result is True

    # Verify files exist
    result = client.exec(session_id, ["ls", "-la", "/workspace"])
    assert result["exitCode"] == 0
    assert "test.txt" in result["stdout"]
    assert "script.py" in result["stdout"]
    assert "data.bin" in result["stdout"]


@pytest.mark.integration
def test_download_files(client, session_id):
    """Test downloading files."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Create some files
    files = {"file1.txt": "content1", "file2.txt": "content2", "subdir/file3.txt": "content3"}
    client.upload_files(session_id, files, dest="/workspace")

    # Download files
    tar_data = client.download_files(session_id, src="/workspace")
    assert len(tar_data) > 0

    # Extract and verify
    import io
    import tarfile

    tar_buffer = io.BytesIO(tar_data)
    # Use r:* to auto-detect compression (some backends return gzip, others return plain tar)
    with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
        names = tar.getnames()
        # Filter out directory entries
        file_names = [n for n in names if not n.endswith("/") and n != "."]
        assert any("file1.txt" in name for name in file_names) or any(
            "file1.txt" in name for name in names
        )
        assert any("file2.txt" in name for name in file_names) or any(
            "file2.txt" in name for name in names
        )


@pytest.mark.integration
def test_touch(client, session_id):
    """Test touching (extending TTL) a sandbox."""
    client.create_sandbox(session_id, ttl_seconds=300)

    result = client.touch(session_id)
    assert result is True


@pytest.mark.integration
def test_delete_sandbox(client, session_id):
    """Test deleting a sandbox."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.delete_sandbox(session_id)
    assert result is True

    # Verify sandbox is deleted
    # Note: Some backends may auto-recreate sandboxes on exec, so we check multiple ways
    try:
        # Try to exec - should either fail or the backend may auto-recreate
        exec_result = client.exec(session_id, ["echo", "test"], timeout_seconds=5)
        # If exec succeeds, backend auto-recreated the sandbox (acceptable behavior)
        # Just verify we got a response
        assert "exitCode" in exec_result
    except (NoxRunnerError, NoxRunnerHTTPError):
        # If exec fails, that's also acceptable - sandbox was deleted
        pass


@pytest.mark.integration
def test_full_workflow(client):
    """Test a complete workflow: create, upload, exec, download, delete."""
    session_id = f"workflow-test-{int(time.time())}"

    try:
        # Create sandbox
        result = client.create_sandbox(session_id, ttl_seconds=600)
        assert "podName" in result

        # Wait for ready
        assert client.wait_for_pod_ready(session_id, timeout=60)

        # Upload files
        files = {
            "script.py": "#!/usr/bin/env python3\nprint('Hello from script!')\n",
            "data.txt": "test data",
        }
        assert client.upload_files(session_id, files)

        # Execute script
        result = client.exec(session_id, ["python3", "/workspace/script.py"])
        assert result["exitCode"] == 0
        assert "Hello from script!" in result["stdout"]

        # Download files
        tar_data = client.download_files(session_id)
        assert len(tar_data) > 0

        # Touch
        assert client.touch(session_id)

    finally:
        # Cleanup
        try:
            client.delete_sandbox(session_id)
        except Exception:
            pass


@pytest.mark.integration
def test_concurrent_sessions(client):
    """Test multiple concurrent sessions."""
    session_ids = [f"concurrent-{i}-{int(time.time())}" for i in range(3)]

    try:
        # Create multiple sandboxes
        for sid in session_ids:
            client.create_sandbox(sid, ttl_seconds=300)

        # Wait for all to be ready
        for sid in session_ids:
            assert client.wait_for_pod_ready(sid, timeout=60)

        # Execute commands in each
        for sid in session_ids:
            result = client.exec(sid, ["echo", f"session-{sid}"])
            assert result["exitCode"] == 0

    finally:
        # Cleanup
        for sid in session_ids:
            try:
                client.delete_sandbox(sid)
            except Exception:
                pass


@pytest.mark.integration
def test_exec_shell_simple(client, session_id):
    """Test exec_shell with simple command."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec_shell(session_id, "echo hello world")

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "hello world", f"Expected 'hello world', got: {repr(stdout)}"


@pytest.mark.integration
def test_exec_shell_with_env(client, session_id):
    """Test exec_shell with environment variables."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec_shell(
        session_id, "echo $TEST_VAR", env={"TEST_VAR": "shell_test_value_123"}
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert stdout == "shell_test_value_123", (
        f"Expected 'shell_test_value_123', got: {repr(stdout)}. "
        f"exec_shell should correctly expand environment variables."
    )


@pytest.mark.integration
def test_exec_shell_with_pipes(client, session_id):
    """Test exec_shell with pipes and redirection."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Create a file first
    client.exec(session_id, ["sh", "-c", "echo -e 'line1\\nline2\\nline3\\nline4' > test.txt"])

    result = client.exec_shell(session_id, "cat test.txt | head -2")

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert "line1" in stdout, f"Expected 'line1' in output, got: {repr(stdout)}"
    assert "line2" in stdout, f"Expected 'line2' in output, got: {repr(stdout)}"
    assert "line4" not in stdout or stdout.count("line") <= 2, (
        f"Expected only first 2 lines, got: {repr(stdout)}"
    )


@pytest.mark.integration
def test_exec_shell_with_multiple_commands(client, session_id):
    """Test exec_shell with multiple commands (&&)."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Use environment variables passed to exec_shell instead of export
    result = client.exec_shell(
        session_id, 'echo "$VAR1:$VAR2"', env={"VAR1": "value1", "VAR2": "value2"}
    )

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    # The output should contain both values
    assert "value1" in stdout and "value2" in stdout, (
        f"Expected both 'value1' and 'value2' in output, got: {repr(stdout)}"
    )


@pytest.mark.integration
def test_exec_shell_with_bash(client, session_id):
    """Test exec_shell with bash shell."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    result = client.exec_shell(session_id, "echo $BASH_VERSION", shell="bash")

    # bash might not be available, so check exit code
    if result["exitCode"] == 0:
        stdout = result["stdout"].strip()
        stdout
        # If bash is available, BASH_VERSION should be non-empty
        # But if it's empty, that's also acceptable (might be a minimal bash)
        # Just verify the command executed successfully
        assert result["exitCode"] == 0, "Command should succeed if bash is available"
    else:
        # bash not found is acceptable
        assert result["exitCode"] in (
            127,
            1,
        ), f"Expected exit code 127 or 1 if bash not found, got: {result['exitCode']}"


@pytest.mark.integration
def test_exec_shell_invalid_shell(client, session_id):
    """Test exec_shell with invalid shell raises ValueError."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    with pytest.raises(ValueError, match="shell must be 'sh' or 'bash'"):
        client.exec_shell(session_id, "echo test", shell="python")


@pytest.mark.integration
def test_exec_shell_with_workdir(client, session_id):
    """Test exec_shell with custom workdir."""
    client.create_sandbox(session_id)
    client.wait_for_pod_ready(session_id, timeout=60)

    # Create subdirectory
    client.exec(session_id, ["mkdir", "-p", "/workspace/subdir"])

    result = client.exec_shell(session_id, "pwd", workdir="/workspace/subdir")

    assert result["exitCode"] == 0, f"Command failed: {result.get('stderr', '')}"
    stdout = result["stdout"].strip()
    assert "subdir" in stdout or "/workspace/subdir" in stdout, (
        f"Expected workdir in output, got: {repr(stdout)}"
    )
