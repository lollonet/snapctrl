# SnapCTRL - Vision Document

## Project Overview

**Name**: SnapCTRL (formerly Snapcast MVP)
**Status**: Active Development
**Created**: 2025-01-24
**Updated**: 2026-01-28
**Timeline**: ~3 months (12 weeks)
**Target Platforms**: Windows, macOS, Linux

---

## Problem Statement

Snapcast is a powerful multi-room audio solution, but controlling it typically requires:
- A web interface (snapweb) that runs in a browser
- Mobile apps with limited functionality
- Command-line tools for advanced operations

**Home audio enthusiasts** need a native desktop application that provides:
- Quick access to volume controls across all rooms
- Visual management of groups and audio sources
- Real-time status monitoring
- Cross-platform compatibility

---

## Vision

> A native desktop controller for Snapcast that feels at home on Windows, macOS, and Linux.

**Success means**:
- A user can open the app and immediately see what's playing where
- See track metadata (title, artist, album, cover art) for each source
- Volume adjustments happen instantly with visual feedback
- Switching audio sources between rooms is intuitive
- Zero-configuration startup via mDNS autodiscovery
- The app feels responsive and native on each platform

---

## Target Users

### Primary: Home Audio Enthusiasts
- DIY smart home users
- Multi-room audio setup owners
- Technical users comfortable with server configuration
- **Use case**: Daily control of whole-house music

### Secondary: Small Business Owners
- Cafes, restaurants, retail spaces
- Need zone-based audio control
- **Use case**: Background music management

---

## Out of Scope for MVP

| Feature | Rationale |
|---------|-----------|
| Multi-server management | Single server is sufficient for most home users |
| Server configuration editing | Use existing tools (SSH, config files) |
| Mobile apps | Desktop-only for MVP |
| Advanced automation | Use home automation systems |
| Audio visualization | Nice-to-have, not core |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to first connection | < 2 minutes | User testing |
| Volume control latency | < 100ms | Automated tests |
| Memory usage | < 200MB | Profiling |
| Startup time | < 2 seconds | Benchmark |
| Platform coverage | Win/macOS/Linux | Release checklist |

---

## Non-Negotiables

1. **Native look and feel** on each platform
2. **Real-time updates** via WebSocket
3. **Offline graceful degradation** (show last known state)
4. **Type-safe** codebase (strict type checking)
5. **Test coverage** ≥ 70% for core modules

---

*Next: [Requirements](docs/01-REQUIREMENTS.md) →*
