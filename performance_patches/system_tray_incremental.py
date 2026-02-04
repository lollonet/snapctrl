"""Performance patch: Incremental menu updates for system tray."""

# Replace _rebuild_menu() with incremental update pattern:

def _update_menu_incremental(self) -> None:
    """Update only changed menu sections instead of full rebuild."""
    # Cache previous state for diff
    if not hasattr(self, '_menu_cache'):
        self._menu_cache = {
            'groups': [],
            'sources': [],
            'connected': False,
            'snapclient_status': None,
        }

    current_state = {
        'groups': self._state.groups,
        'sources': self._state.sources,
        'connected': self._connected,
        'snapclient_status': self._snapclient_mgr.status if self._snapclient_mgr else None,
    }

    # Update only changed sections
    if self._menu_cache['groups'] != current_state['groups']:
        self._update_group_section(current_state['groups'])

    if self._menu_cache['connected'] != current_state['connected']:
        self._update_toggle_action()

    if self._menu_cache['snapclient_status'] != current_state['snapclient_status']:
        self._update_snapclient_section()

    # Update now playing (cheap comparison)
    self._update_now_playing()

    # Cache for next diff
    self._menu_cache = current_state

def _update_group_section(self, groups: list[Group]) -> None:
    """Update only the group entries section of menu."""
    # Remove old group actions (track by object data)
    actions_to_remove = []
    for action in self._menu.actions():
        if hasattr(action, '_snapctrl_group_id'):
            actions_to_remove.append(action)

    for action in actions_to_remove:
        self._menu.removeAction(action)

    # Add new group entries at correct position
    separator_before_local = None
    for action in self._menu.actions():
        if action.text().startswith("Local:"):
            separator_before_local = action
            break

    insert_before = separator_before_local or self._menu.actions()[-3]  # Before prefs

    for group in groups:
        group_clients = [c for c in self._state.clients if c.id in group.client_ids]
        action = self._create_group_action(group, group_clients)
        action._snapctrl_group_id = group.id  # Mark for future removal
        self._menu.insertAction(insert_before, action)

# Key insight: Preserve volume slider widget across updates
def _ensure_volume_slider_preserved(self, target_group: Group) -> None:
    """Ensure volume slider widget is reused, not recreated."""
    if not self._volume_slider:
        # Create once and reuse
        self._volume_slider = VolumeSlider()
        widget_action = QWidgetAction(self._menu)
        widget_action.setDefaultWidget(self._volume_slider)
        self._menu.addAction(widget_action)

    # Update existing slider state without recreation
    self._volume_slider.set_volume(self._calculate_group_volume(target_group))
    self._volume_slider.set_muted(target_group.muted)