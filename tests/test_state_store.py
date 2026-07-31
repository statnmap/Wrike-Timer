from wrike_timer.state_store import DEFAULT_STATE, StateStore


def test_load_returns_defaults_when_file_missing(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.load() == DEFAULT_STATE


def test_save_then_load_roundtrip(tmp_path):
    store = StateStore(tmp_path / "state.json")
    data = {
        "recent_tasks": [{"id": "A", "title": "Fix bug"}],
        "active_timer": {"task_id": "A", "task_title": "Fix bug", "started_at": 1000.0},
        "pending_timelogs": [],
    }
    store.save(data)
    assert store.load() == data


def test_save_is_atomic_no_leftover_tmp_file(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save({"recent_tasks": [], "active_timer": None, "pending_timelogs": []})
    assert path.exists()
    assert not path.with_suffix(".tmp").exists()


def test_load_recovers_from_corrupted_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = StateStore(path)
    assert store.load() == DEFAULT_STATE


def test_add_and_remove_pending_timelog(tmp_path):
    store = StateStore(tmp_path / "state.json")
    entry = {"task_id": "A", "hours": 1.0, "tracked_date": "2026-07-31", "comment": ""}

    store.add_pending_timelog(entry)
    assert store.load()["pending_timelogs"] == [entry]

    store.remove_pending_timelog(entry)
    assert store.load()["pending_timelogs"] == []


def test_load_merges_missing_keys_with_defaults(tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"recent_tasks": [{"id": "A", "title": "Fix bug"}]}', encoding="utf-8")
    store = StateStore(path)
    data = store.load()
    assert data["recent_tasks"] == [{"id": "A", "title": "Fix bug"}]
    assert data["active_timer"] is None
    assert data["pending_timelogs"] == []
