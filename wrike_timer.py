#!/usr/bin/env python3
"""Wrike Timer — native tray timer for Wrike, no third-party service."""

import argparse
import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wrike_timer import config

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_PATH = AUTOSTART_DIR / "wrike-timer.desktop"


def setup_logging():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(config.LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def cmd_set_token(token_arg=None):
    if token_arg is not None:
        token = token_arg.strip()
    else:
        try:
            token = getpass.getpass("Token API Wrike (Permanent Access Token) : ").strip()
        except EOFError:
            print(
                "Saisie interactive impossible (stdin non-TTY). "
                "Lance cette commande depuis un vrai terminal, ou utilise --token <valeur>.",
                file=sys.stderr,
            )
            return 1
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
    parser.add_argument(
        "--token", metavar="TOKEN", help="Token à utiliser avec --set-token, évite le prompt interactif"
    )
    parser.add_argument("--install-autostart", action="store_true", help="Lancer automatiquement au login")
    parser.add_argument("--uninstall-autostart", action="store_true", help="Retirer le lancement automatique")
    args = parser.parse_args()

    if args.set_token:
        return cmd_set_token(args.token)
    if args.install_autostart:
        return cmd_install_autostart()
    if args.uninstall_autostart:
        return cmd_uninstall_autostart()

    from wrike_timer.env import sanitize_snap_env

    sanitize_snap_env()
    from wrike_timer import tray_app  # imported lazily: pulls in pystray/GTK, only needed to run the tray

    setup_logging()
    token = config.get_token()
    cfg = config.load_config()
    if not token:
        logging.getLogger(__name__).warning("No token configured, starting in unconfigured mode")
        tray_app.run_unconfigured(cfg)
        return 0

    tray_app.run(cfg, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
