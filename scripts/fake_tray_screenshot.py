#!/usr/bin/env python3
"""Show the tray with fake data, for taking a screenshot (README, docs...).

Usage:
    .venv/bin/python scripts/fake_tray_screenshot.py

Uses no real token and none of the machine's real state.json/config.json:
the Wrike client is a stub and the state is redirected to a temp file.
"""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wrike_timer.env import sanitize_snap_env

# Must be called before importing tray_app (which imports pystray/GTK) —
# see wrike_timer.py, same order for the same reason.
sanitize_snap_env()

from wrike_timer import config, timer
from wrike_timer import tray_app as tray_app_module
from wrike_timer.tray_app import TrayApp

FAKE_CFG = {
    "recent_tasks_limit": 10,
    "recent_tasks_lookback_days": 30,
    "refresh_interval_seconds": 3600,
    "timesheet_url": "",
    "language": "en",
}

FAKE_RECENT_TASKS = [
    {"id": "A", "title": "Homepage mockup", "status": "Active"},
    {"id": "B", "title": "Fix PDF export bug", "status": "Active"},
    {"id": "C", "title": "Code review for client X", "status": "Active"},
    {"id": "D", "title": "Old archived task", "status": "Completed"},
]


class FakeClient:
    """Network-free stub — same role as FakeClient in tests/test_tray_app.py."""

    def __init__(self, *args, **kwargs):
        pass


def main():
    tray_app_module.WrikeClient = FakeClient
    config.STATE_PATH = Path(tempfile.mkdtemp()) / "state.json"

    app = TrayApp("fake-token", FAKE_CFG)
    app.state["recent_tasks"] = FAKE_RECENT_TASKS
    app.active_timer = timer.TimerState(
        task_id="Z",
        task_title="Payment API integration",
        started_at=time.time() - 4354,  # ~01:12:34
    )
    app.today_total_hours = 3.5
    app._refresh_icon_and_menu()

    print("Tray icon shown with fake data. Click the icon to open the menu.")
    print("Ctrl+C or the 'Quit' entry in the menu to stop.")
    app.icon.run()


if __name__ == "__main__":
    main()
