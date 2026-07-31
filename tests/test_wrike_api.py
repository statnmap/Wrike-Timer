import pytest
import requests

from wrike_timer import wrike_api


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self.text = text

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self._responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_client(responses):
    session = FakeSession(responses)
    client = wrike_api.WrikeClient("fake-token", session=session)
    return client, session


def test_get_my_contact_id_returns_first_contact_id():
    client, _ = make_client([FakeResponse(json_data={"data": [{"id": "KUAXXXX"}]})])
    assert client.get_my_contact_id() == "KUAXXXX"


def test_get_recent_task_ids_sorts_by_created_date_desc_dedupes_and_respects_limit():
    # Deliberately out of order: the API gives no ordering guarantee.
    timelogs = {
        "data": [
            {"taskId": "B", "createdDate": "2026-07-20T10:00:00Z"},
            {"taskId": "A", "createdDate": "2026-07-31T10:00:00Z"},
            {"taskId": "A", "createdDate": "2026-07-25T10:00:00Z"},  # older dupe of A, ignored
            {"taskId": "C", "createdDate": "2026-07-10T10:00:00Z"},
        ]
    }
    client, _ = make_client([FakeResponse(json_data=timelogs)])
    assert client.get_recent_task_ids(limit=2) == ["A", "B"]


def test_get_recent_task_ids_skips_entries_without_task_id():
    timelogs = {
        "data": [
            {"taskId": None, "createdDate": "2026-07-31T10:00:00Z"},
            {"taskId": "A", "createdDate": "2026-07-30T10:00:00Z"},
        ]
    }
    client, _ = make_client([FakeResponse(json_data=timelogs)])
    assert client.get_recent_task_ids(limit=10) == ["A"]


def test_get_recent_task_ids_does_not_send_unsupported_sort_params():
    timelogs = {"data": [{"taskId": "A", "createdDate": "2026-07-31T10:00:00Z"}]}
    client, session = make_client([FakeResponse(json_data=timelogs)])
    client.get_recent_task_ids(limit=10, lookback_days=30)
    _, _, kwargs = session.calls[0]
    assert "sortField" not in kwargs["params"]
    assert "sortOrder" not in kwargs["params"]
    assert kwargs["params"]["pageSize"] == 1000
    assert "createdDate" in kwargs["params"]


def test_get_tasks_returns_id_and_title():
    client, _ = make_client(
        [FakeResponse(json_data={"data": [{"id": "A", "title": "Fix bug"}, {"id": "B", "title": "Write docs"}]})]
    )
    assert client.get_tasks(["A", "B"]) == [
        {"id": "A", "title": "Fix bug"},
        {"id": "B", "title": "Write docs"},
    ]


def test_get_tasks_with_empty_list_skips_request():
    client, session = make_client([])
    assert client.get_tasks([]) == []
    assert session.calls == []


def test_post_timelog_sends_expected_payload():
    client, session = make_client([FakeResponse(json_data={"data": [{}]})])
    client.post_timelog("A", 1.5, "2026-07-31", "worked on it")
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url.endswith("/timelogs/task/A")
    assert kwargs["data"] == {"hours": 1.5, "trackedDate": "2026-07-31", "comment": "worked on it"}


def test_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(wrike_api.time, "sleep", lambda _seconds: None)
    client, _ = make_client(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "0"}),
            FakeResponse(json_data={"data": [{"id": "KUAXXXX"}]}),
        ]
    )
    assert client.get_my_contact_id() == "KUAXXXX"


def test_retries_on_network_error_then_succeeds(monkeypatch):
    monkeypatch.setattr(wrike_api.time, "sleep", lambda _seconds: None)
    client, _ = make_client(
        [
            requests.ConnectionError("boom"),
            FakeResponse(json_data={"data": [{"id": "KUAXXXX"}]}),
        ]
    )
    assert client.get_my_contact_id() == "KUAXXXX"


def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(wrike_api.time, "sleep", lambda _seconds: None)
    responses = [FakeResponse(status_code=500) for _ in range(wrike_api.MAX_RETRIES)]
    client, _ = make_client(responses)
    with pytest.raises(wrike_api.WrikeApiError):
        client.get_my_contact_id()


def test_non_retryable_error_raises_immediately():
    client, session = make_client([FakeResponse(status_code=404, text="not found")])
    with pytest.raises(wrike_api.WrikeApiError):
        client.get_my_contact_id()
    assert len(session.calls) == 1
