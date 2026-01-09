# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-09

### Added
- **Modular Architecture**: Complete refactoring with clear separation of concerns
  - `backend/` module: Abstract base class and concrete implementations
  - `security/` module: Command validation and path sanitization utilities
  - `fileops/` module: Tar archive handling utilities
- **Unified Client Interface**: `NoxRunnerClient.download_workspace()` method for seamless file synchronization
- **Enhanced Security**: Centralized security utilities (`CommandValidator`, `PathSanitizer`)
- **Improved File Operations**: Unified tar handling with security checks
- **Comprehensive Test Coverage**: 98+ unit tests and 30+ integration tests
- **Ruff Integration**: Migrated from flake8/black to ruff for code quality

### Changed
- **BREAKING**: Removed backward compatibility aliases (`RemoteSandboxBackend`, `LocalSandboxBackend`)
- **BREAKING**: Renamed `RemoteSandboxBackend` → `HTTPSandboxBackend`
- **BREAKING**: Renamed `LocalSandboxBackend` → `LocalBackend`
- **BREAKING**: Removed `WorkspaceSync` class (functionality integrated into `TarHandler` and `NoxRunnerClient`)
- **Architecture**: Client now directly uses `TarHandler` instead of `WorkspaceSync` wrapper
- **File Upload**: Enhanced `upload_files` to properly handle subdirectory paths
- **Code Quality**: Migrated from flake8/black to ruff for linting and formatting

### Fixed
- Fixed file synchronization in local sandbox mode
- Fixed subdirectory handling in `upload_files` method
- Fixed path traversal security issues in tar extraction
- Fixed test failures in integration tests

### Removed
- `noxrunner/backend.py` (replaced by `backend/base.py`)
- `noxrunner/local_sandbox.py` (replaced by `backend/local.py`)
- `noxrunner/remote_backend.py` (replaced by `backend/http.py`)
- `noxrunner/fileops/workspace_sync.py` (functionality integrated into client)
- All backward compatibility aliases

### Internal
- Refactored code structure for better maintainability
- Extracted common utilities into dedicated modules
- Improved code organization and separation of concerns
- Enhanced test coverage and documentation

## [1.0.0] - 2024-01-04

### Added
- Initial release of NoxRunner
- Python client library with zero dependencies (standard library only)
- Complete API coverage for NoxRunner-compatible backends
- **Shell command interface** (`exec_shell()` method) for natural command execution
- **Environment variable expansion** support in shell commands (sh -c, bash -c, python -c, etc.)
- Command-line interface (CLI) tool
- Interactive shell mode
- Local sandbox mode for development and testing
- File upload/download support
- Comprehensive documentation
- Backend specification (SPECS.md)

### Project Background
- Extracted from Agentsmith commercial platform
- Client library and backend specification open-sourced
- Local sandbox simulation mode added for development and POC purposes

