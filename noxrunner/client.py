"""
NoxRunner API Client

Main client class for interacting with NoxRunner-compatible sandbox execution backends.
"""

import json
import time
import tarfile
import io
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional, Union

from noxrunner.exceptions import NoxRunnerError, NoxRunnerHTTPError


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
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the NoxRunner client.
        
        Args:
            base_url: Base URL of the NoxRunner backend (e.g., "http://127.0.0.1:8080")
            timeout: Request timeout in seconds (default: 30)
        
        Example:
            >>> client = NoxRunnerClient("http://127.0.0.1:8080", timeout=60)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Union[dict, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
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
                req_data = json.dumps(data).encode('utf-8')
                req_headers['Content-Type'] = content_type or 'application/json'
            elif isinstance(data, bytes):
                # Binary data
                req_data = data
                req_headers['Content-Type'] = content_type or 'application/octet-stream'
        
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
            except:
                pass
            raise NoxRunnerHTTPError(
                e.code,
                str(e),
                error_body.decode('utf-8', errors='ignore')
            )
        except urllib.error.URLError as e:
            raise NoxRunnerError(f"Network error: {e}")
        except Exception as e:
            raise NoxRunnerError(f"Unexpected error: {e}")
    
    def _json_request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None
    ) -> dict:
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
            error_msg = response_body.decode('utf-8', errors='ignore')
            raise NoxRunnerHTTPError(status_code, f"Request failed", error_msg)
        
        if not response_body:
            return {}
        
        try:
            return json.loads(response_body.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise NoxRunnerError(f"Invalid JSON response: {e}")
    
    def health_check(self) -> bool:
        """
        Check if the NoxRunner backend is healthy.
        
        Returns:
            True if healthy, False otherwise
        
        Example:
            >>> if client.health_check():
            ...     print("Backend is healthy")
        """
        try:
            status_code, response_body = self._request('GET', '/healthz')
            return status_code == 200 and b'OK' in response_body
        except:
            return False
    
    def create_sandbox(
        self,
        session_id: str,
        ttl_seconds: int = 900,
        image: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None,
        ephemeral_storage_limit: Optional[str] = None
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
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> result = client.create_sandbox("my-session", ttl_seconds=1800)
            >>> print(f"Sandbox: {result.get('podName')}")
        """
        data = {
            'ttlSeconds': ttl_seconds
        }
        if image:
            data['image'] = image
        if cpu_limit:
            data['cpuLimit'] = cpu_limit
        if memory_limit:
            data['memoryLimit'] = memory_limit
        if ephemeral_storage_limit:
            data['ephemeralStorageLimit'] = ephemeral_storage_limit
        
        return self._json_request('PUT', f'/v1/sandboxes/{session_id}', data)
    
    def touch(self, session_id: str) -> bool:
        """
        Extend the TTL of a sandbox.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        
        Raises:
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> client.touch("my-session")
            True
        """
        try:
            status_code, _ = self._request('POST', f'/v1/sandboxes/{session_id}/touch')
            return status_code == 200
        except NoxRunnerHTTPError as e:
            if e.status_code == 200:
                return True
            raise
    
    def exec(
        self,
        session_id: str,
        cmd: List[str],
        workdir: str = '/workspace',
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30
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
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> result = client.exec("my-session", ["python3", "--version"])
            >>> print(result["stdout"])
        """
        data = {
            'cmd': cmd,
            'workdir': workdir,
            'timeoutSeconds': timeout_seconds
        }
        if env:
            data['env'] = env
        
        return self._json_request('POST', f'/v1/sandboxes/{session_id}/exec', data)
    
    def upload_files(
        self,
        session_id: str,
        files: Dict[str, Union[str, bytes]],
        dest: str = '/workspace'
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
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> client.upload_files("my-session", {
            ...     "script.py": "print('Hello')",
            ...     "data.txt": b"binary data"
            ... })
            True
        """
        # Create tar archive in memory
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            for filepath, content in files.items():
                # Convert string to bytes if needed
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                else:
                    content_bytes = content
                
                # Create tar info
                info = tarfile.TarInfo(name=filepath)
                info.size = len(content_bytes)
                tar.addfile(info, io.BytesIO(content_bytes))
        
        tar_buffer.seek(0)
        tar_data = tar_buffer.read()
        
        # Upload
        path = f'/v1/sandboxes/{session_id}/files/upload?{urllib.parse.urlencode({"dest": dest})}'
        try:
            status_code, _ = self._request(
                'POST',
                path,
                data=tar_data,
                content_type='application/x-tar'
            )
            return status_code == 200
        except NoxRunnerHTTPError as e:
            if e.status_code == 200:
                return True
            raise
    
    def download_files(
        self,
        session_id: str,
        src: str = '/workspace'
    ) -> bytes:
        """
        Download files from the sandbox as a tar archive.
        
        Args:
            session_id: Session identifier
            src: Source directory (default: '/workspace')
        
        Returns:
            Tar archive as bytes
        
        Raises:
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> tar_data = client.download_files("my-session")
            >>> # Extract tar_data using tarfile
        """
        path = f'/v1/sandboxes/{session_id}/files/download?{urllib.parse.urlencode({"src": src})}'
        status_code, response_body = self._request('GET', path)
        
        if not (200 <= status_code < 300):
            raise NoxRunnerHTTPError(status_code, "Download failed")
        
        return response_body
    
    def delete_sandbox(self, session_id: str) -> bool:
        """
        Delete a sandbox execution environment.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        
        Raises:
            NoxRunnerHTTPError: If request fails
        
        Example:
            >>> client.delete_sandbox("my-session")
            True
        """
        try:
            status_code, _ = self._request('DELETE', f'/v1/sandboxes/{session_id}')
            return status_code in (200, 204)
        except NoxRunnerHTTPError as e:
            if e.status_code in (200, 204):
                return True
            raise
    
    def wait_for_pod_ready(
        self,
        session_id: str,
        timeout: int = 30,
        interval: int = 2
    ) -> bool:
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
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = self.exec(
                    session_id,
                    ['echo', 'ready'],
                    timeout_seconds=5
                )
                if result.get('stdout', '').strip() == 'ready':
                    return True
            except:
                # Sandbox might not be ready yet, continue polling
                pass
            
            time.sleep(interval)
        
        return False

