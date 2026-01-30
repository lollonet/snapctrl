"""Snapclient binary discovery and validation.

Locates the snapclient binary using a priority-ordered search:
bundled path → system PATH → user-configured path.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Version line pattern: "snapclient v0.34.0"
VERSION_PREFIX = "snapclient v"


def bundled_snapclient_path() -> Path:
    """Return the expected path for a bundled snapclient binary.

    When running from a PyInstaller bundle, the binary is in the ``bin/``
    subdirectory next to the executable.  When running from source, this
    returns a path that will not exist (caller should check).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: sys._MEIPASS is the temp extraction dir
        base = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]  # noqa: SLF001
    else:
        # Running from source — use project root as a fallback
        base = Path(__file__).resolve().parents[3]
    return base / "bin" / "snapclient"


def find_snapclient(configured_path: str | None = None) -> Path | None:
    """Find the snapclient binary using priority-ordered search.

    Search order:
    1. Bundled binary (inside PyInstaller package)
    2. System PATH (``shutil.which``)
    3. User-configured path

    Args:
        configured_path: Optional user-configured path to snapclient.

    Returns:
        Path to snapclient if found, None otherwise.
    """
    # 1. Bundled
    bundled = bundled_snapclient_path()
    if bundled.is_file():
        logger.debug("Found bundled snapclient: %s", bundled)
        return bundled

    # 2. System PATH
    system = shutil.which("snapclient")
    if system is not None:
        logger.debug("Found snapclient in PATH: %s", system)
        return Path(system)

    # 3. User-configured
    if configured_path:
        user_path = Path(configured_path)
        if user_path.is_file():
            logger.debug("Found user-configured snapclient: %s", user_path)
            return user_path
        logger.warning("User-configured snapclient not found: %s", configured_path)

    logger.info("snapclient binary not found")
    return None


def validate_snapclient(path: Path) -> tuple[bool, str]:
    """Validate a snapclient binary by running ``--version``.

    Args:
        path: Path to the snapclient binary.

    Returns:
        Tuple of (is_valid, version_string).
        On failure, version_string contains the error message.
    """
    if not path.is_file() or path.is_symlink():
        reason = "symlink" if path.is_symlink() else "not found"
        return False, f"Invalid binary path ({reason}): {path}"

    try:
        resolved = path.resolve(strict=True)
        result = subprocess.run(
            [str(resolved), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        # First line should be "snapclient v0.34.0"
        first_line = output.split("\n")[0] if output else ""
        if first_line.startswith(VERSION_PREFIX):
            version = first_line[len(VERSION_PREFIX) :]
            logger.info("Validated snapclient %s at %s", version, path)
            return True, version
        return False, f"Unexpected output: {first_line}"
    except FileNotFoundError:
        return False, f"Binary not executable: {path}"
    except subprocess.TimeoutExpired:
        return False, "Timed out running --version"
    except OSError as e:
        return False, f"OS error: {e}"
