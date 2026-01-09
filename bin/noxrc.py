#!/usr/bin/env python3
"""
NoxRunner CLI Tool

A command-line interface for interacting with the NoxRunner API.
Uses only standard library - no external dependencies.
"""

import sys
import os
import argparse
import tarfile
import io
import shlex
from pathlib import Path
from typing import Optional

# Import the API client
from noxrunner import NoxRunnerClient, NoxRunnerError


# ANSI color codes
class Colors:
    """ANSI color escape codes."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def colorize(text: str, color: str) -> str:
    """Add color to text if output is a TTY."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def success(msg: str):
    """Print success message."""
    print(colorize(f"✓ {msg}", Colors.GREEN))


def error(msg: str):
    """Print error message."""
    print(colorize(f"✗ {msg}", Colors.RED), file=sys.stderr)


def warning(msg: str):
    """Print warning message."""
    print(colorize(f"⚠ {msg}", Colors.YELLOW))


def info(msg: str):
    """Print info message."""
    print(colorize(f"ℹ {msg}", Colors.BLUE))


def get_base_url() -> Optional[str]:
    """Get base URL from environment or default."""
    url = os.environ.get("NOXRUNNER_BASE_URL", "http://127.0.0.1:8080")
    # Return None if explicitly set to empty string (for local test)
    if url == "":
        return None
    return url


def create_client(args) -> NoxRunnerClient:
    """Create NoxRunnerClient from args."""
    return NoxRunnerClient(base_url=args.base_url, timeout=args.timeout, local_test=args.local_test)


def cmd_health(args):
    """Health check command."""
    client = create_client(args)
    try:
        if client.health_check():
            success("Manager is healthy")
            return 0
        else:
            error("Manager is not healthy")
            return 1
    except NoxRunnerError as e:
        error(f"Health check failed: {e}")
        return 1


def cmd_create(args):
    """Create sandbox command."""
    client = create_client(args)
    try:
        result = client.create_sandbox(
            args.session_id,
            ttl_seconds=args.ttl,
            image=args.image,
            cpu_limit=args.cpu,
            memory_limit=args.mem,
            ephemeral_storage_limit=args.storage,
        )
        success(f"Sandbox created: {result.get('podName')}")
        if args.wait:
            info("Waiting for pod to be ready...")
            if client.wait_for_pod_ready(args.session_id, timeout=args.wait_timeout):
                success("Pod is ready")
            else:
                warning("Pod did not become ready within timeout")
        return 0
    except NoxRunnerError as e:
        error(f"Failed to create noxrunner: {e}")
        return 1


def cmd_exec(args):
    """Execute command command."""
    client = create_client(args)
    try:
        # Parse environment variables
        env = None
        if args.env:
            env = {}
            for env_var in args.env:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env[key] = value
                else:
                    warning(f"Invalid env format (missing =): {env_var}")

        result = client.exec(
            args.session_id,
            args.cmd,
            workdir=args.workdir,
            env=env,
            timeout_seconds=args.timeout_seconds,
        )

        # Print output
        if result.get("stdout"):
            print(result["stdout"], end="")
        if result.get("stderr"):
            print(result["stderr"], end="", file=sys.stderr)

        # Exit with command's exit code
        exit_code = result.get("exitCode", 0)
        if exit_code != 0 and not args.ignore_exit_code:
            return exit_code

        return 0
    except NoxRunnerError as e:
        error(f"Execution failed: {e}")
        return 1


def cmd_upload(args):
    """Upload files command."""
    client = create_client(args)
    try:
        files = {}

        if args.dir:
            # Upload entire directory
            dir_path = Path(args.dir)
            if not dir_path.is_dir():
                error(f"Not a directory: {args.dir}")
                return 1

            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(dir_path)
                    files[str(rel_path)] = file_path.read_bytes()
        else:
            # Upload specified files
            for file_path in args.files:
                path = Path(file_path)
                if not path.exists():
                    error(f"File not found: {file_path}")
                    return 1
                if path.is_dir():
                    error(f"Is a directory (use --dir): {file_path}")
                    return 1

                files[path.name] = path.read_bytes()

        if not files:
            error("No files to upload")
            return 1

        info(f"Uploading {len(files)} file(s)...")
        if client.upload_files(args.session_id, files, dest=args.dest):
            success(f"Uploaded {len(files)} file(s) to {args.dest}")
            return 0
        else:
            error("Upload failed")
            return 1
    except NoxRunnerError as e:
        error(f"Upload failed: {e}")
        return 1
    except Exception as e:
        error(f"Unexpected error: {e}")
        return 1


