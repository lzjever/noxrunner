"""
Base backend interface for NoxRunner sandbox execution.

This module defines the abstract interface that all sandbox backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union


class SandboxBackend(ABC):
    """
    Abstract base class for sandbox execution backends.

    All backends (local, HTTP, k8s, docker, etc.) must implement this interface.
    This provides a unified API regardless of the underlying implementation.

    Architecture Note:
        This base class does NOT read environment variables or configuration files.
        All configuration must be passed through constructor parameters by client code.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize backend with configuration.

        Args:
            verbose: Enable verbose logging (default: False)
        """
        self.verbose = verbose

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
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
            ttl_seconds: Time to live in seconds (default: 900)
            image: Container image (optional)
            cpu_limit: CPU limit (optional, e.g., "1")
            memory_limit: Memory limit (optional, e.g., "1Gi")
            ephemeral_storage_limit: Ephemeral storage limit (optional, e.g., "2Gi")

        Returns:
            Dict with 'podName' (or equivalent) and 'expiresAt'
        """
        pass

    @abstractmethod
    def touch(self, session_id: str) -> bool:
        """
        Extend the TTL of a sandbox.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        pass

    @abstractmethod
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
        """
        pass

    @abstractmethod
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
        """
        pass

    @abstractmethod
    def download_files(self, session_id: str, src: str = "/workspace") -> bytes:
        """
        Download files from the sandbox as a tar archive.

        Args:
            session_id: Session identifier
            src: Source directory (default: '/workspace')

        Returns:
            Tar archive as bytes
        """
        pass

    @abstractmethod
    def delete_sandbox(self, session_id: str) -> bool:
        """
        Delete a sandbox.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def wait_for_pod_ready(self, session_id: str, timeout: int = 30, interval: int = 2) -> bool:
        """
        Wait for sandbox to be ready.

        Args:
            session_id: Session identifier
            timeout: Maximum time to wait in seconds (default: 30)
            interval: Polling interval in seconds (default: 2)

        Returns:
            True if sandbox is ready, False if timeout
        """
        pass
