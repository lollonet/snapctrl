# SnapCTRL — Claude Code Instructions

## Project Overview

Native desktop controller for Snapcast multi-room audio. PySide6 (Qt6) GUI with TCP JSON-RPC API client, mDNS discovery, MPD integration, and album art.

## Tech Stack

- **Python 3.11+** with PySide6 (Qt6)
- **Package manager**: uv
- **Build**: hatchling
- **Linter/formatter**: ruff
- **Type checker**: basedpyright (strict)
- **Tests**: pytest + pytest-qt
- **Bundling**: PyInstaller

## Project Structure

```
src/snapctrl/
  api/          # TCP JSON-RPC client, MPD protocol, album art fetchers
  core/         # Worker thread, state store, config, discovery, snapclient manager
  models/       # Frozen dataclasses (Client, Group, Source, Server)
  ui/
    panels/     # Sources, Groups, Properties panels
    widgets/    # VolumeSlider, GroupCard, ClientCard, Preferences, Dialogs
    theme.py    # ThemeManager with dark/light palettes
    tokens.py   # Design tokens (spacing, typography, sizing)
    main_window.py
    system_tray.py
tests/          # 934+ tests
docs/           # Specs (00-VISION through 09-DESIGN-SYSTEM)
resources/      # App icons (SVG, ICNS, ICO)
```

## Quality Gates (mandatory before commit)

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run basedpyright src/
uv run pytest tests/
```

All must pass with zero errors.

## Key Conventions

### Code Style
- Line length: 100
- Double quotes, space indentation
- Type hints on all function signatures
- Imports: stdlib → third-party → local (separated by blank lines)
- Prefer pathlib over os.path, f-strings over .format()

### Qt/PySide6 Rules
- **Thread safety**: Never call QWidget methods from background threads. Use Signals with explicit `QueuedConnection` for cross-thread communication.
- **No QTimer.singleShot from Python threads** — undefined Qt behavior, causes SIGSEGV.
- **Widget cleanup**: Use `deleteLater()` after `setParent(None)` when removing widgets to prevent dangling event pointers.
- **Signal blocking**: Use `blockSignals(True)` during programmatic slider/widget updates to prevent signal cascades.
- **Slider interaction**: Check `isSliderDown()` before overwriting slider values to avoid snap-back during user drag.

### Architecture Patterns
- **StateStore** (core/state.py): Single source of truth, emits Qt signals on changes.
- **SnapcastWorker** (core/worker.py): QThread for async TCP operations. UI never calls API directly.
- **Differential updates**: GroupsPanel reuses existing GroupCard widgets; only creates/removes cards that changed.
- **Design tokens**: All spacing, typography, and sizing via frozen dataclass singletons in `tokens.py`. No hardcoded pixel values.
- **ThemeManager**: Singleton with dark/light palettes. UI reads `theme_manager.palette` for colors.

### Models
- Frozen dataclasses (`@dataclass(frozen=True)`) for all data models.
- Immutable — create new instances instead of mutating.

### Testing
- pytest with pytest-qt for widget tests
- Mock background threads in tests to prevent SIGSEGV during pytest-qt cleanup
- Use fixtures over setup/teardown
- Test files: `tests/test_*.py`

## Git Workflow

- Always use PRs — never push directly to main
- Branch naming: `feature/<description>` or `fix/<description>`
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Check CI before merge

## Running the App

```bash
uv run python -m snapctrl                    # auto-discover server via mDNS
uv run python -m snapctrl 192.168.1.100      # specify server
uv run python -m snapctrl --host raspy 1705  # host + port
```

## Common Gotchas

- The snapclient streaming port is **1704**, the control/JSON-RPC port is **1705**. Don't mix them up.
- `SF Pro Text` font warning on non-macOS is harmless (falls back to system font).
- Album art uses a fallback chain: Snapcast HTTP → MPD `readpicture` → iTunes API → MusicBrainz.
- `__main__.py:main()` is a large function wiring everything together — this is known tech debt.
