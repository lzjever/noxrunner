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
                # Security: Skip absolute paths and paths with .. unless allowed
                if not allow_absolute and (member.name.startswith("/") or ".." in member.name):
                    continue

                # Skip directories (they will be created automatically)
                if member.isdir():
                    continue

                # Get target path
                target_path = dest / member.name

                # Security check: Ensure target is within dest (or sandbox if provided)
                # First check if member.name itself is safe
                if ".." in member.name or member.name.startswith("/"):
                    # Path traversal in name, skip
                    continue

                if sandbox_path:
                    try:
                        target_path.resolve().relative_to(sandbox_path.resolve())
                    except ValueError:
                        # Path outside sandbox, skip
                        continue
                else:
                    # Ensure target is within dest
                    try:
                        target_path.resolve().relative_to(dest.resolve())
                    except ValueError:
                        # Path outside dest, skip
                        continue

                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Extract file with filter for Python 3.12+
                # Use 'data' filter for security (restricts symlinks, devices, etc.)
                # We've already done path traversal checks above
                if sys.version_info >= (3, 12):
                    tar.extract(member, dest, filter="data")
                else:
                    tar.extract(member, dest)
                file_count += 1

        return file_count
