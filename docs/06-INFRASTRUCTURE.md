# SnapCTRL - Infrastructure

## Development Environment

```yaml
Language: Python 3.11+
Package Manager: uv (or pip)
UI Framework: PySide6 6.8+
Networking: asyncio (TCP sockets)
Testing: pytest 9+, pytest-qt 4+, pytest-asyncio
Linting: ruff 0.9+
Type Checking: basedpyright 1.21+
```

## Project Structure

```
snapcast-mvp/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, format, test (unit only)
│       └── claude-review.yml      # Claude Code Review on PRs
├── src/snapcast_mvp/
│   ├── api/                       # TCP API client
│   ├── core/                      # Business logic
│   ├── models/                    # Frozen dataclasses
│   └── ui/                        # PySide6 UI
├── tests/
│   ├── test_*.py                  # Unit tests
│   └── conftest.py                # Test fixtures
├── docs/
│   ├── requirements/              # REQ-###.md
│   ├── architecture/              # ARC-###.md
│   └── ADR/                       # Decision records
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## CI/CD Pipeline (GitHub Actions)

### Main CI Workflow

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Install pytest and dev tools
        run: uv pip install pytest pytest-cov pytest-asyncio ruff

      - name: Run ruff
        run: uv run ruff check src tests

      - name: Run tests (skip UI/integration)
        run: uv run pytest tests/ -v --ignore=tests/test_ui*.py \
            --ignore=tests/test_integration*.py --cov=src --cov-report=term-missing
```

### Claude Review Workflow

```yaml
# .github/workflows/claude-review.yml
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  claude-review:
    uses: anthropic-actions/claude-review@v0.3.0
    with:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Notes:**
- UI tests skipped in CI (Qt GUI libraries unavailable in GitHub Actions)
- Integration tests skipped (require live Snapcast server)
- Run locally with `QT_QPA_PLATFORM=offscreen uv run pytest`

## Local Development

```bash
# Install dependencies
uv sync

# Run quality checks
uv run ruff check src tests
uv run ruff format src tests

# Run tests (all)
QT_QPA_PLATFORM=offscreen uv run pytest tests/ -v

# Run tests (unit only)
uv run pytest tests/ --ignore=tests/test_ui*.py --ignore=tests/test_integration*.py

# Type check (manual)
uv run basedpyright src/
```

## Packaging

| Platform | Tool | Output |
|----------|------|--------|
| Windows | PyInstaller | SnapCTRL.exe |
| macOS | briefcase | SnapCTRL.app |
| Linux | PyInstaller | SnapCTRL (AppImage) |

---

## Dependencies

### Runtime

```toml
[project]
dependencies = [
    "PySide6>=6.8.0",
]
```

### Development

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "pytest-qt>=4.5",
    "pytest-asyncio>=1.0",
    "ruff>=0.9.0",
    "basedpyright>=1.21.0",
]
```

**Note:** No websockets dependency - Snapcast uses raw TCP sockets.

---

## Pre-commit Hooks

```bash
# .git/hooks/pre-commit (installed by pre-commit package)
#!/bin/bash
uv run ruff check --fix src tests
uv run ruff format src tests
```

---

*Next: [Testing Strategy](07-TESTING.md) →*

*Last updated: 2025-01-26*
