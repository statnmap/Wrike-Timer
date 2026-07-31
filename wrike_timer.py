#!/usr/bin/env python3
"""Wrike Timer — chrono tray natif pour Wrike, sans service tiers."""

import argparse
import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wrike_timer import config, tray_app

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_PATH = AUTOSTART_DIR / "wrike-timer.desktop"


def setup_logging():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(config.LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def cmd_set_token():
    token = getpass.getpass("Token API Wrike (Permanent Access Token) : ").strip()
    if not token:
        print("Token vide, abandon.", file=sys.stderr)
        return 1
    config.set_token(token)
    print("Token enregistré.")
    return 0


def cmd_install_autostart():
    AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable
    script_path = Path(__file__).resolve()
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Wrike Timer\n"
        f"Exec={python_path} {script_path}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "NoDisplay=false\n"
    )
    AUTOSTART_PATH.write_text(content, encoding="utf-8")
    print(f"Autostart installé : {AUTOSTART_PATH}")
    return 0


def cmd_uninstall_autostart():
    if AUTOSTART_PATH.exists():
        AUTOSTART_PATH.unlink()
        print(f"Autostart supprimé : {AUTOSTART_PATH}")
    else:
        print("Aucun autostart installé.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Wrike Timer — chrono tray natif pour Wrike")
    parser.add_argument("--set-token", action="store_true", help="Configurer le token API Wrike")
    parser.add_argument("--install-autostart", action="store_true", help="Lancer automatiquement au login")
    parser.add_argument("--uninstall-autostart", action="store_true", help="Retirer le lancement automatique")
    args = parser.parse_args()

    if args.set_token:
        return cmd_set_token()
    if args.install_autostart:
        return cmd_install_autostart()
    if args.uninstall_autostart:
        return cmd_uninstall_autostart()

    setup_logging()
    token = config.get_token()
    cfg = config.load_config()
    if not token:
        logging.getLogger(__name__).warning("Aucun token configuré, lancement en mode non configuré")
        tray_app.run_unconfigured()
        return 0

    tray_app.run(cfg, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
