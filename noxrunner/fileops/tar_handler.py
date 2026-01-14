"""
Tar archive handling utilities.

This module provides utilities for creating and extracting tar archives
used in file synchronization between local and sandbox environments.
"""

import io
import sys
import tarfile
from pathlib import Path
from typing import Dict, Optional, Union


class TarHandler:
    """
    Handles tar archive creation and extraction.

    This class provides methods to create tar archives from file dictionaries
    and extract tar archives to directories, with security checks.
    """

    def create_tar(self, files: Dict[str, Union[str, bytes]]) -> bytes:
        """
        Create a tar archive from a dictionary of files.

        Args:
            files: Dictionary mapping file paths to content (str or bytes)

        Returns:
            Tar archive as bytes (gzip compressed)
        """
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            for filepath, content in files.items():
                # Convert string to bytes if needed
                if isinstance(content, str):
                    content_bytes = content.encode("utf-8")
                else:
                    content_bytes = content

                # Create tar info
                info = tarfile.TarInfo(name=filepath)
                info.size = len(content_bytes)
                tar.addfile(info, io.BytesIO(content_bytes))

        tar_buffer.seek(0)
        return tar_buffer.read()

    def create_tar_from_directory(self, directory: Path, src: Path) -> bytes:
        """
        Create a tar archive from a directory.

        Args:
            directory: Directory to archive
            src: Source path (for relative path calculation)

        Returns:
            Tar archive as bytes (gzip compressed)
        """
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            if directory.is_file():
                tar.add(directory, arcname=directory.name)
            elif directory.is_dir():
                import os

                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(src)
                        tar.add(file_path, arcname=str(arcname))

        tar_buffer.seek(0)
        return tar_buffer.read()

    def _is_safe_member(self, member, dest: Path) -> bool:
        """
        Check if a tar member is safe to extract.

        This method performs security checks to prevent:
        - Path traversal attacks
        - Symbolic link attacks
        - Absolute path escapes

        Args:
            member: Tar member to check
            dest: Destination directory

        Returns:
            True if member is safe to extract, False otherwise
        """
        # Check for absolute paths
        if member.name.startswith("/"):
            return False

        # Check for path traversal (more thorough than simple ".." check)
        path_parts = member.name.replace("\\", "/").split("/")
        for part in path_parts:
            if part == "..":
                return False

        # Check if the extracted path would be outside destination
        target_path = dest / member.name
        try:
            target_path.resolve().relative_to(dest.resolve())
        except ValueError:
            return False

        # For symlinks, check the link target
        if member.issym() or member.islnk():
            # Don't allow absolute symlinks
            if member.linkname.startswith("/"):
                return False
            # Don't allow symlinks with path traversal
            linkname_parts = member.linkname.replace("\\", "/").split("/")
            for part in linkname_parts:
                if part == "..":
                    return False

        return True

    def extract_tar(
        self,
        tar_data: bytes,
        dest: Path,
        sandbox_path: Optional[Path] = None,
        allow_absolute: bool = False,
    ) -> int:
        """
        Extract a tar archive to a directory.

        Args:
            tar_data: Tar archive data (bytes)
            dest: Destination directory
            sandbox_path: Optional sandbox path for security checks
            allow_absolute: Whether to allow absolute paths (default: False)

        Returns:
            Number of files extracted
        """
        if not tar_data or len(tar_data) == 0:
            return 0

        dest.mkdir(parents=True, exist_ok=True)
        file_count = 0

        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            for member in tar.getmembers():
                # Skip directories (they will be created automatically)
                if member.isdir():
                    continue

                # Security check for all Python versions
                # Perform comprehensive safety checks before extraction
                if not allow_absolute and not self._is_safe_member(member, dest):
                    continue

                # Additional sandbox check if provided
                if sandbox_path:
                    target_path = dest / member.name
                    try:
                        target_path.resolve().relative_to(sandbox_path.resolve())
                    except ValueError:
                        # Path outside sandbox, skip
                        continue

                # Create parent directories
                target_path = dest / member.name
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Extract with appropriate filter based on Python version
                # Python 3.12+: Use built-in 'data' filter
                # Python <3.12: Manual checks already done above
                if sys.version_info >= (3, 12):
                    tar.extract(member, dest, filter="data")
                else:
                    # Manual security checks already performed above
                    tar.extract(member, dest)
                file_count += 1

        return file_count
