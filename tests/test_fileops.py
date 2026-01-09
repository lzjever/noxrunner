"""
Tests for file operations modules.

Tests for tar handling.
"""

import tempfile
from pathlib import Path

from noxrunner.fileops.tar_handler import TarHandler


class TestTarHandler:
    """Test TarHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tar_handler = TarHandler()

    def test_create_tar_from_files(self):
        """Test creating tar archive from file dictionary."""
        files = {
            "test1.txt": "Hello, World!",
            "test2.txt": b"Binary data",
            "subdir/test3.txt": "Nested file",
        }

        tar_data = self.tar_handler.create_tar(files)
        assert len(tar_data) > 0

        # Verify it's a valid tar archive
        import io
        import tarfile

        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            members = tar.getnames()
            assert "test1.txt" in members
            assert "test2.txt" in members
            assert "subdir/test3.txt" in members

    def test_create_tar_from_directory(self):
        """Test creating tar archive from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test files
            (tmp_path / "file1.txt").write_text("content1")
            (tmp_path / "file2.txt").write_text("content2")
            (tmp_path / "subdir").mkdir()
            (tmp_path / "subdir" / "file3.txt").write_text("content3")

            tar_data = self.tar_handler.create_tar_from_directory(tmp_path, tmp_path)
            assert len(tar_data) > 0

    def test_extract_tar(self):
        """Test extracting tar archive."""
        # Create tar archive
        files = {
            "test1.txt": "Hello, World!",
            "test2.txt": "Another file",
        }
        tar_data = self.tar_handler.create_tar(files)

        # Extract to temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            file_count = self.tar_handler.extract_tar(tar_data, dest)

            assert file_count == 2
            assert (dest / "test1.txt").exists()
            assert (dest / "test2.txt").exists()
            assert (dest / "test1.txt").read_text() == "Hello, World!"
            assert (dest / "test2.txt").read_text() == "Another file"

    def test_extract_tar_with_security_check(self):
        """Test extracting tar archive with security checks."""
        # Create tar archive with potentially dangerous paths
        files = {
            "normal.txt": "Normal file",
            "/absolute.txt": "Absolute path",
            "../../etc/passwd": "Path traversal",
        }
        tar_data = self.tar_handler.create_tar(files)

        # Extract with security check
        # dest should be within sandbox_path for the check to work
        with tempfile.TemporaryDirectory() as sandbox_base:
            sandbox_path = Path(sandbox_base) / "sandbox"
            sandbox_path.mkdir()
            dest = sandbox_path / "workspace"
            dest.mkdir()

            file_count = self.tar_handler.extract_tar(tar_data, dest, sandbox_path=sandbox_path)

            # Only normal.txt should be extracted (dangerous paths are filtered)
            assert file_count == 1
            assert (dest / "normal.txt").exists()
            assert not (dest / "absolute.txt").exists()
            assert not (dest / "passwd").exists()

    def test_extract_empty_tar(self):
        """Test extracting empty tar archive."""
        tar_data = b""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            file_count = self.tar_handler.extract_tar(tar_data, dest)
            assert file_count == 0
