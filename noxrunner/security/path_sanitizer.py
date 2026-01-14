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
            # Relative path - need to handle carefully
            # Strategy: Normalize the path component by component to detect traversal
            try:
                # Split and normalize path parts manually
                path_parts = path.replace("\\", "/").split("/")
                normalized_parts = []

                for part in path_parts:
                    if part == "." or not part:
                        # Current directory or empty, skip
                        continue
                    elif part == "..":
                        # Parent directory - this is traversal
                        # For security, reject any path with .. in relative paths
                        return workspace
                    elif ".." in part:
                        # Path contains .. as part of a name (e.g., "file..txt")
                        # Only reject if it's ALL dots (repeated .. patterns)
                        # This catches "..", "...", "....", etc. but allows "file..txt"
                        if part.replace(".", "").replace("/", "").strip() == "":
                            # It's all dots, likely a traversal attempt
                            return workspace
                        # Otherwise it's a legitimate filename with .. in it
                        normalized_parts.append(part)
                    else:
                        # Normal path component
                        normalized_parts.append(part)

                # Reconstruct the safe path
                if normalized_parts:
                    resolved = workspace
                    for part in normalized_parts:
                        resolved = resolved / part

                    # Verify the final path is still within sandbox
                    try:
                        resolved.relative_to(sandbox_resolved)
                        return resolved
                    except ValueError:
                        # Something went wrong, fallback to workspace
                        return workspace
                else:
                    # Empty path after normalization
                    return workspace

            except (OSError, ValueError):
                # Fallback to workspace if anything fails
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
