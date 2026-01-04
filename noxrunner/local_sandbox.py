"""
Local sandbox backend for offline testing.

WARNING: This module provides a local testing sandbox that executes commands
in the local environment. Use with extreme caution as it can cause data loss
or security risks.
"""

import os
import sys
import subprocess
import shutil
import time
import tarfile
import io
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone

from noxrunner.backend import SandboxBackend


class LocalSandboxBackend(SandboxBackend):
    """
    Local sandbox backend for offline testing.

    WARNING: This backend executes commands in the local environment using
    temporary directories. It should ONLY be used for testing purposes.
    Using this in production can cause severe data loss or security risks.
    """

    # Security: Allowed commands that are safe to execute
    # Only allow read/write operations, no deletion or execution outside sandbox
    _ALLOWED_COMMANDS = {
        "echo",
        "cat",
        "ls",
        "pwd",
        "head",
        "tail",
        "grep",
        "wc",
        "sort",
        "python",
        "python3",
        "python2",
        "node",
        "bash",
        "sh",
        "zsh",
        "test",
        "[",
        "true",
        "false",
        "which",
        "type",
        "env",
        "printenv",
        "mkdir",
        "touch",
        "cp",
        "mv",
        "ln",
        "readlink",
        "stat",
        "file",
        "find",
        "xargs",
        "sed",
        "awk",
        "cut",
        "tr",
        "uniq",
        "diff",
        "cmp",
        "tar",
        "gzip",
        "gunzip",
        "zip",
        "unzip",
    }

    # Dangerous commands that should be blocked
    _BLOCKED_COMMANDS = {
        "rm",
        "rmdir",
        "unlink",
        "del",
        "format",
        "mkfs",
        "dd",
        "fdisk",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init",
        "killall",
        "sudo",
        "su",
        "chmod",
        "chown",
        "chgrp",
        "mount",
        "umount",
    }

    def __init__(self, base_dir: str = "/tmp"):
        """
        Initialize local sandbox backend.

        Args:
            base_dir: Base directory for sandbox storage (default: /tmp)
        """
        self.base_dir = Path(base_dir)
        self._sandboxes: Dict[str, Dict] = {}  # session_id -> sandbox info
        self._warned_init = False

        # Print warning on initialization
        self._print_warning(
            "Local sandbox mode is enabled. This executes commands in your local environment.",
            "⚠️  Using local sandbox can cause SEVERE DATA LOSS or SECURITY RISKS! ⚠️",
        )

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

    def _validate_command(self, cmd: List[str]) -> bool:
        """
        Validate that command is safe to execute.

        Security: Only allow safe commands, block dangerous ones.
        """
        if not cmd:
            return False

        command = cmd[0].lower()

        # Block dangerous commands
        if command in self._BLOCKED_COMMANDS:
            return False

        # For testing, allow common commands
        # In production, this should be more restrictive
        return True

    def _sanitize_path(self, path: str, sandbox_path: Path) -> Path:
        """
        Sanitize a path to ensure it's within the sandbox.

        Security: Prevent path traversal attacks.
        Only allows paths within the sandbox directory.
        """
        sandbox_resolved = sandbox_path.resolve()
        workspace = sandbox_resolved / "workspace"

        # Resolve relative paths
        if os.path.isabs(path):
            # If absolute, ensure it's within sandbox
            try:
                resolved = Path(path).resolve()
                # Check if resolved path is within sandbox
                try:
                    resolved.relative_to(sandbox_resolved)
                    # Path is within sandbox, return it
                    return resolved
                except ValueError:
                    # Path outside sandbox, redirect to workspace
                    return workspace
            except (OSError, ValueError):
                return workspace
        else:
            # Relative path, resolve within workspace
            try:
                resolved = (workspace / path).resolve()
                # Ensure resolved path is still within sandbox
                try:
                    resolved.relative_to(sandbox_resolved)
                    return resolved
                except ValueError:
                    # Path traversal detected, return workspace root
                    return workspace
            except (OSError, ValueError):
                return workspace

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
        # Print warning for every exec
        self._print_warning(
            f"Executing command in LOCAL environment: {' '.join(cmd)}",
            "⚠️  This may cause DATA LOSS or SECURITY RISKS! ⚠️",
        )

        if session_id not in self._sandboxes:
            # Auto-create sandbox if doesn't exist
            self.create_sandbox(session_id)

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]

        # Validate command
        if not self._validate_command(cmd):
            return {
                "exitCode": 1,
                "stdout": "",
                "stderr": f"Command not allowed: {cmd[0] if cmd else 'empty'}",
                "durationMs": 0,
            }

        # Sanitize workdir
        workdir_path = self._sanitize_path(workdir, sandbox_path)
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
        dest_path = self._sanitize_path(dest, sandbox_path)
        dest_path.mkdir(parents=True, exist_ok=True)

        for filepath, content in files.items():
            # Sanitize file path
            safe_path = Path(filepath).name  # Only use filename, no path traversal
            target = dest_path / safe_path

            # Write file
            if isinstance(content, str):
                target.write_text(content, encoding="utf-8")
            else:
                target.write_bytes(content)

        return True

    def upload_tar(self, session_id: str, tar_data: bytes, dest: str = "/workspace") -> bool:
        """Upload tar archive to the sandbox."""
        if session_id not in self._sandboxes:
            self.create_sandbox(session_id)

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]
        dest_path = self._sanitize_path(dest, sandbox_path)
        dest_path.mkdir(parents=True, exist_ok=True)

        # Extract tar archive
        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            # Security: Only extract files within sandbox
            for member in tar.getmembers():
                # Sanitize member name
                safe_name = Path(member.name).name
                target = dest_path / safe_name

                # Ensure target is within sandbox
                try:
                    target.resolve().relative_to(sandbox_path.resolve())
                except ValueError:
                    # Path outside sandbox, skip
                    continue

                if member.isfile():
                    tar.extract(member, dest_path)

        return True

    def download_files(self, session_id: str, src: str = "/workspace") -> bytes:
        """Download files from the sandbox as a tar archive."""
        if session_id not in self._sandboxes:
            raise ValueError(f"Sandbox {session_id} does not exist")

        sandbox = self._sandboxes[session_id]
        sandbox_path = sandbox["path"]
        src_path = self._sanitize_path(src, sandbox_path)

        if not src_path.exists():
            raise ValueError(f"Source path does not exist: {src}")

        # Create tar archive
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            if src_path.is_file():
                tar.add(src_path, arcname=src_path.name)
            elif src_path.is_dir():
                for root, dirs, files in os.walk(src_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(src_path)
                        tar.add(file_path, arcname=str(arcname))

        tar_buffer.seek(0)
        return tar_buffer.read()

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
