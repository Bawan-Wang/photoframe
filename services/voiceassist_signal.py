"""Background poller for /tmp/voiceassist_signal.json.

When the signal file's `photoframe_should_exit` flag flips to true,
invoke `on_exit_request` on the Kivy main thread (caller's responsibility
to bounce back via `Clock.schedule_once`).

This module is intentionally tiny and only depends on the stdlib so it
can be imported by photoframe's apt-installed system Python without
pulling in any voiceassist dependencies.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable

SIGNAL_PATH = Path("/tmp/voiceassist_signal.json")
POLL_INTERVAL = 0.25


def _read() -> dict:
    try:
        with SIGNAL_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def start(on_exit_request: Callable[[], None]) -> threading.Thread:
    """Spawn a daemon thread that polls the signal file and fires
    `on_exit_request()` exactly once when photoframe_should_exit goes true."""
    initial_ts = _read().get("ts", 0)

    def loop() -> None:
        # Ignore any pre-existing 'true' that was set BEFORE photoframe
        # started — only react to fresh requests (newer ts).
        while True:
            data = _read()
            if data.get("photoframe_should_exit") and data.get("ts", 0) > initial_ts:
                try:
                    on_exit_request()
                except Exception:
                    pass
                return
            time.sleep(POLL_INTERVAL)

    t = threading.Thread(target=loop, daemon=True, name="voiceassist-signal-poller")
    t.start()
    return t
