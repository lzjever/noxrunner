CLI Usage
=========

NoxRunner provides a command-line interface for interacting with sandbox backends.

Basic Commands
--------------

Health Check
~~~~~~~~~~~~

Check if the backend is healthy:

.. code-block:: bash

   noxrc health

Create Sandbox
~~~~~~~~~~~~~~

Create a new sandbox:

.. code-block:: bash

   noxrc create my-session --wait

Options:

- ``--ttl SECONDS``: Time to live in seconds (default: 900)
- ``--wait``: Wait for pod to be ready
- ``--wait-timeout SECONDS``: Wait timeout (default: 30)

Execute Command
~~~~~~~~~~~~~~~

Execute a command in the sandbox:

.. code-block:: bash

   noxrc exec my-session python3 --version

Options:

- ``--workdir DIR``: Working directory (default: /workspace)
- ``--env KEY=VALUE``: Environment variable (can be used multiple times)
- ``--timeout-seconds SECONDS``: Command timeout (default: 30)
- ``--ignore-exit-code``: Don't fail on non-zero exit codes

Upload Files
~~~~~~~~~~~~

Upload files to the sandbox:

.. code-block:: bash

   noxrc upload my-session script.py data.txt

Options:

- ``--dir DIR``: Upload entire directory
- ``--dest DIR``: Destination directory (default: /workspace)

Download Files
~~~~~~~~~~~~~~

Download files from the sandbox:

.. code-block:: bash

   noxrc download my-session --extract ./output

Options:

- ``--src DIR``: Source directory (default: /workspace)
- ``--output FILE``: Output tar file (if not specified, extracts to current directory)
- ``--extract DIR``: Extract directory (default: current directory)

Interactive Shell
~~~~~~~~~~~~~~~~~

Start an interactive shell:

.. code-block:: bash

   noxrc shell my-session

Special commands:

- ``exit`` or ``quit``: Exit shell
- ``help``: Show help
- ``touch``: Extend TTL

Delete Sandbox
~~~~~~~~~~~~~~

Delete a sandbox:

.. code-block:: bash

   noxrc delete my-session

Local Testing Mode
------------------

Use ``--local-test`` flag for offline testing:

.. code-block:: bash

   noxrc --local-test create my-session
   noxrc --local-test exec my-session echo "Hello"

.. warning::

   Local testing mode executes commands in your local environment. 
   Use only for testing purposes!

Environment Variables
---------------------

- ``NOXRUNNER_BASE_URL``: Base URL of the backend (default: ``http://127.0.0.1:8080``)

Global Options
--------------

- ``--base-url URL``: Backend URL
- ``--local-test``: Use local sandbox backend
- ``--timeout SECONDS``: Request timeout (default: 30)
- ``--verbose``: Verbose output