def cmd_download(args):
    """Download files command."""
    client = create_client(args)
    try:
        info("Downloading files...")
        tar_data = client.download_files(args.session_id, src=args.src)

        if args.output:
            output_path = Path(args.output)
            output_path.write_bytes(tar_data)
            success(f"Downloaded to {args.output}")
        else:
            # Extract to current directory
            extract_dir = Path(args.extract or ".")
            extract_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:gz") as tar:
                # Use 'data' filter for Python 3.12+ to avoid deprecation warning
                # and enhance security (restricts symlinks, devices, etc.)
                if sys.version_info >= (3, 12):
                    tar.extractall(extract_dir, filter="data")
                else:
                    tar.extractall(extract_dir)

            success(f"Extracted to {extract_dir}")

        return 0
    except NoxRunnerError as e:
        error(f"Download failed: {e}")
        return 1
    except Exception as e:
        error(f"Unexpected error: {e}")
        return 1


def cmd_touch(args):
    """Touch (extend TTL) command."""
    client = create_client(args)
    try:
        if client.touch(args.session_id):
            success("TTL extended")
            return 0
        else:
            error("Failed to extend TTL")
            return 1
    except NoxRunnerError as e:
        error(f"Touch failed: {e}")
        return 1


def cmd_delete(args):
    """Delete sandbox command."""
    client = create_client(args)
    try:
        if client.delete_sandbox(args.session_id):
            success("Sandbox deleted")
            return 0
        else:
            error("Failed to delete sandbox")
            return 1
    except NoxRunnerError as e:
        error(f"Delete failed: {e}")
        return 1


def cmd_shell(args):
    """Interactive shell command."""
    client = create_client(args)

    info(f"Interactive shell for session: {args.session_id}")
    info("Type 'exit' or 'quit' to exit, 'help' for help")
    print()

    while True:
        try:
            # Read command
            try:
                cmd_line = input(colorize(f"noxrunner:{args.session_id}$ ", Colors.CYAN))
            except (EOFError, KeyboardInterrupt):
                print()
                break

            cmd_line = cmd_line.strip()
            if not cmd_line:
                continue

            # Handle special commands
            if cmd_line in ("exit", "quit"):
                break
            if cmd_line == "help":
                print("Commands:")
                print("  exit, quit  - Exit shell")
                print("  help        - Show this help")
                print("  touch       - Extend TTL")
                print("  Any other command will be executed in the sandbox")
                continue
            if cmd_line == "touch":
                if client.touch(args.session_id):
                    success("TTL extended")
                else:
                    error("Failed to extend TTL")
                continue

            # Parse command
            try:
                cmd_parts = shlex.split(cmd_line)
            except ValueError as e:
                error(f"Invalid command: {e}")
                continue

            if not cmd_parts:
                continue

            # Execute command
            try:
                result = client.exec(
                    args.session_id,
                    cmd_parts,
                    workdir=args.workdir,
                    timeout_seconds=args.timeout_seconds,
                )

                # Print output
                if result.get("stdout"):
                    print(result["stdout"], end="")
                if result.get("stderr"):
                    print(result["stderr"], end="", file=sys.stderr)

                # Show exit code if non-zero
                exit_code = result.get("exitCode", 0)
                if exit_code != 0:
                    warning(f"Command exited with code {exit_code}")
            except NoxRunnerError as e:
                error(f"Execution failed: {e}")
        except KeyboardInterrupt:
            print()
            continue

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NoxRunner CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Health check
  %(prog)s health

  # Create sandbox
  %(prog)s create my-session

  # Execute command
  %(prog)s exec my-session python3 --version

  # Upload files
  %(prog)s upload my-session script.py data.txt

  # Download files
  %(prog)s download my-session --extract ./output

  # Interactive shell
  %(prog)s shell my-session

