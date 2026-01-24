# Snapcast MVP - Infrastructure

## Development Environment

```yaml
Language: Python 3.11+
Package Manager: uv (or pip)
UI Framework: PySide6 6.8+
WebSocket: websockets 14+
Testing: pytest 8+, pytest-qt 4+
Linting: ruff 0.7+
Type Checking: basedpyright 1.21+
```

## Project Structure

```
snapcast-mvp/
├── .github/
│   └── workflows/
│       ├── ci.yml          # Lint, typecheck, test
│       └── release.yml     # Build releases
├── src/snapcast_mvp/
│   ├── core/               # Business logic
│   ├── models/             # Data models
│   └── ui/                 # Qt UI
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/
│   ├── requirements/       # REQ-###.md
│   ├── architecture/       # ARC-###.md
│   └── ADR/                # Decision records
├── pyproject.toml
├── CONTROL.yaml            # BassCodeBase config
├── .bass-ready             # BassCodeBase marker
└── README.md
```

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install ruff basedpyright pytest pytest-qt
      - run: ruff check src tests
      - run: basedpyright src
      - run: pytest --cov

  test-ui:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e .
      - run: pytest tests/ui/  # UI tests (headless)
```

## Packaging

| Platform | Tool | Output |
|----------|------|--------|
| Windows | PyInstaller | snapcast-mvp.exe |
| macOS | briefcase | Snapcast MVP.app |
| Linux | PyInstaller | snapcast-mvp (AppImage) |

---

## Dependencies

```toml
[project]
dependencies = [
    "PySide6>=6.8.0",
    "websockets>=14.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-qt>=4.3",
    "ruff>=0.7.0",
    "basedpyright>=1.21.0",
]
```

---

*Next: [Testing Strategy](docs/07-TESTING.md) →*
