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


def test_format_hours():
    assert timer.format_hours(0) == "0h00"
    assert timer.format_hours(3.75) == "3h45"
    assert timer.format_hours(0.5) == "0h30"


def test_format_hours_rounds_to_nearest_minute():
    assert timer.format_hours(1.001) == "1h00"
    assert timer.format_hours(1.99999) == "2h00"


def test_gap_seconds():
    assert timer.gap_seconds(1000.0, 1090.0) == 90.0


def test_gap_seconds_never_negative():
    assert timer.gap_seconds(1000.0, 500.0) == 0


def test_detect_resume_gap_none_when_no_heartbeat_ever_recorded():
    # First run after upgrading from a state.json written before heartbeats existed.
    assert timer.detect_resume_gap(None, 1000.0, threshold_seconds=300) is None


def test_detect_resume_gap_none_when_heartbeat_is_recent():
    assert timer.detect_resume_gap(1000.0, 1010.0, threshold_seconds=300) is None


def test_detect_resume_gap_returns_gap_when_stale():
    assert timer.detect_resume_gap(1000.0, 1000.0 + 301, threshold_seconds=300) == 301


def test_detect_resume_gap_boundary_is_exclusive():
    assert timer.detect_resume_gap(1000.0, 1300.0, threshold_seconds=300) is None


def test_task_label_marks_completed_tasks():
    assert timer.task_label("Fix bug", "Completed") == "❌ Fix bug"


def test_task_label_leaves_other_statuses_untouched():
    assert timer.task_label("Fix bug", "Active") == "Fix bug"
    assert timer.task_label("Fix bug", None) == "Fix bug"
