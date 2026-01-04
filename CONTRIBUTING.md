# Contributing to NoxRunner

Thank you for your interest in contributing to NoxRunner!

## Development Setup

### Quick Start

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Set up development environment**:
   ```bash
   make dev-install
   ```

3. **Run tests**:
   ```bash
   make test
   ```

That's it! You're ready to contribute.

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Development Workflow

### Standard Development

For active development where you need to import and use noxrunner:

```bash
make dev-install  # Installs package + all dependencies
make test         # Run tests
make lint         # Check code quality
make format       # Format code
```

### CI/CD or Code Review

If you only need development tools (linting, formatting) without installing the package:

```bash
make setup-venv   # Only installs dependencies, not the package
make lint         # Can still run linting
make format-check # Can still check formatting
```

## Code Style

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

- Write tests for all new features
- Ensure tests pass: `make test`
- Aim for high test coverage

## Documentation

- Update README.md for user-facing changes
- Update SPECS.md for API changes
- Add docstrings to all new functions and classes
- Update CHANGELOG.md for all changes

## Submitting Changes

1. Create a feature branch
2. Make your changes
3. Run tests and linting: `make check`
4. Commit with clear messages
5. Submit a pull request

## Questions?

Open an issue or contact the maintainers.

