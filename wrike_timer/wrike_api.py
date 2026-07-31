"""Thin client for the parts of the Wrike API v4 this app needs."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://www.wrike.com/api/v4"
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 1.5

log = logging.getLogger(__name__)


class WrikeApiError(Exception):
    pass


class WrikeClient:
    def __init__(self, token, session=None):
        self._session = session or requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method, path, **kwargs):
        url = f"{BASE_URL}{path}"
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._session.request(method, url, timeout=15, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                log.warning("Network error calling %s %s (attempt %d/%d): %s", method, path, attempt + 1, MAX_RETRIES, exc)
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
                continue

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = float(response.headers.get("Retry-After", BACKOFF_BASE_SECONDS * (2**attempt)))
                last_error = WrikeApiError(f"{method} {path} -> HTTP {response.status_code}")
                log.warning("Wrike API returned %d for %s %s, retrying in %.1fs", response.status_code, method, path, retry_after)
                time.sleep(retry_after)
                continue

            if not response.ok:
                raise WrikeApiError(f"{method} {path} -> HTTP {response.status_code}: {response.text[:500]}")

            return response.json()

        raise WrikeApiError(f"{method} {path} failed after {MAX_RETRIES} attempts") from last_error

    def get_my_contact_id(self):
        data = self._request("GET", "/contacts", params={"me": "true"})
        return data["data"][0]["id"]

    def get_recent_task_ids(self, limit=10, lookback_days=30):
        # /timelogs doesn't support sortField/sortOrder (HTTP 400 if passed), and
        # omitting pageSize returns the user's *entire* timelog history in one
        # response. Bound the request with a createdDate window instead, and sort
        # client-side since the API gives no ordering guarantee.
        start = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = self._request(
            "GET",
            "/timelogs",
            params={"me": "true", "pageSize": 1000, "createdDate": json.dumps({"start": start})},
        )
        entries = sorted(data["data"], key=lambda entry: entry["createdDate"], reverse=True)
        task_ids = []
        for entry in entries:
            task_id = entry.get("taskId")
            if task_id and task_id not in task_ids:
                task_ids.append(task_id)
            if len(task_ids) >= limit:
                break
        return task_ids

    def get_tasks(self, task_ids):
        if not task_ids:
            return []
        data = self._request("GET", f"/tasks/{','.join(task_ids)}")
        return [{"id": task["id"], "title": task["title"]} for task in data["data"]]

    def post_timelog(self, task_id, hours, tracked_date, comment=""):
        self._request(
            "POST",
            f"/timelogs/task/{task_id}",
            data={"hours": hours, "trackedDate": tracked_date, "comment": comment},
        )
