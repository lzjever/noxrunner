"""
Tests for security modules.

Tests for command validation and path sanitization.
"""

from pathlib import Path

from noxrunner.security.command_validator import CommandValidator
from noxrunner.security.path_sanitizer import PathSanitizer


class TestCommandValidator:
    """Test CommandValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CommandValidator()

    def test_validate_empty_command(self):
        """Test validation of empty command."""
        assert self.validator.validate([]) is False

    def test_validate_allowed_command(self):
        """Test validation of allowed commands."""
        assert self.validator.validate(["echo", "hello"]) is True
        assert self.validator.validate(["python3", "--version"]) is True
        assert self.validator.validate(["ls", "-la"]) is True

    def test_validate_blocked_command(self):
        """Test validation of blocked commands."""
        assert self.validator.validate(["rm", "-rf", "/"]) is False
        assert self.validator.validate(["sudo", "rm", "-rf", "/"]) is False
        assert self.validator.validate(["shutdown", "-h", "now"]) is False

    def test_is_allowed(self):
        """Test is_allowed method."""
        assert self.validator.is_allowed("echo") is True
        assert self.validator.is_allowed("python3") is True
        assert self.validator.is_allowed("rm") is False

    def test_is_blocked(self):
        """Test is_blocked method."""
        assert self.validator.is_blocked("rm") is True
        assert self.validator.is_blocked("sudo") is True
        assert self.validator.is_blocked("echo") is False

    def test_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert self.validator.validate(["ECHO", "hello"]) is True
        assert self.validator.validate(["RM", "-rf", "/"]) is False

    def test_validate_unknown_command_blocked(self):
        """Test that unknown commands are blocked by allowlist."""
        # Unknown commands should be rejected
        assert self.validator.validate(["unknown_command", "arg1"]) is False
        assert self.validator.validate(["malicious_cmd", "--evil"]) is False
        assert self.validator.validate(["nmap", "localhost"]) is False
        assert self.validator.validate(["nc", "-l", "1234"]) is False

    def test_validate_all_allowed_commands_pass(self):
        """Test that all commands in ALLOWED_COMMANDS pass validation."""

        # Sample of allowed commands
        allowed_samples = [
            "echo",
            "cat",
            "ls",
            "pwd",
            "python3",
            "bash",
            "grep",
            "mkdir",
            "touch",
            "cp",
            "mv",
            "tar",
            "gzip",
        ]

        for cmd in allowed_samples:
            assert self.validator.validate([cmd, "arg"]) is True, f"Command {cmd} should be allowed"

    def test_validate_all_blocked_commands_fail(self):
        """Test that all commands in BLOCKED_COMMANDS fail validation."""

        # Sample of blocked commands
        blocked_samples = ["rm", "rmdir", "sudo", "su", "chmod", "chown", "killall"]

        for cmd in blocked_samples:
            assert self.validator.validate([cmd, "arg"]) is False, (
                f"Command {cmd} should be blocked"
            )


class TestPathSanitizer:
    """Test PathSanitizer."""

    def setup_method(self):
        """Set up test fixtures."""
        import tempfile

        self.temp_dir = Path(tempfile.mkdtemp())
        self.sanitizer = PathSanitizer()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_sanitize_relative_path(self):
        """Test sanitizing relative paths."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()

        result = self.sanitizer.sanitize("test.txt", sandbox_path)
        expected = sandbox_path / "workspace" / "test.txt"
        assert result == expected

    def test_sanitize_absolute_path_within_sandbox(self):
        """Test sanitizing absolute path within sandbox."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()
        workspace = sandbox_path / "workspace"
        workspace.mkdir()
        test_file = workspace / "test.txt"
        test_file.write_text("test")

        result = self.sanitizer.sanitize(str(test_file), sandbox_path)
        assert result == test_file

    def test_sanitize_absolute_path_outside_sandbox(self):
        """Test sanitizing absolute path outside sandbox."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()

        # Try to access path outside sandbox
        outside_path = self.temp_dir / "outside" / "test.txt"
        result = self.sanitizer.sanitize(str(outside_path), sandbox_path)

        # Should redirect to workspace
        expected = sandbox_path / "workspace"
        assert result == expected

    def test_sanitize_path_traversal(self):
        """Test sanitizing path traversal attempts."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()

        # Path traversal attempts
        result1 = self.sanitizer.sanitize("../../etc/passwd", sandbox_path)
        result2 = self.sanitizer.sanitize("../test.txt", sandbox_path)

        # Should redirect to workspace
        expected = sandbox_path / "workspace"
        assert result1 == expected
        assert result2 == expected

    def test_sanitize_path_traversal_advanced(self):
        """Test advanced path traversal attempts that bypass simple checks."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()
        workspace = sandbox_path / "workspace"
        workspace.mkdir()

        # Various path traversal bypass attempts
        traversal_attempts = [
            "....//....//etc/passwd",  # Double dots variation
            "..././../etc/passwd",  # Mixed dots
            "./../../etc/passwd",  # Leading dot
            "..//..//etc/passwd",  # Double slashes
            "../",  # Parent directory only
            "../../",  # Multiple parents
            "...",  # Triple dot (traversal)
            "....",  # Quadruple dot (traversal)
            "..\\..\\etc\\passwd",  # Windows-style (if applicable)
            "/../../etc/passwd",  # Leading slash with traversal
        ]

        for attempt in traversal_attempts:
            result = self.sanitizer.sanitize(attempt, sandbox_path)
            # All traversal attempts should be blocked and redirected to workspace
            assert result == workspace, f"Traversal attempt not blocked: {attempt}"

    def test_sanitize_valid_paths_still_work(self):
        """Test that valid paths still work after security fix."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()
        workspace = sandbox_path / "workspace"
        workspace.mkdir()

        # Valid paths should still work
        valid_paths = [
            "file.txt",
            "subdir/file.txt",
            "subdir/deeply/nested/file.txt",
            "dir../file.txt",  # Contains .. but is not a traversal
            "file..txt",  # Contains .. but is not a traversal
            "....txt",  # Looks suspicious but is a valid filename
            "...txt",  # Also a valid filename
        ]

        for path in valid_paths:
            result = self.sanitizer.sanitize(path, sandbox_path)
            # Verify result is within workspace
            try:
                result.relative_to(workspace)
            except ValueError:
                raise AssertionError(f"Valid path rejected: {path}")

    def test_sanitize_filename(self):
        """Test sanitizing filename."""
        assert self.sanitizer.sanitize_filename("test.txt") == "test.txt"
        assert self.sanitizer.sanitize_filename("/path/to/file.txt") == "file.txt"
        assert self.sanitizer.sanitize_filename("../../etc/passwd") == "passwd"

    def test_ensure_within_sandbox(self):
        """Test ensure_within_sandbox method."""
        sandbox_path = self.temp_dir / "sandbox"
        sandbox_path.mkdir()
        workspace = sandbox_path / "workspace"
        workspace.mkdir()

        assert self.sanitizer.ensure_within_sandbox(workspace, sandbox_path) is True
        assert (
            self.sanitizer.ensure_within_sandbox(self.temp_dir / "outside", sandbox_path) is False
        )
