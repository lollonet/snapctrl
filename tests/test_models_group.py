"""Tests for Group model."""

import pytest

from snapctrl.models.group import Group


class TestGroup:
    """Tests for Group dataclass."""

    def test_group_creation_with_defaults(self) -> None:
        """Test creating a group with default values."""
        group = Group(id="group-1")
        assert group.id == "group-1"
        assert group.name == ""
        assert group.stream_id == ""
        assert group.muted is False
        assert group.client_ids == []

    def test_group_creation_with_all_params(self) -> None:
        """Test creating a group with all parameters."""
        group = Group(
            id="group-2",
            name="Downstairs",
            stream_id="stream-1",
            muted=True,
            client_ids=["client-1", "client-2", "client-3"],
        )
        assert group.id == "group-2"
        assert group.name == "Downstairs"
        assert group.stream_id == "stream-1"
        assert group.muted is True
        assert group.client_ids == ["client-1", "client-2", "client-3"]

    def test_stream_alias(self) -> None:
        """Test stream is an alias for stream_id."""
        group = Group(id="group-1", stream_id="stream-5")
        assert group.stream == "stream-5"

    def test_client_count(self) -> None:
        """Test client_count returns number of clients."""
        group = Group(id="group-1", client_ids=["c1", "c2", "c3"])
        assert group.client_count == 3

    def test_client_count_empty(self) -> None:
        """Test client_count returns 0 for empty group."""
        group = Group(id="group-1")
        assert group.client_count == 0

    def test_is_empty(self) -> None:
        """Test is_empty returns True when no clients."""
        group = Group(id="group-1")
        assert group.is_empty is True

    def test_is_empty_false(self) -> None:
        """Test is_empty returns False when has clients."""
        group = Group(id="group-1", client_ids=["client-1"])
        assert group.is_empty is False

    def test_group_is_immutable(self) -> None:
        """Test that Group instances are immutable (frozen)."""
        group = Group(id="group-1")
        with pytest.raises(Exception):  # FrozenInstanceError
            group.name = "Changed"  # type: ignore[misc]

    def test_group_equality(self) -> None:
        """Test group equality comparison."""
        group1 = Group(id="group-1", name="Test")
        group2 = Group(id="group-1", name="Test")
        group3 = Group(id="group-1", name="Different")

        assert group1 == group2
        assert group1 != group3

    def test_mutable_default_factory(self) -> None:
        """Test that default_factory works correctly for list."""
        group1 = Group(id="group-1")
        group2 = Group(id="group-2")

        # Each instance should have its own list
        group1.client_ids.append("client-1")

        assert len(group1.client_ids) == 1
        assert len(group2.client_ids) == 0
