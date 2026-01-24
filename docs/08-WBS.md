# Snapcast MVP - Work Breakdown Structure (12 Weeks)

## Legend
- 🎯 Milestone
- ✅ Task (1-3 days)
- 📦 Deliverable

---

## Month 1: Foundation (Weeks 1-4)

### Week 1: Project Setup & Core Models
| Task | Estimate | Owner |
|------|----------|-------|
| Create project structure, pyproject.toml | 0.5d | ✅ |
| Set up CI/CD (GitHub Actions) | 0.5d | ✅ |
| Implement data models (Server, Client, Group, Source) | 1d | ✅ |
| Write model unit tests | 1d | ✅ |
| Set up pre-commit hooks | 0.5d | ✅ |

**Deliverable:** Testable models, CI passing

---

### Week 2: WebSocket API Client
| Task | Estimate | Owner |
|------|----------|-------|
| Implement SnapcastClient (WebSocket wrapper) | 1d | 📦 |
| JSON-RPC method dispatch | 1d | 📦 |
| Server.GetStatus parsing | 1d | 📦 |
| Mock WebSocket server for testing | 1d | 📦 |
| API client unit tests | 1d | ✅ |

**Deliverable:** Working SnapcastClient with tests

---

### Week 3: State Management
| Task | Estimate | Owner |
|------|----------|-------|
| Implement StateStore with Qt signals | 1d | 📦 |
| Connect StateStore to SnapcastClient | 1d | 📦 |
| QThread worker for async WebSocket | 1d | 📦 |
| State update tests | 1d | ✅ |
| Integration test: connect → state → UI signal | 1d | ✅ |

**Deliverable:** State management layer working

---

### Week 4: Configuration
| Task | Estimate | Owner |
|------|----------|-------|
| ConfigManager (QSettings wrapper) | 1d | 📦 |
| Server profile CRUD | 1d | 📦 |
| Config persistence tests | 0.5d | ✅ |
| Auto-connect on startup | 0.5d | 📦 |

**🎯 Milestone: Foundation Complete** - Can connect to server, receive state

---

## Month 2: Core UI & Controls (Weeks 5-8)

### Week 5: Main Window & Layout
| Task | Estimate | Owner |
|------|----------|-------|
| MainWindow with tri-pane layout | 1d | 📦 |
| SourcesPanel (list widget) | 1d | 📦 |
| GroupsPanel (scroll area) | 1d | 📦 |
| PropertiesPanel | 0.5d | 📦 |
| Basic styling (QSS) | 0.5d | 📦 |

---

### Week 6: Group Cards
| Task | Estimate | Owner |
|------|----------|-------|
| GroupCard widget | 1d | 📦 |
| VolumeSlider with mute button | 1d | 📦 |
| Source dropdown | 0.5d | 📦 |
| Client list (expandable) | 1d | 📦 |
| UI tests for widgets | 1d | ✅ |

---

### Week 7: Volume Control
| Task | Estimate | Owner |
|------|----------|-------|
| Wire volume slider to API calls | 1d | 📦 |
| Optimistic UI updates | 1d | 📦 |
| Mute toggle functionality | 0.5d | 📦 |
| Volume change debouncing (100ms) | 0.5d | 📦 |
| Integration tests | 1d | ✅ |

---

### Week 8: Source Switching
| Task | Estimate | Owner |
|------|----------|-------|
| Wire source dropdown to API | 0.5d | 📦 |
| Playing indicator (visual) | 0.5d | 📦 |
| Real-time source updates | 1d | 📦 |
| Source metadata display | 1d | 📦 |
| Tests | 1d | ✅ |

**🎯 Milestone: Core Controls Working** - Can control volume and switch sources

---

## Month 3: Polish & Launch (Weeks 9-12)

### Week 9: Connection Management
| Task | Estimate | Owner |
|------|----------|-------|
| ConnectionDialog (add/edit servers) | 1d | 📦 |
| Server selector in toolbar | 0.5d | 📦 |
| Connection status indicator | 0.5d | 📦 |
| Auto-reconnection logic | 1d | 📦 |
| Tests | 1d | ✅ |

---

### Week 10: System Integration
| Task | Estimate | Owner |
|------|----------|-------|
| System tray icon | 1d | 📦 |
| Tray menu (Show/Hide, Quit) | 0.5d | 📦 |
| Quick volume in tray | 1d | 📦 |
| Dark/light theme detection | 0.5d | 📦 |
| Theme styling | 1d | 📦 |

---

### Week 11: Polish & Bug Fixes
| Task | Estimate | Owner |
|------|----------|-------|
| Error handling UI | 1d | 📦 |
| Loading states | 0.5d | 📦 |
| Keyboard shortcuts | 0.5d | 📦 |
| Performance profiling | 1d | 📦 |
| Bug fixes | 2d | 🔧 |

---

### Week 12: Release
| Task | Estimate | Owner |
|------|----------|-------|
| Documentation (README, INSTALL) | 1d | 📦 |
| Packaging (Windows, macOS, Linux) | 2d | 📦 |
| Beta testing | 1d | 📦 |
| Release v0.1.0 | 1d | 🎯 |

**🎯 Milestone: MVP Release** 🚀

---

## Summary

| Month | Focus | Deliverable |
|-------|-------|-------------|
| 1 | Foundation | API + State working |
| 2 | Core UI | Full control capabilities |
| 3 | Polish | Production-ready app |

**Total:** 12 weeks ≈ 3 months

---

*End of Interview Phase*
