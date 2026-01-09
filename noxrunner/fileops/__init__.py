"""
File operations utilities for NoxRunner backends.

This is an INTERNAL module used by backends and client.
Users should not import from this module directly.

Internal utilities:
- TarHandler: Handles tar archive creation and extraction
"""

from noxrunner.fileops.tar_handler import TarHandler

# Internal module - not part of public API
__all__ = [
    "TarHandler",
]
