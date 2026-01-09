Basic Usage Tutorial
====================

This tutorial covers common usage patterns.

Working with Files
------------------

Upload Multiple Files
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   files = {
       "script.py": "print('Hello')",
       "data.json": '{"key": "value"}',
       "config.txt": "setting=value"
   }
   client.upload_files(session_id, files)

Upload Binary Files
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   files = {
       "image.png": b"\x89PNG\r\n\x1a\n..."  # Binary data
   }
   client.upload_files(session_id, files)

Download and Extract
~~~~~~~~~~~~~~~~~~~~

Recommended: Use ``download_workspace()`` for automatic extraction:

.. code-block:: python

   import tempfile
   from pathlib import Path

   with tempfile.TemporaryDirectory() as tmpdir:
       client.download_workspace(session_id, tmpdir)
       # Files are now extracted in tmpdir

Manual extraction (if needed):

.. code-block:: python

   import tarfile
   import io

   tar_data = client.download_files(session_id)
   tar_buffer = io.BytesIO(tar_data)
   
   with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
       tar.extractall("./output")

Environment Variables
---------------------

Set environment variables for commands:

.. code-block:: python

   result = client.exec(
       session_id,
       ["sh", "-c", "echo $MY_VAR"],
       env={"MY_VAR": "test_value"}
   )

Custom Working Directory
-------------------------

Execute commands in a specific directory:

.. code-block:: python

   # Create subdirectory
   client.exec(session_id, ["mkdir", "-p", "/workspace/subdir"])

   # Execute in subdirectory
   result = client.exec(
       session_id,
       ["pwd"],
       workdir="/workspace/subdir"
   )

Error Handling
--------------

Handle errors gracefully:

.. code-block:: python

   from noxrunner import NoxRunnerClient, NoxRunnerError, NoxRunnerHTTPError

   try:
       result = client.exec(session_id, ["nonexistent-command"])
       if result['exitCode'] != 0:
           print(f"Command failed: {result['stderr']}")
   except NoxRunnerHTTPError as e:
       print(f"HTTP error: {e.status_code} - {e.message}")
   except NoxRunnerError as e:
       print(f"Error: {e}")

TTL Management
--------------

Extend sandbox lifetime:

.. code-block:: python

   # Create with TTL
   client.create_sandbox(session_id, ttl_seconds=300)

   # Extend TTL
   client.touch(session_id)

