"""Runs before test collection so importing tray_app (pystray/GTK) doesn't
crash when pytest is launched from a snap-packaged terminal. See
wrike_timer/env.py for why.
"""

from wrike_timer.env import sanitize_snap_env

sanitize_snap_env()
