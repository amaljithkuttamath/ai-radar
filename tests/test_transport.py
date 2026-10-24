import io
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest


def test_transient_http_failure_is_retried(monkeypatch):
    from radar import http

    responses = iter([HTTPError("https://example.org", 503, "unavailable", {}, None), io.BytesIO(b"ok")])

    def open_request(request, timeout):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(http.urllib.request, "urlopen", open_request)
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    assert http.fetch_bytes(Request("https://example.org")) == b"ok"


def test_permanent_http_error_is_not_retried(monkeypatch):
    from radar import http

    calls = []

    def unavailable(*args, **kwargs):
        calls.append(1)
        raise HTTPError("https://example.org", 404, "missing", {}, None)

    monkeypatch.setattr(http.urllib.request, "urlopen", unavailable)
    with pytest.raises(HTTPError):
        http.fetch_bytes(Request("https://example.org"))
    assert len(calls) == 1


def test_network_failure_has_bounded_retries(monkeypatch):
    from radar import http

    calls = []

    def unavailable(*args, **kwargs):
        calls.append(1)
        raise URLError("offline")

    monkeypatch.setattr(http.urllib.request, "urlopen", unavailable)
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    with pytest.raises(URLError):
        http.fetch_bytes(Request("https://example.org"), attempts=3)
    assert len(calls) == 3


def test_large_response_is_rejected(monkeypatch):
    from radar import http

    monkeypatch.setattr(http.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"123456"))
    with pytest.raises(ValueError, match="large"):
        http.fetch_bytes(Request("https://example.org"), max_bytes=5)
