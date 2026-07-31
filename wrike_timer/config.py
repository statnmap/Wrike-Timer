"""Configuration and token storage for Wrike Timer.

Token resolution order: system keyring first, then a plaintext fallback in
config.json (chmod 600) if no keyring backend is available on the machine.
"""

import json
import logging
import os
from pathlib import Path

KEYRING_SERVICE = "wrike-timer"
KEYRING_USERNAME = "api_token"

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wrike-timer"
CONFIG_PATH = CONFIG_DIR / "config.json"

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "wrike-timer"
STATE_PATH = DATA_DIR / "state.json"
LOG_PATH = DATA_DIR / "wrike-timer.log"

DEFAULT_CONFIG = {
    "refresh_interval_seconds": 30,
    "recent_tasks_limit": 10,
    "recent_tasks_lookback_days": 30,
}

log = logging.getLogger(__name__)


def load_config():
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config.update(json.load(f))
    return config


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def get_token():
    try:
        import keyring

        token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if token:
            return token
    except Exception:
        log.exception("Keyring lookup failed, falling back to config.json")

    config = load_config()
    return config.get("token")


def set_token(token):
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        # Token now lives in the keyring: make sure no stale copy remains on disk.
        config = load_config()
        if "token" in config:
            del config["token"]
            save_config(config)
        return
    except Exception:
        log.warning("No usable keyring backend, storing token in config.json instead", exc_info=True)

    config = load_config()
    config["token"] = token
    save_config(config)
