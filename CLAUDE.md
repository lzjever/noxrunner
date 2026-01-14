# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NoxRunner is a zero-dependency Python client library for NoxRunner-compatible sandbox execution backends. It uses **only Python standard library** - no external dependencies. The project supports two modes:
- **HTTP backend mode**: Connects to remote NoxRunner backends for production use
- **Local backend mode**: Offline testing using `/tmp` directories (development only, has security implications)

## Architecture

### Backend Pattern
The codebase uses a strategy pattern with interchangeable backends:
- `noxrunner/backend/base.py`: Abstract `SandboxBackend` class defining the interface
- `noxrunner/backend/http.py`: `HTTPSandboxBackend` for remote HTTP communication
- `noxrunner/backend/local.py`: `LocalBackend` for local testing (executes in `/tmp/noxrunner-{sessionId}`)

The `NoxRunnerClient` (in `client.py`) automatically selects the appropriate backend based on initialization parameters.

### Key Modules
- `noxrunner/client.py`: Main `NoxRunnerClient` class - the primary API
- `noxrunner/exceptions.py`: Custom exception hierarchy (`NoxRunnerError`, `NoxRunnerHTTPError`)
- `noxrunner/security/`: Command validation and path sanitization
- `noxrunner/fileops/`: Tar archive handling for file uploads/downloads
- `bin/noxrc.py`: CLI tool entry point

### Zero Dependency Constraint
**Critical**: This project intentionally uses NO external dependencies. Only Python standard library is allowed. This is enforced via `dependencies = []` in `pyproject.toml`.

## Common Commands

### Development Setup
```bash
# Install with dev dependencies (recommended for active development)
make dev-install

# Alternative: setup venv without installing package (CI/tools only)
make setup-venv
make install
```

The project prefers `uv` over `pip` for faster dependency management, but falls back to `pip` automatically if `uv` is not available.

### Testing
```bash
# Run unit tests only (fast, no backend required)
make test

# Run with coverage
make test-cov

# Run integration tests (requires running NoxRunner backend)
NOXRUNNER_ENABLE_INTEGRATION=1 NOXRUNNER_BASE_URL=http://127.0.0.1:8080 make test-integration

# Run specific test file
pytest tests/test_security.py -v

# Run specific test
pytest tests/test_security.py::TestCommandValidator::test_validate_command -v
```

Tests are marked with pytest markers: `unit` (default) and `integration` (requires backend).

### Code Quality
```bash
# Format code with ruff
make format

# Check formatting
make format-check

# Lint code
make lint

# Run all checks (lint + format check + tests)
make check
```

The project uses **ruff** as both linter and formatter (replaces black + flake8). Configuration is in `pyproject.toml`.

### Building
```bash
# Build source and wheel distributions
make build

# Clean build artifacts
make clean
```

## Local Testing Mode

The local backend (`LocalBackend`) executes commands directly on the host machine using `/tmp` directories. This is intended for development and testing only.

**Security Warning**: Local mode can execute arbitrary commands and modify files. The workspace is at `/tmp/noxrunner-{sessionId}`.

When testing with local mode:
```python
from noxrunner import NoxRunnerClient
client = NoxRunnerClient(local_test=True)
```

Or via CLI:
```bash
noxrc --local-test create my-session
noxrc --local-test exec my-session echo "Hello"
```

## API Specification

The backend API is fully specified in `SPECS.md`. Key endpoints:
- `GET /healthz` - Health check
- `PUT /v1/sandboxes/{sessionId}` - Create/ensure sandbox
- `POST /v1/sandboxes/{sessionId}/exec` - Execute command
- `POST /v1/sandboxes/{sessionId}/files/upload` - Upload files (tar.gz)
- `GET /v1/sandboxes/{sessionId}/files/download` - Download files (tar.gz)
- `DELETE /v1/sandboxes/{sessionId}` - Delete sandbox
- `POST /v1/sandboxes/{sessionId}/touch` - Extend TTL

## File Operations

File uploads/downloads use tar archives (tar.gz format). The `TarHandler` class in `noxrunner/fileops/tar_handler.py` handles:
- `upload_files()`: Creates tar archive from file dictionary
- `download_workspace()`: Extracts tar archive to local directory

The `download_files()` method returns raw tar bytes, while `download_workspace()` extracts to a directory (more convenient).

## Shell Command Support

The client provides `exec_shell()` for natural shell command execution with environment variable expansion:
```python
result = client.exec_shell(session_id, "echo $MY_VAR && ls -la", env={"MY_VAR": "test"})
```

This internally converts shell strings to command arrays (for security) and handles environment variables.

## Python Version Support

The project supports Python 3.8 through 3.14. Type hints use compatibility patterns like `Optional[X]` and `Union[X, Y]` instead of the newer `X | None` syntax to maintain Python 3.8 compatibility.

## CLI Tool

The `noxrc` CLI is installed as a console entry point. Key commands:
- `noxrc health` - Health check
- `noxrc create <session> [--wait]` - Create sandbox
- `noxrc exec <session> <command>` - Execute command
- `noxrc shell <session>` - Interactive shell
- `noxrc upload <session> <files...>` - Upload files
- `noxrc download <session> [--extract <path>]` - Download files
- `noxrc delete <session>` - Delete sandbox

Add `--local-test` flag to any command for offline testing.
