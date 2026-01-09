#!/usr/bin/env python3
"""
Quick Start Example for Sandbox Manager Python API

This example demonstrates the basic usage of the Sandbox Manager API.
"""

import time

from noxrunner import NoxRunnerClient, NoxRunnerError


def main():
    # Initialize client
    base_url = "http://127.0.0.1:8080"
    print(f"Connecting to Sandbox Manager at {base_url}")

    client = NoxRunnerClient(base_url)

    # 1. Health check
    print("\n1. Health Check")
    if client.health_check():
        print("   ✓ Manager is healthy")
    else:
        print("   ✗ Manager is not healthy")
        return 1

    # 2. Create sandbox
    session_id = f"quickstart-{int(time.time())}"
    print(f"\n2. Creating Sandbox: {session_id}")
    try:
        result = client.create_sandbox(session_id, ttl_seconds=900)
        print(f"   ✓ Created: {result.get('podName')}")
        print(f"   Expires at: {result.get('expiresAt')}")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 3. Wait for pod ready
    print("\n3. Waiting for Pod to be Ready")
    if client.wait_for_pod_ready(session_id, timeout=30):
        print("   ✓ Pod is ready")
    else:
        print("   ✗ Pod did not become ready")
        return 1

    # 4. Execute a simple command
    print("\n4. Executing Command: python3 --version")
    try:
        result = client.exec(session_id, ["python3", "--version"])
        print(f"   Exit code: {result.get('exitCode')}")
        print(f"   Output: {result.get('stdout', '').strip()}")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 5. Upload a Python script
    print("\n5. Uploading Python Script")
    script = """#!/usr/bin/env python3
import sys
import os

print("Hello from sandbox!")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Files in workspace:")
for item in os.listdir('.'):
    print(f"  - {item}")
"""
    try:
        client.upload_files(session_id, {"hello.py": script})
        print("   ✓ Script uploaded")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 6. Execute the uploaded script
    print("\n6. Executing Uploaded Script")
    try:
        result = client.exec(session_id, ["python3", "hello.py"])
        print("   Output:")
        print(result.get("stdout", ""))
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 7. Upload multiple files
    print("\n7. Uploading Multiple Files")
    files = {
        "data.txt": "Line 1\nLine 2\nLine 3\n",
        "config.json": '{"name": "test", "value": 42}\n',
        "README.md": "# Test Project\n\nThis is a test.\n",
    }
    try:
        client.upload_files(session_id, files)
        print(f"   ✓ Uploaded {len(files)} files")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 8. List files
    print("\n8. Listing Files")
    try:
        result = client.exec(session_id, ["ls", "-la"])
        print("   Files:")
        print(result.get("stdout", ""))
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 9. Read a file
    print("\n9. Reading File Content")
    try:
        result = client.exec(session_id, ["cat", "data.txt"])
        print("   Content:")
        print(result.get("stdout", ""))
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 10. Extend TTL
    print("\n10. Extending TTL")
    try:
        if client.touch(session_id):
            print("   ✓ TTL extended")
        else:
            print("   ✗ Failed to extend TTL")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")

    # 11. Download files
    print("\n11. Downloading Files")
    try:
        tar_data = client.download_files(session_id)
        print(f"   ✓ Downloaded {len(tar_data)} bytes")

        # Download and extract to local directory (recommended)
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            client.download_workspace(session_id, tmpdir)
            files = list(Path(tmpdir).glob("*"))
            print(f"   ✓ Extracted {len(files)} files to temporary directory")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    # 12. Cleanup
    print("\n12. Cleaning Up")
    try:
        if client.delete_sandbox(session_id):
            print("   ✓ Sandbox deleted")
        else:
            print("   ✗ Failed to delete sandbox")
    except NoxRunnerError as e:
        print(f"   ✗ Failed: {e}")
        return 1

    print("\n" + "=" * 50)
    print("Quick Start Example Completed Successfully!")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
