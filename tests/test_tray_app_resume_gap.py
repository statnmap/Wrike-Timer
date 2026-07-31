from wrike_timer import config, tray_app


def make_app(tmp_path, monkeypatch, state):
    monkeypatch.setattr(config, "STATE_PATH", tmp_path / "state.json")
    from wrike_timer.state_store import StateStore

    StateStore(tmp_path / "state.json").save(state)
    return tray_app.TrayApp("fake-token", {"refresh_interval_seconds": 30, "recent_tasks_limit": 10})


def active_timer_state(started_at=1000.0):
    return {"task_id": "A", "task_title": "Fix bug", "started_at": started_at}


def test_no_warning_when_no_active_timer(tmp_path, monkeypatch):
    app = make_app(
        tmp_path, monkeypatch, {"recent_tasks": [], "active_timer": None, "pending_timelogs": [], "last_heartbeat": 1.0}
    )
    assert app.resume_gap_seconds is None


def test_no_warning_when_heartbeat_is_recent(tmp_path, monkeypatch):
    monkeypatch.setattr(tray_app.time, "time", lambda: 1010.0)
    app = make_app(
        tmp_path,
        monkeypatch,
        {"recent_tasks": [], "active_timer": active_timer_state(), "pending_timelogs": [], "last_heartbeat": 1000.0},
    )
    assert app.resume_gap_seconds is None


def test_warns_when_heartbeat_is_stale(tmp_path, monkeypatch):
    stale_gap = tray_app.HEARTBEAT_GAP_WARNING_SECONDS + 60
    monkeypatch.setattr(tray_app.time, "time", lambda: 1000.0 + stale_gap)
    app = make_app(
        tmp_path,
        monkeypatch,
        {"recent_tasks": [], "active_timer": active_timer_state(), "pending_timelogs": [], "last_heartbeat": 1000.0},
    )
    assert app.resume_gap_seconds == stale_gap


def test_no_warning_when_no_heartbeat_ever_recorded(tmp_path, monkeypatch):
    # First run after upgrading from a state.json written before this feature existed.
    app = make_app(tmp_path, monkeypatch, {"recent_tasks": [], "active_timer": active_timer_state(), "pending_timelogs": []})
    assert app.resume_gap_seconds is None


def test_stopping_the_timer_clears_the_warning(tmp_path, monkeypatch):
    stale_gap = tray_app.HEARTBEAT_GAP_WARNING_SECONDS + 60
    monkeypatch.setattr(tray_app.time, "time", lambda: 1000.0 + stale_gap)
    app = make_app(
        tmp_path,
        monkeypatch,
        {"recent_tasks": [], "active_timer": active_timer_state(), "pending_timelogs": [], "last_heartbeat": 1000.0},
    )
    assert app.resume_gap_seconds == stale_gap

    monkeypatch.setattr(app.client, "post_timelog", lambda *args, **kwargs: None)
    app._on_stop(app.icon, None)

    assert app.resume_gap_seconds is None
