"""
Backend implementations for NoxRunner.

This package contains different backend implementations:
- LocalBackend: Local filesystem backend for testing
- HTTPSandboxBackend: HTTP client backend for remote services
- Future: K8sBackend, DockerBackend
"""

from noxrunner.backend.base import SandboxBackend
from noxrunner.backend.http import HTTPSandboxBackend
from noxrunner.backend.local import LocalBackend

# Backward compatibility aliases
LocalSandboxBackend = LocalBackend
RemoteSandboxBackend = HTTPSandboxBackend

__all__ = [
    "SandboxBackend",
    "LocalBackend",
    "LocalSandboxBackend",  # Backward compatibility
    "HTTPSandboxBackend",
    "RemoteSandboxBackend",  # Backward compatibility
]
