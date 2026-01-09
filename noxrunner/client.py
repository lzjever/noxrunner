"""
NoxRunner API Client

Main client class for interacting with NoxRunner-compatible sandbox execution backends.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from noxrunner.backend.base import SandboxBackend
from noxrunner.fileops.tar_handler import TarHandler


class NoxRunnerClient:
    """
    Client for NoxRunner-compatible sandbox execution backends.

    This client provides a Python interface to NoxRunner backends,
    allowing you to create, manage, and interact with sandbox execution environments.

    The client uses only Python standard library - no external dependencies required.
    This makes it suitable for environments where installing third-party packages
    is restricted or undesirable.

    Example:
        >>> from noxrunner import NoxRunnerClient
        >>> client = NoxRunnerClient("http://127.0.0.1:8080")
        >>> client.create_sandbox("my-session")
        >>> result = client.exec("my-session", ["python3", "--version"])
        >>> print(result["stdout"])
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30, local_test: bool = False):
        """
        Initialize the NoxRunner client.

        Args:
            base_url: Base URL of the NoxRunner backend (e.g., "http://127.0.0.1:8080").
                     If None or empty and local_test is False, will raise an error.
                     If None or empty and local_test is True, will use local sandbox mode.
            timeout: Request timeout in seconds (default: 30)
            local_test: If True, use local sandbox backend for offline testing.
                       WARNING: This executes commands in your local environment!

        Example:
            >>> client = NoxRunnerClient("http://127.0.0.1:8080", timeout=60)
            >>> # Or for local testing:
            >>> client = NoxRunnerClient(local_test=True)
        """
        # Create appropriate backend based on parameters
        if local_test:
            # Use new backend structure
            from noxrunner.backend.local import LocalBackend

            self._backend: SandboxBackend = LocalBackend()
        elif base_url is None or base_url.strip() == "":
            raise ValueError(
                "base_url is required unless local_test=True. "
                "For local testing, set local_test=True explicitly."
            )
        else:
            # Use new backend structure
            from noxrunner.backend.http import HTTPSandboxBackend

            self._backend: SandboxBackend = HTTPSandboxBackend(base_url, timeout)

        # Initialize tar handler for file operations (internal module)
        self._tar_handler = TarHandler()

    def health_check(self) -> bool:
        """
        Check if the NoxRunner backend is healthy.

        Returns:
            True if healthy, False otherwise

        Example:
            >>> if client.health_check():
            ...     print("Backend is healthy")
        """
        return self._backend.health_check()

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
        Create or ensure a sandbox execution environment exists.

        Args:
            session_id: Unique session identifier
            ttl_seconds: Time to live in seconds (default: 900)
            image: Container image (optional)
            cpu_limit: CPU limit (optional, e.g., "1")
            memory_limit: Memory limit (optional, e.g., "1Gi")
            ephemeral_storage_limit: Ephemeral storage limit (optional, e.g., "2Gi")

        Returns:
            Dict with 'podName' (or equivalent) and 'expiresAt'

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> result = client.create_sandbox("my-session", ttl_seconds=1800)
            >>> print(f"Sandbox: {result.get('podName')}")
        """
        return self._backend.create_sandbox(
            session_id, ttl_seconds, image, cpu_limit, memory_limit, ephemeral_storage_limit
        )

    def touch(self, session_id: str) -> bool:
        """
        Extend the TTL of a sandbox.

        Args:
            session_id: Session identifier

        Returns:
            True if successful

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> client.touch("my-session")
            True
        """
        return self._backend.touch(session_id)

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

        Args:
            session_id: Session identifier
            cmd: Command to execute (list of strings)
            workdir: Working directory (default: '/workspace')
            env: Environment variables (optional)
            timeout_seconds: Command timeout in seconds (default: 30)

        Returns:
            Dict with 'exitCode', 'stdout', 'stderr', 'durationMs'

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> result = client.exec("my-session", ["python3", "--version"])
            >>> print(result["stdout"])
        """
        return self._backend.exec(session_id, cmd, workdir, env, timeout_seconds)

    def exec_shell(
        self,
        session_id: str,
        command: str,
        workdir: str = "/workspace",
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        shell: str = "sh",
    ) -> dict:
        """
        Execute a shell command string in the sandbox.

        This is a convenience method that allows you to pass shell commands
        as a string (like you would type in a terminal), rather than as a list.
        The command is executed using sh -c (or bash -c if shell='bash').

        Args:
            session_id: Session identifier
            command: Shell command string to execute (e.g., "echo hello && ls -la")
            workdir: Working directory (default: '/workspace')
            env: Environment variables (optional)
            timeout_seconds: Command timeout in seconds (default: 30)
            shell: Shell to use ('sh' or 'bash', default: 'sh')

        Returns:
            Dict with 'exitCode', 'stdout', 'stderr', 'durationMs'

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails
            ValueError: If shell is not 'sh' or 'bash'

        Example:
            >>> # Simple command
            >>> result = client.exec_shell("my-session", "echo hello world")
            >>> print(result["stdout"])
            hello world

            >>> # Command with pipes and redirection
            >>> result = client.exec_shell("my-session", "ls -la | head -5")
            >>> print(result["stdout"])

            >>> # Command with environment variables
            >>> result = client.exec_shell(
            ...     "my-session",
            ...     "echo $MY_VAR",
            ...     env={"MY_VAR": "test_value"}
            ... )
            >>> print(result["stdout"])
            test_value

            >>> # Using bash instead of sh
            >>> result = client.exec_shell("my-session", "echo $BASH_VERSION", shell='bash')
        """
        if shell not in ("sh", "bash"):
            raise ValueError(f"shell must be 'sh' or 'bash', got: {shell}")

        # Convert shell command string to exec format: [shell, '-c', command]
        cmd = [shell, "-c", command]
        return self._backend.exec(session_id, cmd, workdir, env, timeout_seconds)

    def upload_files(
        self, session_id: str, files: Dict[str, Union[str, bytes]], dest: str = "/workspace"
    ) -> bool:
        """
        Upload files to the sandbox.

        Args:
            session_id: Session identifier
            files: Dict mapping file paths to content (str or bytes)
            dest: Destination directory (default: '/workspace')

        Returns:
            True if successful

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> client.upload_files("my-session", {
            ...     "script.py": "print('Hello')",
            ...     "data.txt": b"binary data"
            ... })
            True
        """
        return self._backend.upload_files(session_id, files, dest)

    def download_files(self, session_id: str, src: str = "/workspace") -> bytes:
        """
        Download files from the sandbox as a tar archive.

        Args:
            session_id: Session identifier
            src: Source directory (default: '/workspace')

        Returns:
            Tar archive as bytes

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> tar_data = client.download_files("my-session")
            >>> # Extract tar_data using tarfile
        """
        return self._backend.download_files(session_id, src)

    def download_workspace(
        self, session_id: str, local_dir: Union[str, Path], src: str = "/workspace"
    ) -> bool:
        """
        Download workspace from sandbox to local directory.

        This is a convenience method that downloads files from the sandbox
        and extracts them to a local directory. It handles tar extraction
        automatically, so you don't need to deal with tar archives directly.

        Args:
            session_id: Session identifier
            local_dir: Local directory path to extract files to
            src: Source directory in sandbox (default: '/workspace')

        Returns:
            True if successful, False otherwise

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails
            ValueError: If local_dir is invalid

        Example:
            >>> client.download_workspace("my-session", "./output")
            True
            >>> # Files from /workspace in sandbox are now in ./output
        """
        local_path = Path(local_dir)

        try:
            # Download tar archive from backend
            tar_data = self.download_files(session_id, src)

            if not tar_data or len(tar_data) == 0:
                return False

            # Use TarHandler to extract tar archive (internal module)
            file_count = self._tar_handler.extract_tar(
                tar_data=tar_data,
                dest=local_path,
                sandbox_path=None,
                allow_absolute=False,
            )
            return file_count > 0  # Success if files were extracted
        except Exception:
            return False

    def delete_sandbox(self, session_id: str) -> bool:
        """
        Delete a sandbox execution environment.

        Args:
            session_id: Session identifier

        Returns:
            True if successful

        Raises:
            :exc:`~noxrunner.exceptions.NoxRunnerHTTPError`: If request fails

        Example:
            >>> client.delete_sandbox("my-session")
            True
        """
        return self._backend.delete_sandbox(session_id)

    def wait_for_pod_ready(self, session_id: str, timeout: int = 30, interval: int = 2) -> bool:
        """
        Wait for the sandbox execution environment to be ready by polling with a simple command.

        Args:
            session_id: Session identifier
            timeout: Maximum time to wait in seconds (default: 30)
            interval: Polling interval in seconds (default: 2)

        Returns:
            True if sandbox is ready, False if timeout

        Example:
            >>> if client.wait_for_pod_ready("my-session", timeout=60):
            ...     print("Sandbox is ready")
        """
        return self._backend.wait_for_pod_ready(session_id, timeout, interval)
