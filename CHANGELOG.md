# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Week 1: Data Models** - Jan 24
  - Immutable frozen dataclasses for Client, Group, Server, Source
  - ServerState aggregate with lookup methods (get_client, get_group, get_source)
  - Full type hints with basedpyright strict mode compliance
  - 100% test coverage on all models

- **Week 2: TCP API Client** - Jan 24
  - SnapcastClient using asyncio TCP sockets (Snapcast uses raw TCP, not WebSocket)
  - JSON-RPC 2.0 protocol implementation with request/response handling
  - Automatic reconnection with exponential backoff (max 30s delay)
  - Real server integration validated against Snapcast v0.34.0 at 192.168.63.3
  - Methods: get_status, set_client_volume, set_group_mute, set_group_stream

- **Week 3: State Management** - Jan 25
  - StateStore with Qt signals for reactive UI updates
  - SnapcastWorker QThread for running async client in background
  - Thread-safe state updates with optimistic UI support
  - Integration with Qt's signal/slot mechanism

- **Week 4: Configuration** - Jan 25
  - ServerProfile dataclass for connection configuration
  - ConfigManager (QSettings wrapper) for persistent storage
  - Server profile CRUD operations (add, remove, get, list)
  - Auto-connect profile selection
  - Last-connected server tracking

- **Infrastructure**
  - Partial BassCodeBase adoption (CLI tooling only, no git hooks)
  - GitHub Actions CI pipeline with uvx
  - Quality gates: ruff, ruff format, basedpyright, pytest
  - 160 tests passing (141 unit + 20 integration + 1 worker integration)

## [0.1.0] - 2025-01-24

### Added
- Initial project scaffold with BassCodeBase export
- Data models (Server, Client, Group, Source, ServerState)
- TCP API client with JSON-RPC protocol
- Foundation: Month 1 complete (Weeks 1-4)