Environment Variables:
  NOXRUNNER_BASE_URL    Base URL of the NoxRunner (default: http://127.0.0.1:8080)

Local Testing Mode:
  Use --local-test flag to enable offline local testing mode.
  This mode executes commands in your local environment using /tmp directories.
  WARNING: This can cause data loss or security risks!

  Example:
    %(prog)s --local-test create test-session
    %(prog)s --local-test exec test-session echo hello
        """,
    )

    parser.add_argument(
        "--base-url",
        default=get_base_url(),
        help="Base URL of the NoxRunner (default: from NOXRUNNER_BASE_URL env or http://127.0.0.1:8080). Ignored if --local-test is set.",
    )
    parser.add_argument(
        "--local-test",
        action="store_true",
        help="Use local sandbox backend for offline testing. WARNING: Executes commands in your local environment!",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check if manager is healthy")
    health_parser.set_defaults(func=cmd_health)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create or ensure sandbox exists")
    create_parser.add_argument("session_id", help="Session identifier")
    create_parser.add_argument("--ttl", type=int, default=900, help="TTL in seconds (default: 900)")
    create_parser.add_argument("--image", help="Container image")
    create_parser.add_argument("--cpu", help="CPU limit")
    create_parser.add_argument("--mem", help="Memory limit")
    create_parser.add_argument("--storage", help="Ephemeral storage limit")
    create_parser.add_argument("--wait", action="store_true", help="Wait for pod to be ready")
    create_parser.add_argument(
        "--wait-timeout", type=int, default=30, help="Wait timeout in seconds (default: 30)"
    )
    create_parser.set_defaults(func=cmd_create)

    # Exec command
    exec_parser = subparsers.add_parser("exec", help="Execute command in sandbox")
    exec_parser.add_argument("session_id", help="Session identifier")
    exec_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute")
    exec_parser.add_argument(
        "--workdir", default="/workspace", help="Working directory (default: /workspace)"
    )
    exec_parser.add_argument("--env", action="append", help="Environment variable (KEY=VALUE)")
    exec_parser.add_argument(
        "--timeout-seconds", type=int, default=30, help="Command timeout (default: 30)"
    )
    exec_parser.add_argument(
        "--ignore-exit-code", action="store_true", help="Ignore non-zero exit codes"
    )
    exec_parser.set_defaults(func=cmd_exec)

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload files to sandbox")
    upload_parser.add_argument("session_id", help="Session identifier")
    upload_parser.add_argument("files", nargs="*", help="Files to upload")
    upload_parser.add_argument("--dir", help="Upload entire directory")
    upload_parser.add_argument(
        "--dest", default="/workspace", help="Destination directory (default: /workspace)"
    )
    upload_parser.set_defaults(func=cmd_upload)

    # Download command
    download_parser = subparsers.add_parser("download", help="Download files from sandbox")
    download_parser.add_argument("session_id", help="Session identifier")
    download_parser.add_argument(
        "--src", default="/workspace", help="Source directory (default: /workspace)"
    )
    download_parser.add_argument(
        "--output", help="Output tar file (if not specified, extracts to current directory)"
    )
    download_parser.add_argument("--extract", help="Extract directory (default: current directory)")
    download_parser.set_defaults(func=cmd_download)

    # Touch command
    touch_parser = subparsers.add_parser("touch", help="Extend sandbox TTL")
    touch_parser.add_argument("session_id", help="Session identifier")
    touch_parser.set_defaults(func=cmd_touch)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete sandbox")
    delete_parser.add_argument("session_id", help="Session identifier")
    delete_parser.set_defaults(func=cmd_delete)

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Interactive shell")
    shell_parser.add_argument("session_id", help="Session identifier")
    shell_parser.add_argument(
        "--workdir", default="/workspace", help="Working directory (default: /workspace)"
    )
    shell_parser.add_argument(
        "--timeout-seconds", type=int, default=30, help="Command timeout (default: 30)"
    )
    shell_parser.set_defaults(func=cmd_shell)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        error("Interrupted by user")
        return 130
    except Exception as e:
        if args.verbose:
            import traceback

            traceback.print_exc()
        error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

