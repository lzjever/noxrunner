"""
HTTP client backend for NoxRunner sandbox execution.

This backend communicates with a remote NoxRunner-compatible API via HTTP.
The remote service may be implemented using Kubernetes, Docker, or other technologies.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Union

from noxrunner.backend.base import SandboxBackend
from noxrunner.exceptions import NoxRunnerError, NoxRunnerHTTPError
from noxrunner.fileops.tar_handler import TarHandler


class HTTPSandboxBackend(SandboxBackend):
    """
    HTTP client backend for NoxRunner sandbox execution.

    This backend communicates with a remote NoxRunner-compatible API via HTTP.
    The remote service may be implemented using Kubernetes, Docker, or other technologies.

    This backend acts as an HTTP client and does not implement the sandbox itself.
    It connects to a remote service that provides the actual sandbox implementation.

    Architecture Note:
        This backend does NOT read environment variables for configuration.
        All configuration must be passed via constructor parameters.
    """

    def __init__(self, base_url: str, timeout: int = 30, verbose: bool = False):
        """
        Initialize the HTTP backend.

        Args:
            base_url: Base URL of the NoxRunner backend (e.g., "http://127.0.0.1:8080")
            timeout: Request timeout in seconds (default: 30)
            verbose: Enable verbose logging (default: False)
        """
        # Initialize parent class with verbose parameter
        super().__init__(verbose=verbose)

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.tar_handler = TarHandler()

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Union[dict, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> tuple[int, bytes]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/v1/sandboxes/{id}")
            data: Request data (dict for JSON, bytes for binary)
            headers: Additional headers
            content_type: Content-Type header

        Returns:
            Tuple of (status_code, response_body)

        Raises:
            NoxRunnerHTTPError: If HTTP request fails
            NoxRunnerError: If network or other error occurs
        """
        url = f"{self.base_url}{path}"

        # Prepare headers
        req_headers = {}
        if headers:
            req_headers.update(headers)

        # Prepare request data
        req_data = None
        if data is not None:
            if isinstance(data, dict):
                # JSON data
                req_data = json.dumps(data).encode("utf-8")
                req_headers["Content-Type"] = content_type or "application/json"
            elif isinstance(data, bytes):
                # Binary data
                req_data = data
                req_headers["Content-Type"] = content_type or "application/octet-stream"

        # Create request
        req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                response_body = response.read()
                return status_code, response_body
        except urllib.error.HTTPError as e:
            # Read error response body
            error_body = b""
            try:
                error_body = e.read()
            except Exception:
                pass
            raise NoxRunnerHTTPError(e.code, str(e), error_body.decode("utf-8", errors="ignore"))
        except urllib.error.URLError as e:
            raise NoxRunnerError(f"Network error: {e}")
        except Exception as e:
            raise NoxRunnerError(f"Unexpected error: {e}")

    def _json_request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        """
        Make a JSON request and return parsed JSON response.

        Args:
            method: HTTP method
            path: API path
            data: Request data (dict)

        Returns:
            Parsed JSON response as dict

        Raises:
            NoxRunnerHTTPError: If request fails
            NoxRunnerError: If JSON parsing fails
        """
        status_code, response_body = self._request(method, path, data)

        if not (200 <= status_code < 300):
            error_msg = response_body.decode("utf-8", errors="ignore")
            raise NoxRunnerHTTPError(status_code, "Request failed", error_msg)

        if not response_body:
            return {}

        try:
            return json.loads(response_body.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise NoxRunnerError(f"Invalid JSON response: {e}")

    def health_check(self) -> bool:
        """Check if the backend is healthy."""
        try:
            status_code, response_body = self._request("GET", "/healthz")
            return status_code == 200 and b"OK" in response_body
        except Exception:
            return False

    def create_sandbox(
        self,
        session_id: str,
        ttl_seconds: int = 900,
        image: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None,
        ephemeral_storage_limit: Optional[str] = None,
    ) -> dict:
        """Create or ensure a sandbox exists."""
        data = {"ttlSeconds": ttl_seconds}
        if image:
            data["image"] = image
        if cpu_limit:
            data["cpuLimit"] = cpu_limit
        if memory_limit:
            data["memoryLimit"] = memory_limit
        if ephemeral_storage_limit:
            data["ephemeralStorageLimit"] = ephemeral_storage_limit

        return self._json_request("PUT", f"/v1/sandboxes/{session_id}", data)

    def touch(self, session_id: str) -> bool:
        """Extend the TTL of a sandbox."""
        status_code, _ = self._request("POST", f"/v1/sandboxes/{session_id}/touch")
        return status_code == 200

    def exec(
        self,
        session_id: str,
        cmd: List[str],
        workdir: str = "/workspace",
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
    ) -> dict:
        """Execute a command in the sandbox."""
        data = {"cmd": cmd, "workdir": workdir, "timeoutSeconds": timeout_seconds}
        if env:
            data["env"] = env

        return self._json_request("POST", f"/v1/sandboxes/{session_id}/exec", data)

    def upload_files(
        self, session_id: str, files: Dict[str, Union[str, bytes]], dest: str = "/workspace"
    ) -> bool:
        """Upload files to the sandbox."""
        # Use TarHandler to create tar archive
        tar_data = self.tar_handler.create_tar(files)

        # Upload
        path = f"/v1/sandboxes/{session_id}/files/upload?{urllib.parse.urlencode({'dest': dest})}"
        status_code, _ = self._request(
            "POST", path, data=tar_data, content_type="application/x-tar"
        )
        return status_code == 200

    def download_files(self, session_id: str, src: str = "/workspace") -> bytes:
        """Download files from the sandbox as a tar archive."""
        path = f"/v1/sandboxes/{session_id}/files/download?{urllib.parse.urlencode({'src': src})}"
        status_code, response_body = self._request("GET", path)

        if not (200 <= status_code < 300):
            raise NoxRunnerHTTPError(status_code, "Download failed")

        return response_body

    def delete_sandbox(self, session_id: str) -> bool:
        """Delete a sandbox."""
        status_code, _ = self._request("DELETE", f"/v1/sandboxes/{session_id}")
        return status_code in (200, 204)

    def wait_for_pod_ready(self, session_id: str, timeout: int = 30, interval: int = 2) -> bool:
        """Wait for sandbox to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = self.exec(session_id, ["echo", "ready"], timeout_seconds=5)
                if result.get("stdout", "").strip() == "ready":
                    return True
            except Exception:
                # Sandbox might not be ready yet, continue polling
                pass

            time.sleep(interval)

        return False
