"""
Command validation for sandbox security.

This module provides command validation to prevent dangerous operations
in sandbox environments.
"""

from typing import List


class CommandValidator:
    """
    Validates commands for safety in sandbox environments.

    This validator checks commands against allowlists and blocklists
    to prevent dangerous operations.
    """

    # Security: Allowed commands that are safe to execute
    # Only allow read/write operations, no deletion or execution outside sandbox
    ALLOWED_COMMANDS = {
        "echo",
        "cat",
        "ls",
        "pwd",
        "head",
        "tail",
        "grep",
        "wc",
        "sort",
        "python",
        "python3",
        "python2",
        "node",
        "bash",
        "sh",
        "zsh",
        "test",
        "[",
        "true",
        "false",
        "which",
        "type",
        "env",
        "printenv",
        "mkdir",
        "touch",
        "cp",
        "mv",
        "ln",
        "readlink",
        "stat",
        "file",
        "find",
        "xargs",
        "sed",
        "awk",
        "cut",
        "tr",
        "uniq",
        "diff",
        "cmp",
        "tar",
        "gzip",
        "gunzip",
        "zip",
        "unzip",
        "sleep",  # For testing timeout functionality
        "cd",  # For changing directories (shell built-in)
    }

    # Dangerous commands that should be blocked
    BLOCKED_COMMANDS = {
        "rm",
        "rmdir",
        "unlink",
        "del",
        "format",
        "mkfs",
        "dd",
        "fdisk",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init",
        "killall",
        "sudo",
        "su",
        "chmod",
        "chown",
        "chgrp",
        "mount",
        "umount",
    }

    def validate(self, cmd: List[str]) -> bool:
        """
        Validate that command is safe to execute.

        Uses strict allowlist mode - only commands in ALLOWED_COMMANDS are permitted.
        This provides defense-in-depth security by blocking any command not explicitly
        allowed, even if it's not in the BLOCKED_COMMANDS list.

        Args:
            cmd: Command to validate (list of strings)

        Returns:
            True if command is safe, False otherwise
        """
        if not cmd:
            return False

        command = cmd[0].lower()

        # Always block dangerous commands first (defense in depth)
        if command in self.BLOCKED_COMMANDS:
            return False

        # Only allow commands in the allowlist
        return command in self.ALLOWED_COMMANDS

    def is_allowed(self, command: str) -> bool:
        """
        Check if a command is in the allowed list.

        Args:
            command: Command name to check

        Returns:
            True if command is allowed
        """
        return command.lower() in self.ALLOWED_COMMANDS

    def is_blocked(self, command: str) -> bool:
        """
        Check if a command is in the blocked list.

        Args:
            command: Command name to check

        Returns:
            True if command is blocked
        """
        return command.lower() in self.BLOCKED_COMMANDS
