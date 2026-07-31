from datetime import date

from wrike_timer import timer


def test_start_captures_task_and_time():
    state = timer.start("123", "Fix bug XYZ", now=1000.0)
    assert state.task_id == "123"
    assert state.task_title == "Fix bug XYZ"
    assert state.started_at == 1000.0


def test_stop_computes_duration_in_seconds():
    state = timer.start("123", "Fix bug XYZ", now=1000.0)
    duration_seconds, _ = timer.stop(state, now=1000.0 + 90)
    assert duration_seconds == 90


def test_stop_never_returns_negative_duration():
    state = timer.start("123", "Fix bug XYZ", now=1000.0)
    duration_seconds, _ = timer.stop(state, now=500.0)
    assert duration_seconds == 0


def test_stop_tracked_date_uses_start_date_even_across_midnight():
    # Started 2026-01-01 23:59:00 UTC-ish local, stopped after midnight.
    started_at = 1735775940.0  # 2025-01-01T23:59:00Z
    ended_at = started_at + 120  # crosses into 2025-01-02
    state = timer.start("123", "Ticket", now=started_at)
    _, tracked_date = timer.stop(state, now=ended_at)

    assert tracked_date == date.fromtimestamp(started_at).isoformat()


def test_elapsed_seconds_reflects_time_passed():
    state = timer.start("123", "Ticket", now=1000.0)
    assert timer.elapsed_seconds(state, now=1042.0) == 42.0


def test_format_duration():
    assert timer.format_duration(0) == "00:00:00"
    assert timer.format_duration(65) == "00:01:05"
    assert timer.format_duration(3661) == "01:01:01"


def test_seconds_to_hours():
    assert timer.seconds_to_hours(3600) == 1.0
    assert timer.seconds_to_hours(1800) == 0.5


def test_timer_state_roundtrip_through_dict():
    state = timer.start("123", "Ticket", now=1000.0)
    restored = timer.TimerState.from_dict(state.to_dict())
    assert restored == state
