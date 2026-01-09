Introduction
============

What is NoxRunner?
------------------

**NoxRunner** is a Python client library for interacting with NoxRunner-compatible sandbox execution backends. 
It provides a simple, unified interface for managing isolated execution environments where you can safely run code.

Project Background
------------------

NoxRunner is the client library extracted from **Agentsmith**, a commercial distributed, high-concurrency secure sandbox system. 
In the commercial Agentsmith platform, sandboxes run on enterprise private cloud clusters with comprehensive enterprise features including:

- Advanced security policies and compliance frameworks
- Operational standards and monitoring
- Automated container lifecycle management
- Container image building and distribution
- Resource allocation and quota management
- Content auditing and logging

These enterprise features are proprietary and not part of this open-source release.

What's Open Source
------------------

This repository includes:

- **Client Library**: The complete Python client library for interacting with NoxRunner-compatible backends
- **Backend Specification**: The full API specification (see :doc:`user_guide/backend_specification`) that any compatible backend must implement
- **Local Sandbox Mode**: A local device simulation mode that mimics the backend behavior for development, testing, and POC demonstrations

Recommended Usage
-----------------

- **Development & Testing**: Use the local sandbox mode to develop and test AI agents or other applications without the operational overhead of managing a full cluster
- **Mock Backend**: Perfect for building simple AI agents that need a sandbox execution environment during development
- **Production Deployment**: When ready to deploy publicly, switch to a real NoxRunner backend cluster for production workloads

This approach significantly reduces operational and debugging burden during the development phase while maintaining full compatibility with production-grade sandbox infrastructure.

Key Features
------------

- **Zero Dependencies**: Uses only Python standard library - no external dependencies required
- **Complete API Coverage**: Supports all NoxRunner backend endpoints
- **Shell Command Interface**: Natural shell command execution with ``exec_shell()`` method - pass commands as strings just like in a terminal
- **Environment Variable Support**: Full support for environment variable expansion in shell commands (sh -c, bash -c, python -c, etc.)
- **Friendly CLI**: Command-line interface with colored output and interactive shell
- **Local Testing Mode**: Offline testing with local sandbox backend simulation
- **Type Hints**: Full type support for better IDE experience
- **Well Documented**: Comprehensive documentation and examples

Use Cases
---------

NoxRunner is ideal for:

- **Code Execution Services**: Run user-submitted code in isolated environments
- **CI/CD Pipelines**: Execute build scripts and tests in sandboxed containers
- **Educational Platforms**: Provide safe code execution for learning
- **Testing Frameworks**: Test code in isolated environments
- **Development Tools**: Local testing and development workflows

Architecture
------------

NoxRunner follows a modular client-server architecture::

    NoxRunnerClient (Public API)
         |
         | Delegates to
         v
    SandboxBackend (Abstract Interface)
         |
         +-- LocalBackend (Local filesystem)
         |
         +-- HTTPSandboxBackend (HTTP client)
                |
                | HTTP API
                v
           NoxRunner Backend Service
                |
                v
           Sandbox Environment (Container/Pod)

The architecture is organized into clear layers:

**Client Layer**
  - ``NoxRunnerClient``: Unified public API for users
  - Automatically selects appropriate backend (local or HTTP)
  - Provides high-level convenience methods

**Backend Layer**
  - ``SandboxBackend``: Abstract base class defining the interface
  - ``LocalBackend``: Local filesystem implementation for testing
  - ``HTTPSandboxBackend``: HTTP client for remote services

**Internal Modules**
  - ``security/``: Command validation and path sanitization
  - ``fileops/``: Tar archive handling utilities

The client communicates with a backend service that manages sandbox execution environments. 
The backend can be implemented using various technologies:

- Kubernetes-based sandbox managers
- Docker-based execution backends
- VM-based sandbox systems
- Custom implementations following the specification

Backend Compatibility
---------------------

NoxRunner is designed to work with any backend that implements the 
NoxRunner Backend Specification. This specification defines:

- RESTful HTTP API endpoints
- Request/response formats
- Error handling
- Session management
- File operations

See the :doc:`Backend Specification <user_guide/backend_specification>` for complete specification details.

Next Steps
----------

- Read the :doc:`quickstart` guide to get started
- Explore the :doc:`tutorial/index` for step-by-step examples
- Check out the :doc:`api_reference/index` for complete API documentation

