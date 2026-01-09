Backend API
===========

SandboxBackend (Abstract Base Class)
------------------------------------

.. autoclass:: noxrunner.backend.base.SandboxBackend
   :members:
   :undoc-members:
   :show-inheritance:

HTTPSandboxBackend
------------------

HTTP client backend for remote NoxRunner services.

.. autoclass:: noxrunner.backend.http.HTTPSandboxBackend
   :members:
   :undoc-members:
   :show-inheritance:

LocalBackend
------------

Local filesystem backend for development and testing.

.. autoclass:: noxrunner.backend.local.LocalBackend
   :members:
   :undoc-members:
   :show-inheritance:

Internal Modules
----------------

Security Module
~~~~~~~~~~~~~~~

.. automodule:: noxrunner.security.command_validator
   :members:
   :undoc-members:

.. automodule:: noxrunner.security.path_sanitizer
   :members:
   :undoc-members:

File Operations Module
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: noxrunner.fileops.tar_handler
   :members:
   :undoc-members:

