import time

import pytest

from wrike_timer import tray_app as tray_app_module
from wrike_timer.state_store import StateStore
from wrike_timer.tray_app import TrayApp
from wrike_timer.wrike_api import WrikeApiError

CFG = {
    "recent_tasks_limit": 10,
    "recent_tasks_lookback_days": 30,
    "refresh_interval_seconds": 60,
    "timesheet_url": None,
}


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.posted = []
        self.raise_on_post = False

    def post_timelog(self, task_id, hours, tracked_date, comment=""):
        if self.raise_on_post:
            raise WrikeApiError("boom")
        self.posted.append({"task_id": task_id, "hours": hours, "tracked_date": tracked_date, "comment": comment})


def make_app(tmp_path, monkeypatch, recent_tasks=None, cfg=None):
    monkeypatch.setattr(tray_app_module, "WrikeClient", FakeClient)
    monkeypatch.setattr(tray_app_module.config, "STATE_PATH", tmp_path / "state.json")
    app = TrayApp("token", cfg or CFG)
    app.state["recent_tasks"] = recent_tasks or []
    return app


TASK_A = {"id": "A", "title": "Task A"}
TASK_B = {"id": "B", "title": "Task B"}


def test_switch_to_task_stops_and_submits_current_then_starts_new(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, recent_tasks=[TASK_A, TASK_B])

    app._switch_to_task(TASK_A)
    started_at_a = app.active_timer.started_at

    app._switch_to_task(TASK_B)

    assert len(app.client.posted) == 1
    assert app.client.posted[0]["task_id"] == "A"
    assert app.active_timer.task_id == "B"
    assert app.active_timer.started_at != started_at_a


def test_switch_to_task_same_task_is_noop(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, recent_tasks=[TASK_A])

    app._switch_to_task(TASK_A)
    started_at = app.active_timer.started_at

    app._switch_to_task(TASK_A)

    assert app.client.posted == []
    assert app.active_timer.task_id == "A"
    assert app.active_timer.started_at == started_at


def test_switch_to_task_queues_entry_when_post_fails(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, recent_tasks=[TASK_A, TASK_B])
    app._switch_to_task(TASK_A)
    app.client.raise_on_post = True

    app._switch_to_task(TASK_B)

    assert app.client.posted == []
    assert len(app.state["pending_timelogs"]) == 1
    assert app.state["pending_timelogs"][0]["task_id"] == "A"
    assert app.active_timer.task_id == "B"


def test_build_menu_excludes_active_task_and_enables_others(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, recent_tasks=[TASK_A, TASK_B])
    app._switch_to_task(TASK_A)

    menu_items = list(app._build_menu())
    recent_labels = {item.text for item in menu_items if getattr(item, "text", None) == "Task B"}

    assert "Task B" in recent_labels
    assert not any(getattr(item, "text", None) == "Task A" for item in menu_items)

    b_item = next(item for item in menu_items if getattr(item, "text", None) == "Task B")
    assert b_item.enabled


def test_build_menu_defaults_to_english(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)

    labels = [item.text for item in app._build_menu()]

    assert "Quit" in labels
    assert "Quitter" not in labels


def test_build_menu_respects_language_config(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, cfg={**CFG, "language": "fr"})

    labels = [item.text for item in app._build_menu()]

    assert "Quitter" in labels
    assert "Quit" not in labels


def _long_entry(**overrides):
    return {"task_id": "A", "hours": 70.0, "tracked_date": "2026-10-23", "comment": "", "started_at": 1_000_000.0, **overrides}


def test_stop_over_threshold_queues_without_posting(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, recent_tasks=[TASK_A])
    app._switch_to_task(TASK_A)
    app.active_timer.started_at -= 13 * 3600

    app._on_stop(None, None)

    assert app.client.posted == []
    assert len(app.state["pending_timelogs"]) == 1
    assert app.state["pending_timelogs"][0]["started_at"] == pytest.approx(time.time() - 13 * 3600, abs=5)


def test_retry_skips_entries_over_threshold(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    long_entry = _long_entry()
    app.state["pending_timelogs"] = [long_entry, _long_entry(hours=1.0)]

    app._on_retry_pending(None, None)

    assert [p["hours"] for p in app.client.posted] == [1.0]
    assert app.state["pending_timelogs"] == [long_entry]


def test_send_anyway_posts_and_removes_entry(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    entry = _long_entry()
    app.state["pending_timelogs"] = [entry]

    app._make_send_anyway_handler(entry)(None, None)

    assert len(app.client.posted) == 1
    assert app.state["pending_timelogs"] == []


def test_send_anyway_keeps_entry_when_post_fails(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    entry = _long_entry()
    app.state["pending_timelogs"] = [entry]
    app.client.raise_on_post = True

    app._make_send_anyway_handler(entry)(None, None)

    assert app.state["pending_timelogs"] == [entry]


def test_discard_removes_entry_without_posting(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    entry = _long_entry()
    app.state["pending_timelogs"] = [entry]

    app._make_discard_handler(entry)(None, None)

    assert app.client.posted == []
    assert app.state["pending_timelogs"] == []


def test_build_menu_shows_confirmation_entries_with_and_without_start(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    app.state["pending_timelogs"] = [_long_entry(), _long_entry(started_at=None, hours=30.0)]

    labels = [item.text for item in app._build_menu()]

    assert any(label.startswith("⚠ 70h00 — started ") for label in labels)
    assert "⚠ 30h00 — on 2026-10-23" in labels
    assert not any("pending submission" in label for label in labels)
