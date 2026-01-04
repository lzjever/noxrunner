"""
NoxRunner - Python Client Library for Sandbox Execution Backends

A complete Python client library for interacting with NoxRunner-compatible
sandbox execution backends. Uses only Python standard library - zero external dependencies.

Example:
    >>> from noxrunner import NoxRunnerClient
    >>> client = NoxRunnerClient("http://127.0.0.1:8080")
    >>> client.create_sandbox("my-session")
    >>> result = client.exec("my-session", ["python3", "--version"])
    >>> print(result["stdout"])
"""

from noxrunner.exceptions import NoxRunnerError, NoxRunnerHTTPError
from noxrunner.client import NoxRunnerClient

__version__ = "1.0.0"
__author__ = "NoxRunner Team"
__all__ = ["NoxRunnerClient", "NoxRunnerError", "NoxRunnerHTTPError"]

