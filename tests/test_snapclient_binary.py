"""Tests for snapclient binary discovery and validation."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import snapctrl.core.snapclient_binary as snapclient_binary_mod
from snapctrl.core.snapclient_binary import (
    VERSION_PREFIX,
    bundled_snapclient_path,
    find_snapclient,
    validate_snapclient,
)


class TestBundledSnapclientPath:
    """Test bundled binary path resolution."""

    def test_returns_path_object(self) -> None:
        """Bundled path is always a Path, even if it doesn't exist."""
        result = bundled_snapclient_path()
        assert isinstance(result, Path)

    def test_ends_with_bin_snapclient(self) -> None:
        """Bundled path ends with bin/snapclient."""
        result = bundled_snapclient_path()
        assert result.name == "snapclient"
        assert result.parent.name == "bin"

    @patch("snapctrl.core.snapclient_binary.sys")
    def test_frozen_uses_meipass(self, mock_sys: object) -> None:
        """When frozen (PyInstaller), uses resolved sys._MEIPASS."""
        mock_sys.frozen = True  # type: ignore[union-attr]
        mock_sys._MEIPASS = "/tmp/pyinstaller_extract"  # type: ignore[union-attr]  # noqa: SLF001
        result = snapclient_binary_mod.bundled_snapclient_path()
        expected = Path("/tmp/pyinstaller_extract").resolve() / "bin" / "snapclient"
        assert result == expected


class TestFindSnapclient:
    """Test binary discovery order."""

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Returns None when no binary found anywhere."""
        with (
            patch("snapctrl.core.snapclient_binary.bundled_snapclient_path") as mock_bundled,
            patch("snapctrl.core.snapclient_binary.shutil.which", return_value=None),
        ):
            mock_bundled.return_value = tmp_path / "nonexistent" / "snapclient"
            result = find_snapclient()
            assert result is None

    def test_prefers_bundled(self, tmp_path: Path) -> None:
        """Bundled binary has highest priority."""
        bundled = tmp_path / "bin" / "snapclient"
        bundled.parent.mkdir(parents=True)
        bundled.touch()

        with patch("snapctrl.core.snapclient_binary.bundled_snapclient_path") as mock_bundled:
            mock_bundled.return_value = bundled
            result = find_snapclient()
            assert result == bundled

    def test_falls_back_to_path(self, tmp_path: Path) -> None:
        """Falls back to system PATH when bundled not found."""
        with (
            patch("snapctrl.core.snapclient_binary.bundled_snapclient_path") as mock_bundled,
            patch(
                "snapctrl.core.snapclient_binary.shutil.which",
                return_value="/usr/local/bin/snapclient",
            ),
        ):
            mock_bundled.return_value = tmp_path / "nonexistent" / "snapclient"
            result = find_snapclient()
            assert result == Path("/usr/local/bin/snapclient")

    def test_falls_back_to_configured(self, tmp_path: Path) -> None:
        """Falls back to user-configured path as last resort."""
        configured = tmp_path / "my_snapclient"
        configured.touch()

        with (
            patch("snapctrl.core.snapclient_binary.bundled_snapclient_path") as mock_bundled,
            patch("snapctrl.core.snapclient_binary.shutil.which", return_value=None),
        ):
            mock_bundled.return_value = tmp_path / "nonexistent" / "snapclient"
            result = find_snapclient(str(configured))
            assert result == configured

    def test_configured_path_not_found(self, tmp_path: Path) -> None:
        """Returns None when configured path doesn't exist."""
        with (
            patch("snapctrl.core.snapclient_binary.bundled_snapclient_path") as mock_bundled,
            patch("snapctrl.core.snapclient_binary.shutil.which", return_value=None),
        ):
            mock_bundled.return_value = tmp_path / "nonexistent" / "snapclient"
            result = find_snapclient("/no/such/path")
            assert result is None


class TestValidateSnapclient:
    """Test binary validation."""

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        """Returns (False, error) for nonexistent file."""
        valid, msg = validate_snapclient(tmp_path / "nope")
        assert valid is False
        assert "not found" in msg.lower()

    def test_symlink_rejected(self, tmp_path: Path) -> None:
        """Returns (False, error) for symlink."""
        real_bin = tmp_path / "real_snapclient"
        real_bin.touch()
        symlink = tmp_path / "snapclient_link"
        symlink.symlink_to(real_bin)

        valid, msg = validate_snapclient(symlink)
        assert valid is False
        assert "symlink" in msg

    def test_valid_binary(self, tmp_path: Path) -> None:
        """Returns (True, version) for valid binary."""
        fake_bin = tmp_path / "snapclient"
        fake_bin.write_text("#!/bin/sh\necho 'snapclient v0.34.0'\n")
        fake_bin.chmod(0o755)

        with patch("snapctrl.core.snapclient_binary.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "snapclient v0.34.0\nCopyright..."
            mock_run.return_value.stderr = ""
            valid, version = validate_snapclient(fake_bin)
            assert valid is True
            assert version == "0.34.0"

    def test_unexpected_output(self, tmp_path: Path) -> None:
        """Returns (False, error) for unexpected output."""
        fake_bin = tmp_path / "snapclient"
        fake_bin.write_text("#!/bin/sh\necho 'something else'\n")
        fake_bin.chmod(0o755)

        with patch("snapctrl.core.snapclient_binary.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "something else"
            mock_run.return_value.stderr = ""
            valid, msg = validate_snapclient(fake_bin)
            assert valid is False
            assert "unexpected" in msg.lower()

    def test_timeout(self, tmp_path: Path) -> None:
        """Returns (False, error) on timeout."""
        fake_bin = tmp_path / "snapclient"
        fake_bin.touch()

        with patch("snapctrl.core.snapclient_binary.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="snapclient", timeout=5)
            valid, msg = validate_snapclient(fake_bin)
            assert valid is False
            assert "timed out" in msg.lower()

    def test_version_prefix_constant(self) -> None:
        """Version prefix matches expected format."""
        assert VERSION_PREFIX == "snapclient v"
