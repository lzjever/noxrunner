Quick Start
===========

Installation
------------

Install NoxRunner from PyPI:

.. code-block:: bash

   pip install noxrunner

Or install from source:

.. code-block:: bash

   git clone https://github.com/noxrunner/noxrunner.git
   cd noxrunner
   pip install -e .

Basic Usage
-----------

As a Library
~~~~~~~~~~~~

.. code-block:: python

   from noxrunner import NoxRunnerClient

   # Create client
   client = NoxRunnerClient("http://127.0.0.1:8080")

   # Create sandbox
   session_id = "my-session"
   result = client.create_sandbox(session_id)
   print(f"Sandbox: {result['podName']}")

   # Wait for sandbox ready
   client.wait_for_pod_ready(session_id)

   # Execute command (array format)
   result = client.exec(session_id, ["python3", "--version"])
   print(result["stdout"])

   # Execute shell command (string format - more natural!)
   result = client.exec_shell(session_id, "python3 --version")
   print(result["stdout"])

   # Shell commands with environment variables
   result = client.exec_shell(
       session_id,
       "echo $MY_VAR && ls -la",
       env={"MY_VAR": "test_value"}
   )
   print(result["stdout"])

   # Upload files
   client.upload_files(session_id, {
       "script.py": "print('Hello from NoxRunner!')"
   })

   # Download files
   tar_data = client.download_files(session_id)

   # Delete sandbox
   client.delete_sandbox(session_id)

As a CLI Tool
~~~~~~~~~~~~~

Remote Mode (Default):

.. code-block:: bash

   # Health check
   noxrc health

   # Create sandbox
   noxrc create my-session --wait

   # Execute command
   noxrc exec my-session python3 --version

   # Upload files
   noxrc upload my-session script.py data.txt

   # Download files
   noxrc download my-session --extract ./output

   # Interactive shell
   noxrc shell my-session

   # Delete sandbox
   noxrc delete my-session

Local Testing Mode
~~~~~~~~~~~~~~~~~~

For offline testing without a backend service:

.. code-block:: bash

   # Use --local-test flag
   noxrc --local-test create my-session
   noxrc --local-test exec my-session echo "Hello"
   noxrc --local-test upload my-session script.py
   noxrc --local-test delete my-session

.. warning::

   Local testing mode executes commands in your local environment using ``/tmp`` directories. 
   This can cause data loss or security risks! Use only for testing purposes.

Environment Variables
---------------------

- ``NOXRUNNER_BASE_URL``: Base URL of the NoxRunner backend (default: ``http://127.0.0.1:8080``)

Next Steps
----------

- Read the :doc:`tutorial/index` for detailed examples
- Check the :doc:`user_guide/index` for comprehensive usage guide
- Explore the :doc:`api_reference/index` for complete API documentation

