"""Core business logic layer.

This module contains the core application logic that bridges the
async API client with the Qt UI layer.

Classes:
    StateStore: Central state store with Qt signals.
    SnapcastWorker: QThread worker for async client.
    ConfigManager: QSettings wrapper for configuration.
    Controller: Bridges UI signals to API calls.
"""

from snapctrl.core.config import ConfigManager
from snapctrl.core.controller import Controller
from snapctrl.core.state import StateStore
from snapctrl.core.worker import SnapcastWorker

__all__ = ["ConfigManager", "Controller", "StateStore", "SnapcastWorker"]
