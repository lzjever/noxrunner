Advanced Usage Tutorial
=======================

This tutorial covers advanced features and patterns.

Local Testing Mode
------------------

Use local testing for development:

.. code-block:: python

   from noxrunner import NoxRunnerClient

   # Enable local testing
   client = NoxRunnerClient(local_test=True)

   # Use normally - no backend required
   client.create_sandbox("local-session")
   result = client.exec("local-session", ["echo", "test"])
   client.delete_sandbox("local-session")

Concurrent Sessions
-------------------

Manage multiple sessions:

.. code-block:: python

   sessions = ["session-1", "session-2", "session-3"]

   # Create all sessions
   for sid in sessions:
       client.create_sandbox(sid)

   # Execute in parallel (example with threading)
   import threading

   def run_command(sid):
       result = client.exec(sid, ["echo", f"Session {sid}"])
       print(result["stdout"])

   threads = [threading.Thread(target=run_command, args=(sid,)) for sid in sessions]
   for t in threads:
       t.start()
   for t in threads:
       t.join()

   # Clean up
   for sid in sessions:
       client.delete_sandbox(sid)

Custom Backend Implementation
-----------------------------

Implement a custom backend by extending the abstract base class:

.. code-block:: python

   from noxrunner.backend.base import SandboxBackend

   class MyBackend(SandboxBackend):
       def health_check(self):
           return True

       def create_sandbox(self, session_id, **kwargs):
           # Your implementation
           return {"podName": f"my-{session_id}", "expiresAt": "..."}

       # Implement other required methods from SandboxBackend...

   # Use custom backend
   backend = MyBackend()
   client = NoxRunnerClient()
   client._backend = backend

Error Recovery
--------------

Implement retry logic:

.. code-block:: python

   import time

   def create_sandbox_with_retry(client, session_id, max_retries=3):
       for attempt in range(max_retries):
           try:
               return client.create_sandbox(session_id)
           except NoxRunnerHTTPError as e:
               if e.status_code == 503 and attempt < max_retries - 1:
                   time.sleep(2 ** attempt)  # Exponential backoff
                   continue
               raise

