#!/usr/bin/env python3
"""Affiche le tray avec des données factices, pour prendre une capture d'écran (README, doc...).

Usage:
    .venv/bin/python scripts/fake_tray_screenshot.py

N'utilise aucun vrai token ni le vrai state.json/config.json de la machine :
le client Wrike est un stub et le state est redirigé vers un fichier temporaire.
"""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wrike_timer.env import sanitize_snap_env

# Doit être appelé avant d'importer tray_app (qui importe pystray/GTK) —
# voir wrike_timer.py, même ordre pour la même raison.
sanitize_snap_env()

from wrike_timer import config, timer
from wrike_timer import tray_app as tray_app_module
from wrike_timer.tray_app import TrayApp

FAKE_CFG = {
    "recent_tasks_limit": 10,
    "recent_tasks_lookback_days": 30,
    "refresh_interval_seconds": 3600,
    "timesheet_url": "",
}

FAKE_RECENT_TASKS = [
    {"id": "A", "title": "Maquette page d'accueil", "status": "Active"},
    {"id": "B", "title": "Corriger bug export PDF", "status": "Active"},
    {"id": "C", "title": "Revue de code client X", "status": "Active"},
    {"id": "D", "title": "Ancienne tâche archivée", "status": "Completed"},
]


class FakeClient:
    """Stub sans réseau — même rôle que FakeClient dans tests/test_tray_app.py."""

    def __init__(self, *args, **kwargs):
        pass


def main():
    tray_app_module.WrikeClient = FakeClient
    config.STATE_PATH = Path(tempfile.mkdtemp()) / "state.json"

    app = TrayApp("fake-token", FAKE_CFG)
    app.state["recent_tasks"] = FAKE_RECENT_TASKS
    app.active_timer = timer.TimerState(
        task_id="Z",
        task_title="Intégration API paiement",
        started_at=time.time() - 4354,  # ~01:12:34
    )
    app.today_total_hours = 3.5
    app._refresh_icon_and_menu()

    print("Icône tray affichée avec des données factices. Clique sur l'icône pour ouvrir le menu.")
    print("Ctrl+C ou l'entrée 'Quitter' du menu pour arrêter.")
    app.icon.run()


if __name__ == "__main__":
    main()
