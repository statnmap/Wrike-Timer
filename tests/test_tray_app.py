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


def make_app(tmp_path, monkeypatch, recent_tasks=None):
    monkeypatch.setattr(tray_app_module, "WrikeClient", FakeClient)
    monkeypatch.setattr(tray_app_module.config, "STATE_PATH", tmp_path / "state.json")
    app = TrayApp("token", CFG)
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
