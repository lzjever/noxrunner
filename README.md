# 🚀 NoxRunner - Python Client for Sandbox Execution Backends

[![PyPI version](https://img.shields.io/pypi/v/noxrunner.svg)](https://pypi.org/project/noxrunner/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Documentation](https://readthedocs.org/projects/noxrunner/badge/?version=latest)](https://noxrunner.readthedocs.io)
[![CI](https://github.com/lzjever/noxrunner/workflows/CI/badge.svg)](https://github.com/lzjever/noxrunner/actions)

**NoxRunner** is a Python client library for interacting with NoxRunner-compatible sandbox execution backends. It uses **only Python standard library** - **zero external dependencies**.

## 📖 About This Project

NoxRunner is the client library extracted from **Agentsmith**, a commercial distributed, high-concurrency AI-Agent development and operating platform. In the commercial Agentsmith platform, sandboxes run on enterprise private cloud clusters with comprehensive security policies, operational standards, automated container management, image building, resource allocation, and content auditing capabilities. These enterprise features are not part of this open-source release.

**What's Open Source:**
- ✅ **Client Library**: This Python client library for interacting with NoxRunner backends
- ✅ **Backend Specification**: The complete API specification (see [SPECS.md](SPECS.md))
- ✅ **Local Sandbox Mode**: A local device simulation mode for development, testing, and POC demos

**Use Cases:**
- 🧪 **Development & Testing**: Use the local sandbox mode to develop and test AI agents without the overhead of managing a full cluster
- 🚀 **Production Deployment**: When ready to deploy publicly, switch to a real NoxRunner backend cluster for production workloads
- 🔧 **Mock Backend**: Perfect for building simple AI agents that need a sandbox execution environment during development

This approach significantly reduces operational and debugging burden during the development phase while maintaining compatibility with production-grade sandbox infrastructure.

## ✨ Features

- ✅ **Zero Dependencies**: Only uses Python standard library
- ✅ **Complete API Coverage**: All NoxRunner backend endpoints
- ✅ **Shell Command Interface**: Natural shell command execution with `exec_shell()` method
- ✅ **Environment Variable Support**: Full support for environment variable expansion in shell commands
- ✅ **Friendly CLI**: Colored output, interactive shell
- ✅ **Local Testing Mode**: Offline testing with local sandbox backend
- ✅ **Easy to Use**: Simple API with clear error messages
- ✅ **Well Documented**: Comprehensive documentation and examples
- ✅ **Type Hints**: Full type support for better IDE experience

## 📦 Installation

### Install from Source

```bash
# Clone the repository
git clone https://github.com/noxrunner/noxrunner.git
cd noxrunner

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Install from PyPI (when published)

```bash
pip install noxrunner
```

## 🚀 Quick Start

### As a Library

```python
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
```

### As a CLI Tool

**Remote Mode (Default)**:

```bash
# Health check
noxrunner health

# Create sandbox
noxrunner create my-session --wait

# Execute command
noxrunner exec my-session python3 --version

# Upload files
noxrunner upload my-session script.py data.txt

# Download files
noxrunner download my-session --extract ./output

# Interactive shell
noxrunner shell my-session

# Delete sandbox
noxrunner delete my-session
```

**Local Testing Mode** (for offline testing):

```bash
# Use --local-test flag for offline testing
noxrunner --local-test create my-session
noxrunner --local-test exec my-session echo "Hello"
noxrunner --local-test upload my-session script.py
noxrunner --local-test delete my-session
```

⚠️ **Warning**: Local testing mode executes commands in your local environment using `/tmp` directories. This can cause data loss or security risks!

## 📚 Documentation

- **[API Reference](docs/)** - Complete API documentation
- **[Backend Specification](SPECS.md)** - Implement your own NoxRunner-compatible backend
- **[Examples](examples/)** - Usage examples
- **[Contributing](CONTRIBUTING.md)** - How to contribute

## 🏗️ Project Structure

```
noxrunner/
├── noxrunner/          # Python package
│   ├── __init__.py    # Package initialization
│   ├── client.py      # NoxRunnerClient class
│   ├── exceptions.py  # Exception classes
│   └── cli.py         # CLI tool
├── tests/             # Test suite
├── examples/          # Example scripts
├── docs/              # Sphinx documentation
└── README.md          # This file
```

## 🔌 Backend Compatibility

NoxRunner is designed to work with any backend that implements the [NoxRunner Backend Specification](SPECS.md). This includes:

- Kubernetes-based sandbox managers
- Docker-based execution backends
- VM-based sandbox systems
- Any custom implementation following the spec

## 🧪 Testing

```bash
# Run unit tests (excludes integration tests)
make test

# Run integration tests (requires running NoxRunner backend)
make test-integration

# Run with coverage
make test-cov

# Run linting
make lint

# Format code
make format

# Run all checks
make check
```

### Testing Modes

- **Unit Tests**: Test local functionality using the local sandbox backend (no external dependencies)
- **Integration Tests**: Test against a real remote NoxRunner backend (requires backend service)

See the [documentation](https://noxrunner.readthedocs.io) for more details on testing.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔗 Links

- **Repository**: https://github.com/noxrunner/noxrunner
- **Documentation**: https://noxrunner.readthedocs.io
- **Issues**: https://github.com/noxrunner/noxrunner/issues

## 🙏 Acknowledgments

NoxRunner was originally developed as part of **Agentsmith**, a commercial distributed AI-Agent development and operating platform. The client library and backend specification have been extracted and open-sourced to enable broader adoption and community contribution. The local sandbox simulation mode was added to facilitate development, testing, and POC demonstrations without requiring access to production infrastructure.

