# Snapcast MVP

> Native desktop controller for Snapcast multi-room audio systems.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Qt](https://img.shields.io/badge/Qt-6.8+-green.svg)](https://www.qt.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

Snapcast MVP is a cross-platform desktop application that provides an intuitive GUI for controlling Snapcast servers. It allows you to:

- Connect to your Snapcast server (auto-discovery + manual)
- View groups, clients, and audio sources in real-time
- Control volume per group and per client
- Switch audio sources between rooms
- Mute/unmute any group or client

## Requirements

- Python 3.11+
- PySide6 (Qt6)
- A running Snapcast server

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/snapcast-mvp.git
cd snapcast-mvp

# Install dependencies
pip install -e .
```

## Usage

```bash
# Run the application
snapcast-mvp
```

Or with make:

```bash
make run
```

## Development

```bash
# Install development dependencies
make install

# Run quality checks
make check

# Run tests
make test
```

## Quality Gates

This project is configured for BassCodeBase quality standards.

To adopt the full standards:
```bash
uv tool install basscodebase
bass adopt  # Quick wizard, detects .bass-ready
bass check  # Run quality gates
```

## Roadmap

See [Work Breakdown Structure](docs/08-WBS.md) for the 3-month development plan.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Snapcast](https://github.com/badaix/snapcast) - Multi-room audio system
- [PySide6](https://pypi.org/project/PySide6/) - Qt6 Python bindings
