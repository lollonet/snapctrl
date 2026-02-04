"""Performance patch: Adaptive debounce timing."""

def __init__(self, ...):
    # Replace fixed 500ms with adaptive timing
    self._rebuild_timer = QTimer()
    self._rebuild_timer.setSingleShot(True)
    self._rebuild_timer.timeout.connect(self._rebuild_menu)

    # Adaptive debounce state
    self._last_rebuild_time = 0
    self._rebuild_frequency = 0
    self._adaptive_delay = 100  # Start with 100ms as documented

def _schedule_rebuild(self, *_args: object) -> None:
    """Schedule adaptive debounced menu rebuild."""
    current_time = time.time()

    # Track rebuild frequency
    if self._last_rebuild_time > 0:
        time_since_last = current_time - self._last_rebuild_time
        # Exponential moving average of frequency
        self._rebuild_frequency = 0.7 * self._rebuild_frequency + 0.3 * (1.0 / time_since_last)

    # Adaptive delay based on frequency
    if self._rebuild_frequency > 5:  # More than 5 rebuilds/sec
        self._adaptive_delay = 200  # Increase delay
    elif self._rebuild_frequency > 2:  # More than 2 rebuilds/sec
        self._adaptive_delay = 150
    else:
        self._adaptive_delay = 100  # Normal delay

    self._rebuild_timer.setInterval(self._adaptive_delay)
    self._rebuild_timer.start()
    self._last_rebuild_time = current_time