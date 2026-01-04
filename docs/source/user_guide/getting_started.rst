Getting Started
===============

This guide will help you get started with NoxRunner.

Installation
------------

See :doc:`../quickstart` for installation instructions.

Basic Concepts
--------------

Session ID
~~~~~~~~~~

A **session ID** is a unique identifier for a sandbox execution environment. 
You provide this identifier when creating a sandbox, and use it for all subsequent operations.

Sandbox Lifecycle
~~~~~~~~~~~~~~~~~

1. **Create**: Create a new sandbox with a session ID
2. **Wait**: Wait for the sandbox to be ready (optional)
3. **Use**: Execute commands, upload/download files
4. **Touch**: Extend the TTL (time to live) if needed
5. **Delete**: Clean up the sandbox when done

Working Directory
~~~~~~~~~~~~~~~~~

By default, operations use ``/workspace`` as the working directory. 
You can specify a different directory using the ``workdir`` parameter.

Example
-------

.. code-block:: python

   from noxrunner import NoxRunnerClient

   # Create client
   client = NoxRunnerClient("http://127.0.0.1:8080")

   # Create sandbox
   session_id = "my-session"
   client.create_sandbox(session_id, ttl_seconds=900)

   # Wait for ready
   if client.wait_for_pod_ready(session_id, timeout=60):
       # Execute command (array format)
       result = client.exec(session_id, ["python3", "--version"])
       print(result["stdout"])

       # Or use exec_shell for natural shell commands
       result = client.exec_shell(session_id, "python3 --version")
       print(result["stdout"])

       # Shell commands with environment variables
       result = client.exec_shell(
           session_id,
           "echo $MY_VAR",
           env={"MY_VAR": "test_value"}
       )
       print(result["stdout"])

       # Clean up
       client.delete_sandbox(session_id)

Next Steps
----------

- Learn about :doc:`cli_usage` for command-line usage
- Read about :doc:`local_testing` for offline testing
- Check :doc:`testing` for testing strategies

