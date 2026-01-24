# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Data Models** (Week 1)
  - Immutable frozen dataclasses for Client, Group, Server, Source
  - ServerState aggregate with lookup methods
  - Full type hints with basedpyright strict mode compliance
  - 100% test coverage on all models

- **TCP API Client** (Week 2)
  - SnapcastClient using asyncio TCP sockets (Snapcast uses raw TCP, not WebSocket)
  - JSON-RPC 2.0 protocol implementation
  - Automatic reconnection with exponential backoff
  - Real server integration validated against Snapcast v0.34.0
  - 72% test coverage

- **Infrastructure**
  - Partial BassCodeBase adoption (CLI tooling only, no git hooks)
  - GitHub Actions CI pipeline with uvx
  - Quality gates: ruff, ruff format, basedpyright, pytest
  - 99 tests passing (79 unit + 20 integration)

## [0.1.0] - 2025-01-24

### Added
- Initial project scaffold
- Week 1: Data Models (complete)
- Week 2: TCP API Client (complete)
