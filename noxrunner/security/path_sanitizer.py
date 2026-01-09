"""
Path sanitization for sandbox security.

This module provides path sanitization to prevent path traversal attacks
in sandbox environments.
"""

import os
from pathlib import Path


class PathSanitizer:
    """
    Sanitizes paths to ensure they're within the sandbox.

    Security: Prevents path traversal attacks by ensuring all paths
    are within the sandbox directory.
    """

    def sanitize(self, path: str, sandbox_path: Path, workspace_name: str = "workspace") -> Path:
        """
        Sanitize a path to ensure it's within the sandbox.

        Args:
            path: Path to sanitize (can be absolute or relative)
            sandbox_path: Base sandbox directory path
            workspace_name: Name of the workspace directory (default: "workspace")

        Returns:
            Sanitized Path object that is guaranteed to be within sandbox

        Security:
            - Prevents path traversal attacks (../)
            - Redirects paths outside sandbox to workspace root
            - Handles both absolute and relative paths
        """
        sandbox_resolved = sandbox_path.resolve()
        workspace = sandbox_resolved / workspace_name

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
            # Relative path, check for path traversal first
            if ".." in path or path.startswith("/"):
                # Path traversal detected, return workspace root
                return workspace

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

    def ensure_within_sandbox(self, path: Path, sandbox_path: Path) -> bool:
        """
        Check if a path is within the sandbox.

        Args:
            path: Path to check
            sandbox_path: Base sandbox directory path

        Returns:
            True if path is within sandbox, False otherwise
        """
        try:
            path.resolve().relative_to(sandbox_path.resolve())
            return True
        except ValueError:
            return False

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to prevent path traversal.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename (only the basename, no path components)
        """
        # Only use filename, no path traversal
        return Path(filename).name
