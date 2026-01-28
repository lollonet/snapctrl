# SnapCTRL - Work Breakdown Structure (12 Weeks)

## Legend
- 🎯 Milestone
- ✅ Complete
- 📦 In Progress
- 🔧 Future Work

---

## Month 1: Foundation (Weeks 1-4)

### Week 1: Project Setup & Core Models
| Task | Estimate | Status |
|------|----------|--------|
| Create project structure, pyproject.toml | 0.5d | ✅ |
| Set up CI/CD (GitHub Actions) | 0.5d | ✅ |
| Implement data models (Server, Client, Group, Source) | 1d | ✅ |
| Write model unit tests | 1d | ✅ |
| Set up pre-commit hooks (ruff) | 0.5d | ✅ |

**Deliverable:** Testable models, CI passing

---

### Week 2: TCP API Client
| Task | Estimate | Status |
|------|----------|--------|
| Implement SnapcastClient (asyncio TCP) | 1d | ✅ |
| JSON-RPC method dispatch | 1d | ✅ |
| Server.GetStatus parsing | 1d | ✅ |
| Mock TCP server for testing | 1d | ✅ |
| API client unit tests | 1d | ✅ |

**Deliverable:** Working SnapcastClient with tests

**Note:** Snapcast uses raw TCP sockets (not WebSocket) for JSON-RPC on port 1705.

---

### Week 3: State Management
| Task | Estimate | Status |
|------|----------|--------|
| Implement StateStore with Qt signals | 1d | ✅ |
| Connect StateStore to SnapcastClient | 1d | ✅ |
| QThread worker for async TCP | 1d | ✅ |
| State update tests | 1d | ✅ |
| Integration test: connect → state → UI signal | 1d | ✅ |

**Deliverable:** State management layer working

---

### Week 4: Configuration
| Task | Estimate | Status |
|------|----------|--------|
| ConfigManager (QSettings wrapper) | 1d | ✅ |
| Server profile CRUD | 1d | ✅ |
| Config persistence tests | 0.5d | ✅ |
| Auto-connect on startup | 0.5d | ✅ |

**🎯 Milestone: Foundation Complete** - Can connect to server, receive state

---

## Month 2: Core UI & Controls (Weeks 5-9)

### Week 5-6: Core UI Widgets
| Task | Estimate | Status |
|------|----------|--------|
| MainWindow with tri-pane layout | 1d | ✅ |
| VolumeSlider with mute button | 1d | ✅ |
| GroupCard widget | 1d | ✅ |
| Client list (expandable) | 1d | ✅ |
| UI tests for widgets | 1d | ✅ |

---

### Week 7-8: UI Panels
| Task | Estimate | Status |
|------|----------|--------|
| SourcesPanel (list widget) | 1d | ✅ |
| GroupsPanel (scroll area) | 1d | ✅ |
| PropertiesPanel | 1d | ✅ |
| Basic styling (QSS) | 0.5d | ✅ |
| Signal wiring to StateStore | 0.5d | ✅ |

---

### Week 9: Client Controls + Enhancements
| Task | Estimate | Status |
|------|----------|--------|
| ClientCard widget | 1d | ✅ |
| Wire volume slider to API calls | 1d | ✅ |
| Mute toggle functionality | 0.5d | ✅ |
| Connection status indicator | 0.5d | ✅ |
| Integration tests | 1d | ✅ |
| mDNS autodiscovery (PR #3) | 0.5d | ✅ |
| Source details panel (PR #5) | 1d | ✅ |
| Network RTT ping measurement (PR #5) | 0.5d | ✅ |
| Now Playing metadata display | 0.5d | ✅ |
| Cross-platform build configuration | 1d | ✅ |
| App rebranding to SnapCTRL | 0.5d | ✅ |

**🎯 Milestone: UI Foundation Complete** - Full UI with control capabilities

---

### Week 10: MPD Integration (Current)
| Task | Estimate | Status |
|------|----------|--------|
| MPD async client module | 1d | 📦 |
| Track metadata fetching (currentsong, status) | 0.5d | 📦 |
| Album art fetching (albumart, readpicture) | 0.5d | 📦 |
| MPD monitor Qt integration | 0.5d | 📦 |
| Integration with SourcesPanel | 0.5d | 📦 |
| Tests | 1d | 📦 |

**Deliverable:** MPD track metadata + cover art in sources panel

---

## Month 2: Advanced UI (Weeks 10-12)

### Week 10: Drag & Drop / Context Menus
| Task | Estimate | Status |
|------|----------|--------|
| Drag clients between groups | 1d | 🔧 |
| Context menu for groups | 0.5d | 🔧 |
| Context menu for clients | 0.5d | 🔧 |
| Client rename functionality | 1d | 🔧 |
| Tests | 1d | 🔧 |

---

### Week 11: Connection Management
| Task | Estimate | Status |
|------|----------|--------|
| ConnectionDialog (add/edit servers) | 1d | 🔧 |
| Server selector in toolbar | 0.5d | 🔧 |
| Connection status indicator | 0.5d | 🔧 |
| Auto-reconnection logic | 1d | 🔧 |
| Tests | 1d | 🔧 |

---

### Week 12: System Integration
| Task | Estimate | Status |
|------|----------|--------|
| System tray icon | 1d | 🔧 |
| Tray menu (Show/Hide, Quit) | 0.5d | 🔧 |
| Quick volume in tray | 1d | 🔧 |
| Dark/light theme detection | 0.5d | 🔧 |
| Theme styling | 1d | 🔧 |

---

## Month 3: Polish & Launch (Weeks 13-16)

### Week 13: Polish & Bug Fixes
| Task | Estimate | Status |
|------|----------|--------|
| Error handling UI | 1d | 🔧 |
| Loading states | 0.5d | 🔧 |
| Keyboard shortcuts | 0.5d | 🔧 |
| Performance profiling | 1d | 🔧 |
| Bug fixes | 2d | 🔧 |

---

### Week 14: Testing
| Task | Estimate | Status |
|------|----------|--------|
| Integration test suite | 1d | 🔧 |
| Manual testing on real hardware | 1d | 🔧 |
| Bug fixing | 3d | 🔧 |

---

### Week 15: Documentation
| Task | Estimate | Status |
|------|----------|--------|
| User documentation | 1d | 🔧 |
| Installation guides (Win/Mac/Linux) | 1d | 🔧 |
| Developer documentation | 1d | 🔧 |
| Screenshots and demo video | 1d | 🔧 |

---

### Week 16: Release
| Task | Estimate | Status |
|------|----------|--------|
| Packaging (Windows, macOS, Linux) | 2d | 🔧 |
| Beta testing | 1d | 🔧 |
| Release v0.1.0 | 1d | 🎯 |
| GitHub release announcement | 0.5d | 🔧 |

**🎯 Milestone: MVP Release** 🚀

---

## Summary

| Month | Focus | Deliverable | Status |
|-------|-------|-------------|--------|
| 1 | Foundation | API + State working | ✅ Complete |
| 2 | Core UI | Full control capabilities | ✅ UI Complete |
| 2 | Advanced UI | DnD, menus, connection | 🔧 Next |
| 3 | Polish | Production-ready app | 🔧 Future |

**Current Progress:** 10 of 16 weeks complete (62%)

**Test Coverage:** 231 tests passing
- 127 unit tests
- 24 integration tests
- 58 UI tests
- 22 live server tests

---

*Last updated: 2026-01-28*
