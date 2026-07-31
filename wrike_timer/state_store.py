"""Local persistence: recent tasks cache, active timer, retry queue.

Writes are atomic (write to a temp file, then os.replace) so a crash or power
loss mid-write can't corrupt state.json and lose an in-progress or
not-yet-uploaded timer entry.
"""

import copy
import json
import logging
import os

log = logging.getLogger(__name__)

DEFAULT_STATE = {
    "recent_tasks": [],  # [{"id": ..., "title": ...}, ...]
    "active_timer": None,  # {"task_id", "task_title", "started_at"} or None
    "pending_timelogs": [],  # [{"task_id", "hours", "tracked_date", "comment"}, ...]
}


class StateStore:
    def __init__(self, path):
        self.path = path

    def load(self):
        if not self.path.exists():
            return copy.deepcopy(DEFAULT_STATE)
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            log.exception("Could not read %s, starting from a clean state", self.path)
            return copy.deepcopy(DEFAULT_STATE)
        merged = copy.deepcopy(DEFAULT_STATE)
        merged.update(data)
        return merged

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.path)

    def add_pending_timelog(self, entry):
        data = self.load()
        data["pending_timelogs"].append(entry)
        self.save(data)

    def remove_pending_timelog(self, entry):
        data = self.load()
        data["pending_timelogs"] = [e for e in data["pending_timelogs"] if e != entry]
        self.save(data)
