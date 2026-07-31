"""Pure timer logic: no I/O, no network, easy to unit test."""

import time
from dataclasses import asdict, dataclass
from datetime import date


@dataclass
class TimerState:
    task_id: str
    task_title: str
    started_at: float  # epoch seconds

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(task_id=data["task_id"], task_title=data["task_title"], started_at=data["started_at"])


def start(task_id, task_title, now=None):
    return TimerState(task_id=task_id, task_title=task_title, started_at=now if now is not None else time.time())


def stop(state, now=None):
    """Return (duration_seconds, tracked_date_iso) for the given timer state.

    tracked_date is the local calendar date the timer *started* on, so a
    timer that happens to run past midnight is still logged against the day
    the work began.
    """
    end = now if now is not None else time.time()
    duration_seconds = max(0.0, end - state.started_at)
    tracked_date = date.fromtimestamp(state.started_at).isoformat()
    return duration_seconds, tracked_date


def elapsed_seconds(state, now=None):
    end = now if now is not None else time.time()
    return max(0.0, end - state.started_at)


def gap_seconds(previous_timestamp, current_timestamp):
    return max(0.0, current_timestamp - previous_timestamp)


def format_duration(seconds):
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def seconds_to_hours(seconds):
    return seconds / 3600


def format_hours(total_hours):
    total_minutes = round(total_hours * 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h{minutes:02d}"
