"""Facebook-only request boundary and curl_cffi transport."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from curl_cffi import requests

LOG = logging.getLogger(__name__)
ALLOWED_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "graph.facebook.com"}
ALLOWED_METHODS = {"GET", "POST", "HEAD"}


class RequestError(ValueError):
    """Request rejected before transport."""


def validate_target(method: str, url: str) -> None:
    parsed = urlparse(url)
    if method.upper() not in ALLOWED_METHODS:
        raise RequestError("method_not_allowed")
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise RequestError("url_not_allowed")


def load_cookies(cookie_file: Path) -> list[dict[str, object]]:
    try:
        raw = json.loads(cookie_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RequestError("cookie_file_missing") from exc
    except json.JSONDecodeError as exc:
        raise RequestError("cookie_file_invalid_json") from exc
    cookies = raw.get("cookies", raw) if isinstance(raw, dict) else raw
    if not isinstance(cookies, list):
        raise RequestError("cookie_file_invalid_format")
    return [c for c in cookies if isinstance(c, dict) and c.get("name") and "value" in c]


class FacebookClient:
    def __init__(self, cookie_file: Path, impersonate: str = "chrome", timeout_seconds: int = 30):
        self.cookie_file = cookie_file
        self.impersonate = impersonate
        self.timeout_seconds = timeout_seconds

    def _session(self):
        session = requests.Session(impersonate=self.impersonate)
        for cookie in load_cookies(self.cookie_file):
            domain = str(cookie.get("domain", ".facebook.com"))
            session.cookies.set(str(cookie["name"]), str(cookie["value"]), domain=domain, path=str(cookie.get("path", "/")))
        return session

    def request(self, method: str, url: str, headers: dict[str, str] | None = None, body: str | None = None) -> dict[str, object]:
        method = method.upper()
        validate_target(method, url)
        safe_headers = {str(k): str(v) for k, v in (headers or {}).items() if str(k).lower() not in {"cookie", "host", "content-length"}}
        LOG.info("facebook_request method=%s host=%s", method, urlparse(url).hostname)
        with self._session() as session:
            response = session.request(method, url, headers=safe_headers, data=body, timeout=self.timeout_seconds)
        LOG.info("facebook_response method=%s status=%s", method, response.status_code)
        return {"status": response.status_code, "headers": {"content-type": response.headers.get("content-type", "")}, "body": response.text}
