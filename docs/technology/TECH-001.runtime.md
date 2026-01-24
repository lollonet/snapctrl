# TECH-001: Runtime Technology Stack

**ID:** TECH-001
**Status:** Draft
**Date:** 2025-01-24

## Runtime Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Language** | Python | 3.11+ | Rapid development, Qt bindings |
| **UI Framework** | PySide6 | 6.8+ | Official Qt6 bindings, LGPL |
| **Networking** | websockets | 14.0+ | Async WebSocket, JSON-RPC |
| **Threading** | QThread + asyncio | - | Non-blocking I/O in Qt |
| **Config** | QSettings | - | Native platform storage |

## Development Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Package Manager** | uv (or pip) | Dependency management |
| **Linter** | ruff | Fast Python linting |
| **Formatter** | ruff format | Black-compatible |
| **Type Checker** | basedpyright | Strict type checking |
| **Testing** | pytest + pytest-qt | Unit + UI tests |
| **CI/CD** | GitHub Actions | Automated quality gates |

## Dependency Graph

```
snapcast-mvp
├── PySide6 (Qt6 bindings)
│   ├── QtCore (signals, threads)
│   ├── QtGui (icons, styling)
│   └── QtWidgets (UI widgets)
├── websockets (async WebSocket client)
└── (dev dependencies)
    ├── pytest
    ├── pytest-qt
    ├── ruff
    └── basedpyright
```

## Runtime Requirements

| Platform | Min Version | Notes |
|----------|-------------|-------|
| Windows | 10 64-bit | MSVC redistributable |
| macOS | 12 Monterey | Universal binary possible |
| Linux | glibc 2.17+ | AppImage for distro-agnostic |

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Startup time | < 2s | `time snapcast-mvp` |
| Memory usage | < 200MB | Task Manager / htop |
| Volume latency | < 100ms | End-to-end timing |
| WebSocket msg | < 50ms | Round-trip time |
