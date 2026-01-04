# Tests

This directory contains the test suite for NoxRunner.

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_client.py
```

## Test Structure

- `test_client.py` - Tests for NoxRunnerClient
- `test_exceptions.py` - Tests for exception classes
- `test_cli.py` - Tests for CLI tool

