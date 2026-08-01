"""System tray UI: menu construction, refresh thread, icon rendering."""

import logging
import threading
import time
import webbrowser
from datetime import date

import pystray
from PIL import Image, ImageDraw

from . import config, timer
from .state_store import StateStore
from .wrike_api import WrikeApiError, WrikeClient

log = logging.getLogger(__name__)

ICON_SIZE = 64
COLOR_IDLE = (120, 120, 120, 255)
COLOR_ACTIVE = (220, 50, 47, 255)
COLOR_UNCONFIGURED = (200, 160, 0, 255)

# A gap this large between two heartbeats while a timer was active means the
# app (or the machine) wasn't running for a while — suspend, shutdown, crash —
# not that someone genuinely worked uninterrupted for that long.
HEARTBEAT_GAP_WARNING_SECONDS = 5 * 60


def _make_icon(color):
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = 6
    draw.ellipse((margin, margin, ICON_SIZE - margin, ICON_SIZE - margin), fill=color)
    return image


class TrayApp:
    def __init__(self, token, cfg):
        self.cfg = cfg
        self.client = WrikeClient(token)
        self.store = StateStore(config.STATE_PATH)
        self.state = self.store.load()
        self.active_timer = (
            timer.TimerState.from_dict(self.state["active_timer"]) if self.state.get("active_timer") else None
        )
        self.today_total_hours = None
        self.resume_gap_seconds = None
        if self.active_timer:
            gap = timer.detect_resume_gap(self.state.get("last_heartbeat"), time.time(), HEARTBEAT_GAP_WARNING_SECONDS)
            if gap is not None:
                self.resume_gap_seconds = gap
                log.warning("Resumed an active timer after a %.0fs gap (app wasn't running)", gap)

        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.icon = pystray.Icon(
            "wrike-timer",
            _make_icon(COLOR_ACTIVE if self.active_timer else COLOR_IDLE),
            "Wrike Timer",
        )
        self.icon.menu = self._build_menu()

    def run(self):
        self._last_tick = time.time()
        self._refresh_recent_tasks()
        self._refresh_today_total()
        self._refresh_icon_and_menu()
        thread = threading.Thread(target=self._background_loop, daemon=True)
        thread.start()
        self.icon.run()

    def _persist_active_timer(self):
        self.state["active_timer"] = self.active_timer.to_dict() if self.active_timer else None
        self.store.save(self.state)

    def _refresh_icon_and_menu(self):
        self.icon.icon = _make_icon(COLOR_ACTIVE if self.active_timer else COLOR_IDLE)
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    def _refresh_recent_tasks(self):
        try:
            task_ids = self.client.get_recent_task_ids(
                limit=self.cfg["recent_tasks_limit"],
                lookback_days=self.cfg["recent_tasks_lookback_days"],
            )
            tasks_by_id = {t["id"]: t for t in self.client.get_tasks(task_ids)}
            ordered = [tasks_by_id[tid] for tid in task_ids if tid in tasks_by_id]
        except WrikeApiError:
            log.exception("Failed to refresh recent tasks")
            return
        with self.lock:
            self.state["recent_tasks"] = ordered
            self.store.save(self.state)

    def _refresh_today_total(self):
        try:
            total = self.client.get_hours_logged_on(date.today().isoformat())
        except WrikeApiError:
            log.exception("Failed to refresh today's total hours")
            return
        with self.lock:
            self.today_total_hours = total

    def _update_heartbeat(self):
        self.state["last_heartbeat"] = time.time()
        self.store.save(self.state)

    def _post_or_queue(self, entry):
        try:
            self.client.post_timelog(entry["task_id"], entry["hours"], entry["tracked_date"], entry["comment"])
            log.info("Timelog posted: task=%s hours=%.2f", entry["task_id"], entry["hours"])
        except WrikeApiError:
            log.exception("Failed to post timelog for task=%s, queueing for retry", entry["task_id"])
            self.state["pending_timelogs"].append(entry)
            self.store.save(self.state)

    def _make_start_handler(self, task):
        def handler(icon, item):
            with self.lock:
                if self.active_timer is not None:
                    return
                self.active_timer = timer.start(task["id"], task["title"])
                self._persist_active_timer()
            self._refresh_icon_and_menu()

        return handler

    def _on_stop(self, icon, item):
        with self.lock:
            if self.active_timer is None:
                return
            active = self.active_timer
            duration_seconds, tracked_date = timer.stop(active)
            self.active_timer = None
            self.resume_gap_seconds = None
            self._persist_active_timer()
            entry = {
                "task_id": active.task_id,
                "hours": round(timer.seconds_to_hours(duration_seconds), 4),
                "tracked_date": tracked_date,
                "comment": "",
            }
            self._post_or_queue(entry)
        self._refresh_icon_and_menu()

    def _on_retry_pending(self, icon, item):
        with self.lock:
            pending = list(self.state.get("pending_timelogs", []))
            remaining = []
            for entry in pending:
                try:
                    self.client.post_timelog(entry["task_id"], entry["hours"], entry["tracked_date"], entry["comment"])
                    log.info("Retried timelog succeeded: task=%s", entry["task_id"])
                except WrikeApiError:
                    log.warning("Retry still failing for task=%s", entry["task_id"], exc_info=True)
                    remaining.append(entry)
            self.state["pending_timelogs"] = remaining
            self.store.save(self.state)
        self._refresh_icon_and_menu()

    def _on_refresh(self, icon, item):
        self._refresh_recent_tasks()
        self._refresh_today_total()
        self._refresh_icon_and_menu()

    def _on_settings(self, icon, item):
        message = f"Config: {config.CONFIG_PATH}\nLogs: {config.LOG_PATH}"
        try:
            icon.notify(message, "Wrike Timer — Paramètres")
        except Exception:
            log.info("Settings: %s", message.replace("\n", " | "))

    def _on_open_timesheet(self, icon, item):
        webbrowser.open(self.cfg["timesheet_url"])

    def _on_timesheet_url_missing(self, icon, item):
        message = (
            f'Ajoute "timesheet_url": "<ton url>" dans {config.CONFIG_PATH}\n'
            "(copie l'URL depuis ton navigateur, sur ta page Timesheets Wrike)."
        )
        try:
            icon.notify(message, "Wrike Timer — Feuille de temps")
        except Exception:
            log.info("Timesheet URL not configured: %s", message.replace("\n", " "))

    def _on_quit(self, icon, item):
        self.stop_event.set()
        icon.stop()

    def _build_menu(self):
        items = []

        if self.today_total_hours is not None:
            items.append(
                pystray.MenuItem(f"📅 Aujourd'hui : {timer.format_hours(self.today_total_hours)}", None, enabled=False)
            )
            items.append(pystray.Menu.SEPARATOR)

        if self.active_timer:
            elapsed = timer.format_duration(timer.elapsed_seconds(self.active_timer))
            items.append(pystray.MenuItem(f"🔴 {self.active_timer.task_title} — {elapsed}", self._on_stop))
            if self.resume_gap_seconds:
                gap_label = timer.format_hours(self.resume_gap_seconds / 3600)
                items.append(
                    pystray.MenuItem(f"⚠️ Reprise après ~{gap_label} d'interruption détectée", None, enabled=False)
                )
            items.append(pystray.Menu.SEPARATOR)

        recent = self.state.get("recent_tasks", [])
        if recent:
            for task in recent:
                label = timer.task_label(task["title"], task.get("status"))
                items.append(
                    pystray.MenuItem(label, self._make_start_handler(task), enabled=self.active_timer is None)
                )
        else:
            items.append(pystray.MenuItem("(aucun ticket récent — Rafraîchir)", None, enabled=False))
        items.append(pystray.Menu.SEPARATOR)

        pending = self.state.get("pending_timelogs", [])
        if pending:
            items.append(pystray.MenuItem(f"⚠ {len(pending)} envoi(s) en attente", self._on_retry_pending))

        items.append(pystray.MenuItem("🔄 Rafraîchir la liste", self._on_refresh))
        if self.cfg.get("timesheet_url"):
            items.append(pystray.MenuItem("📊 Ouvrir ma feuille de temps", self._on_open_timesheet))
        else:
            items.append(pystray.MenuItem("📊 Feuille de temps non configurée (clic = comment faire)", self._on_timesheet_url_missing))
        items.append(pystray.MenuItem("⚙️ Paramètres", self._on_settings))
        items.append(pystray.MenuItem("Quitter", self._on_quit))
        return pystray.Menu(*items)

    def _background_loop(self):
        last_refresh = 0.0
        while not self.stop_event.is_set():
            now = time.time()
            with self.lock:
                if self.active_timer:
                    # A tick that took much longer than the ~1s wait means the
                    # machine was suspended while the app itself kept running.
                    tick_gap = timer.detect_resume_gap(self._last_tick, now, HEARTBEAT_GAP_WARNING_SECONDS)
                    if tick_gap is not None and not self.resume_gap_seconds:
                        self.resume_gap_seconds = tick_gap
                        log.warning("Detected a %.0fs gap while a timer was active (system suspend?)", tick_gap)

                    elapsed = timer.format_duration(timer.elapsed_seconds(self.active_timer))
                    try:
                        self.icon.title = f"{self.active_timer.task_title} — {elapsed}"
                    except Exception:
                        log.debug("Tooltip update not supported by this tray backend", exc_info=True)
            self._last_tick = now

            if now - last_refresh >= self.cfg["refresh_interval_seconds"]:
                self._refresh_recent_tasks()
                self._refresh_today_total()
                if self.state.get("pending_timelogs"):
                    self._on_retry_pending(self.icon, None)
                self._update_heartbeat()
                self._refresh_icon_and_menu()
                last_refresh = now

            self.stop_event.wait(1)


def run(cfg, token):
    TrayApp(token, cfg).run()


def run_unconfigured():
    def on_quit(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("⚠ Configuration requise — lancer : wrike_timer.py --set-token", None, enabled=False),
        pystray.MenuItem("Quitter", on_quit),
    )
    icon = pystray.Icon("wrike-timer", _make_icon(COLOR_UNCONFIGURED), "Wrike Timer — non configuré", menu)
    icon.run()
