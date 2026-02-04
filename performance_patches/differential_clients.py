"""Performance patch: Differential client widget updates."""

def _update_client_cards_differential(self, clients: list[Client]) -> None:
    """Update client cards using differential updates instead of recreation."""
    new_client_ids = {c.id for c in clients}
    existing_client_ids = set(self._client_cards.keys())

    # Remove cards for clients that no longer exist
    removed_ids = existing_client_ids - new_client_ids
    for client_id in removed_ids:
        card = self._client_cards.pop(client_id)
        card.setParent(None)

    # Update existing cards and add new ones
    for client in clients:
        if client.id in self._client_cards:
            # Update existing card in-place (NO RECREATION)
            card = self._client_cards[client.id]
            card.update_state(
                name=client.name,
                volume=client.volume,
                muted=client.muted,
                connected=client.connected
            )
        else:
            # Create new card only for new clients
            card = ClientCard(
                client_id=client.id,
                name=client.name,
                volume=client.volume,
                muted=client.muted,
                connected=client.connected,
            )
            # Connect signals only once for new cards
            card.volume_changed.connect(self.client_volume_changed.emit)
            card.mute_toggled.connect(self.client_mute_toggled.emit)
            card.clicked.connect(self.client_clicked.emit)
            card.rename_requested.connect(self.client_rename_requested.emit)

            self._client_cards[client.id] = card
            self._clients_layout.addWidget(card)

    # Update count label
    self._client_list_label.setText(f"Clients: ({len(clients)})")

# Add this method to ClientCard class for in-place updates
def update_state(self, name: str, volume: int, muted: bool, connected: bool) -> None:
    """Update client state without widget recreation."""
    if self._name != name:
        self._name = name
        self._name_label.setText(name)

    if self._volume != volume:
        self._volume = volume
        self._volume_slider.set_volume(volume)

    if self._muted != muted:
        self._muted = muted
        self._volume_slider.set_muted(muted)

    if self._connected != connected:
        self._connected = connected
        self._update_connection_visual(connected)

def _update_connection_visual(self, connected: bool) -> None:
    """Update connection visual indicator efficiently."""
    p = theme_manager.palette
    if connected:
        self.setStyleSheet(f"border-left: 3px solid {p.success};")
    else:
        self.setStyleSheet(f"border-left: 3px solid {p.error};")