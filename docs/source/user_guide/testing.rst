Testing
=======

NoxRunner provides comprehensive testing support for both unit and integration tests.

Test Types
----------

Unit Tests
~~~~~~~~~~

Unit tests use the local sandbox backend and don't require external services:

.. code-block:: bash

   make test

These tests:

- Use the local sandbox backend
- Don't require a running backend service
- Run quickly
- Cover all core functionality

Integration Tests
~~~~~~~~~~~~~~~~~

Integration tests require a running NoxRunner backend:

.. code-block:: bash

   make test-integration

These tests:

- Connect to a real backend service
- Test end-to-end workflows
- Verify API compatibility
- Automatically set ``NOXRUNNER_ENABLE_INTEGRATION=1``
- Optionally use ``NOXRUNNER_BASE_URL`` environment variable (defaults to http://127.0.0.1:8080)

Running Tests
-------------

Unit Tests
~~~~~~~~~~

.. code-block:: bash

   # Run all unit tests
   make test

   # Run with coverage
   make test-cov

   # Run specific test file
   pytest tests/test_local_sandbox.py -v

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Set backend URL (optional, defaults to http://127.0.0.1:8080)
   export NOXRUNNER_BASE_URL=http://your-backend:8080

   # Run integration tests (automatically enables integration tests)
   make test-integration

   # Or directly with pytest (requires NOXRUNNER_ENABLE_INTEGRATION=1)
   NOXRUNNER_ENABLE_INTEGRATION=1 pytest tests/ -v -m integration

Test Markers
------------

Tests are marked with pytest markers:

- ``@pytest.mark.integration``: Integration tests (require backend)
- Unit tests: No marker (run by default)

Running Specific Tests
----------------------

.. code-block:: bash

   # Run only unit tests
   pytest tests/ -m "not integration"

   # Run only integration tests
   pytest tests/ -m integration

   # Run specific test class
   pytest tests/test_local_sandbox.py::TestLocalSandboxBackend

   # Run specific test
   pytest tests/test_local_sandbox.py::TestLocalSandboxBackend::test_health_check

Coverage
--------

Generate coverage reports:

.. code-block:: bash

   make test-cov

This generates:

- Terminal output with coverage summary
- HTML report in ``htmlcov/`` directory

Best Practices
--------------

1. **Write Unit Tests**: Test core functionality with unit tests
2. **Use Integration Tests**: Test API compatibility with integration tests
3. **Unique Session IDs**: Use unique IDs in tests to avoid conflicts
4. **Clean Up**: Always clean up sandboxes in test teardown
5. **Mock When Possible**: Use mocks for external dependencies in unit tests

