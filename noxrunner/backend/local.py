"""
Local filesystem backend for NoxRunner sandbox execution.

WARNING: This backend executes commands in the local environment.
Use with extreme caution as it can cause data loss or security risks.
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

from noxrunner.backend.base import SandboxBackend
from noxrunner.fileops.tar_handler import TarHandler
from noxrunner.security.command_validator import CommandValidator
from noxrunner.security.path_sanitizer import PathSanitizer


class LocalBackend(SandboxBackend):
    """
    Local filesystem backend for offline testing.

    WARNING: This backend executes commands in the local environment using
    temporary directories. It should ONLY be used for testing purposes.
    Using this in production can cause severe data loss or security risks.

    Architecture Note:
        This backend does NOT read environment variables for configuration.
        All configuration (including verbose mode) must be passed via constructor.
    """

    def __init__(self, base_dir: str = "/tmp", verbose: bool = False):
        """
        Initialize local sandbox backend.

        Args:
            base_dir: Base directory for sandbox storage (default: /tmp)
            verbose: Enable verbose logging (default: False)
        """
        # Initialize parent class with verbose parameter
        super().__init__(verbose=verbose)

        self.base_dir = Path(base_dir)
        self._sandboxes: Dict[str, Dict] = {}  # session_id -> sandbox info

        # Initialize security and file operation utilities
        self.validator = CommandValidator()
        self.sanitizer = PathSanitizer()
        self.tar_handler = TarHandler()

        # Track if warning has been shown (for exec warnings)
        self._exec_warning_shown = False

        # Print warning on initialization
        self._print_warning(
            "Local sandbox mode is enabled. This executes commands in your local environment.",
            "⚠️  Using local sandbox can cause SEVERE DATA LOSS or SECURITY RISKS! ⚠️",
        )

        # Auto-cleanup expired sandboxes on initialization
        self._cleanup_expired()

    def _print_warning(self, message: str, critical: Optional[str] = None):
        """Print a warning message to stderr."""
        warning_prefix = "\033[91m\033[1m⚠️  WARNING\033[0m\033[91m"
        if critical:
            warning_prefix = "\033[91m\033[1m🚨 CRITICAL WARNING\033[0m\033[91m"

        # Print with clear formatting
        print("", file=sys.stderr)  # Empty line for visibility
        print(f"{warning_prefix}: {message}\033[0m", file=sys.stderr)
        if critical:
            print(f"\033[91m\033[1m{critical}\033[0m", file=sys.stderr)
        print("", file=sys.stderr)  # Empty line for visibility

    def _cleanup_expired(self):
        """
        Remove expired sandbox directories.

        This method cleans up:
        1. Tracked sandboxes whose TTL has expired
        2. Orphaned sandbox directories (no longer tracked)
        """
        now = datetime.now(timezone.utc)

        # Clean up expired tracked sandboxes
        expired_sessions = []
        for session_id, info in self._sandboxes.items():
            if info.get("expires_at") and info["expires_at"] < now:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            try:
                self.delete_sandbox(session_id)
            except Exception:
                pass  # Best effort cleanup

        # Scan for orphaned sandbox directories
        if self.base_dir.exists():
            for sandbox_dir in self.base_dir.glob("noxrunner_sandbox_*"):
                # Extract session_id from directory name
                session_id = sandbox_dir.name.replace("noxrunner_sandbox_", "")
                # Check if it's tracked
                if session_id not in self._sandboxes:
                    # Orphaned directory, remove it
                    try:
                        shutil.rmtree(sandbox_dir)
                    except Exception:
                        pass  # Best effort cleanup

    def _get_sandbox_path(self, session_id: str) -> Path:
        """Get the sandbox directory path for a session."""
        # Sanitize session_id to prevent path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            safe_id = "default"
        return self.base_dir / f"noxrunner_sandbox_{safe_id}"

    def _ensure_sandbox(self, session_id: str) -> Path:
        """Ensure sandbox directory exists and return its path."""
        sandbox_path = self._get_sandbox_path(session_id)
        sandbox_path.mkdir(parents=True, exist_ok=True)

        # Create workspace directory
        workspace = sandbox_path / "workspace"
        workspace.mkdir(exist_ok=True)

        return sandbox_path

    def health_check(self) -> bool:
        """Check if the local sandbox backend is healthy."""
        return True

    def create_sandbox(
        self,
        session_id: str,
        ttl_seconds: int = 900,
        image: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None,
        ephemeral_storage_limit: Optional[str] = None,
    ) -> dict:
        """
        Create or ensure a sandbox exists.

        Args:
            session_id: Unique session identifier
            ttl_seconds: Time to live in seconds
            image: Container image (ignored in local mode)
            cpu_limit: CPU limit (ignored in local mode)
            memory_limit: Memory limit (ignored in local mode)
            ephemeral_storage_limit: Storage limit (ignored in local mode)

        Returns:
            Dict with 'podName' and 'expiresAt'
        """
        sandbox_path = self._ensure_sandbox(session_id)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        self._sandboxes[session_id] = {
            "path": sandbox_path,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "ttl_seconds": ttl_seconds,
        }

        return {"podName": f"local-{session_id}", "expiresAt": expires_at.isoformat() + "Z"}

    def touch(self, session_id: str) -> bool:
        """Extend the TTL of a sandbox."""
        if session_id not in self._sandboxes:
            # Create if doesn't exist
            self.create_sandbox(session_id)
            return True

        sandbox = self._sandboxes[session_id]
        ttl = sandbox.get("ttl_seconds", 900)
        sandbox["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Trigger cleanup to remove any other expired sandboxes
        self._cleanup_expired()

        return True

    def exec(
        self,
        session_id: str,
        cmd: List[str],
        workdir: str = "/workspace",
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
    ) -> dict:
        """
        Execute a command in the sandbox.

        WARNING: This executes commands in the local environment!
        """
        # Print warning only once (first exec call)
        if not self._exec_warning_shown:
            self._print_warning(
                f"Executing command in LOCAL environment: {' '.join(cmd)}",
                "⚠️  This may cause DATA LOSS or SECURITY RISKS! ⚠️",
            )
            self._exec_warning_shown = True
        elif self.verbose:
            # In verbose mode, show each command
            print(f"\033[90m[noxrunner] Executing: {' '.join(cmd)}\033[0m", file=sys.stderr)

        if session_id not in self._sandboxes:
            # Auto-create sandbox if doesn't exist
            self.create_sandbox(session_id)

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]

        # Validate command using CommandValidator
        if not self.validator.validate(cmd):
            return {
                "exitCode": 1,
                "stdout": "",
                "stderr": f"Command not allowed: {cmd[0] if cmd else 'empty'}",
                "durationMs": 0,
            }

        # Sanitize workdir using PathSanitizer
        workdir_path = self.sanitizer.sanitize(workdir, sandbox_path)
        workdir_path.mkdir(parents=True, exist_ok=True)

        # Prepare environment
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        # Change to sandbox workspace for safety
        original_cwd = os.getcwd()
        try:
            os.chdir(str(workdir_path))

            start_time = time.time()

            # Execute command with timeout
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    env=exec_env,
                    cwd=str(workdir_path),
                    # Security: Don't allow shell injection
                    shell=False,
                )
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired:
                exit_code = 124  # Standard timeout exit code
                stdout = ""
                stderr = f"Command timed out after {timeout_seconds} seconds"
            except FileNotFoundError:
                exit_code = 127  # Command not found
                stdout = ""
                stderr = f"Command not found: {cmd[0]}"
            except Exception as e:
                exit_code = 1
                stdout = ""
                stderr = f"Execution error: {str(e)}"

            duration_ms = int((time.time() - start_time) * 1000)

            return {
                "exitCode": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "durationMs": duration_ms,
            }
        finally:
            os.chdir(original_cwd)

    def upload_files(
        self, session_id: str, files: Dict[str, Union[str, bytes]], dest: str = "/workspace"
    ) -> bool:
        """Upload files to the sandbox."""
        if session_id not in self._sandboxes:
            self.create_sandbox(session_id)

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]
        dest_path = self.sanitizer.sanitize(dest, sandbox_path)
        dest_path.mkdir(parents=True, exist_ok=True)

        for filepath, content in files.items():
            # Sanitize file path - handle relative paths with subdirectories
            # First check if it's a relative path with subdirectories
            if "/" in filepath or "\\" in filepath:
                # Path contains directory separators, sanitize as relative path
                # Remove any leading slashes and path traversal attempts
                clean_path = filepath.lstrip("/").replace("\\", "/")
                if ".." in clean_path or clean_path.startswith("/"):
                    # Path traversal detected, use filename only
                    safe_path = Path(self.sanitizer.sanitize_filename(filepath))
                else:
                    # Safe relative path, use it
                    safe_path = Path(clean_path)
            else:
                # Simple filename, use sanitize_filename
                safe_path = Path(self.sanitizer.sanitize_filename(filepath))

            target = dest_path / safe_path
            # Create parent directories
            target.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            if isinstance(content, str):
                target.write_text(content, encoding="utf-8")
            else:
                target.write_bytes(content)

        return True

    def download_files(self, session_id: str, src: str = "/workspace") -> bytes:
        """Download files from the sandbox as a tar archive."""
        if session_id not in self._sandboxes:
            raise ValueError(f"Sandbox {session_id} does not exist")

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]
        src_path = self.sanitizer.sanitize(src, sandbox_path)

        if not src_path.exists():
            raise ValueError(f"Source path does not exist: {src}")

        # Use TarHandler to create tar archive from directory
        return self.tar_handler.create_tar_from_directory(src_path, src_path)

    def delete_sandbox(self, session_id: str) -> bool:
        """
        Delete a sandbox.

        This removes the entire /tmp/{sandbox_id} directory.
        """
        if session_id not in self._sandboxes:
            return False

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]

        # Remove entire sandbox directory
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)

        del self._sandboxes[session_id]
        return True

    def wait_for_pod_ready(self, session_id: str, timeout: int = 30, interval: int = 2) -> bool:
        """Wait for sandbox to be ready."""
        if session_id not in self._sandboxes:
            self.create_sandbox(session_id)

        # Local sandbox is always ready immediately
        return True
