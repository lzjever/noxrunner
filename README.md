# 🚀 NoxRunner - Python Client for Sandbox Execution Backends

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**NoxRunner** is a Python client library for interacting with NoxRunner-compatible sandbox execution backends. It uses **only Python standard library** - **zero external dependencies**.

## ✨ Features

- ✅ **Zero Dependencies**: Only uses Python standard library
- ✅ **Complete API Coverage**: All NoxRunner backend endpoints
- ✅ **Friendly CLI**: Colored output, interactive shell
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

# Execute command
result = client.exec(session_id, ["python3", "--version"])
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

```bash
# Health check
noxrunner health

# Create sandbox
noxrunner create my-session --wait

# Execute command
noxrunner exec my-session python3 --version

# Upload files
noxrunner upload my-session script.py data.txt

# Interactive shell
noxrunner shell my-session
```

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
# Run all tests
make test

# Run with coverage
make test-cov

# Run linting
make lint

# Format code
make format

# Run all checks
make check
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔗 Links

- **Repository**: https://github.com/noxrunner/noxrunner
- **Documentation**: https://noxrunner.readthedocs.io
- **Issues**: https://github.com/noxrunner/noxrunner/issues

## 🙏 Acknowledgments

NoxRunner was originally developed as part of the sandbox project and has been extracted as a standalone library for broader use.

