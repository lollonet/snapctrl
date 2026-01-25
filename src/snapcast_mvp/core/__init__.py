"""Core business logic layer.

This module contains the core application logic that bridges the
async API client with the Qt UI layer.

Classes:
    StateStore: Central state store with Qt signals.
    SnapcastWorker: QThread worker for async client.
    ConfigManager: QSettings wrapper for configuration.
"""

from snapcast_mvp.core.config import ConfigManager
from snapcast_mvp.core.state import StateStore
from snapcast_mvp.core.worker import SnapcastWorker

__all__ = ["ConfigManager", "StateStore", "SnapcastWorker"]
