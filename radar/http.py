"""Bounded HTTP reads with retries for transient transport failures only."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


def fetch_bytes(
    request: urllib.request.Request, *, timeout: int = 30, attempts: int = 3, max_bytes: int = 8 * 1024 * 1024
) -> bytes:
    if attempts < 1 or timeout <= 0 or max_bytes < 1:
        raise ValueError("HTTP limits must be positive")
    for attempt in range(attempts):
        delay = min(2**attempt, 8)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError("HTTP response is too large")
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
            if retry_after.isdigit():
                delay = min(int(retry_after), 30)
            exc.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == attempts - 1:
                raise
        time.sleep(delay)
    raise RuntimeError("HTTP retry budget exhausted")


def fetch_json(request: urllib.request.Request, **kwargs):
    return json.loads(fetch_bytes(request, **kwargs))
