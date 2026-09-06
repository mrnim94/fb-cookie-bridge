from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Settings
from .facebook import FacebookClient, RequestError

LOG = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    settings: Settings

    def log_message(self, format: str, *args) -> None:
        LOG.info("http %s", format % args)

    def _reply(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/facebook/request":
            self._reply(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise RequestError("body_must_be_object")
            result = FacebookClient(self.settings.cookie_file, self.settings.impersonate, self.settings.timeout_seconds).request(
                payload.get("method", "GET"), payload["url"], payload.get("headers"), payload.get("body")
            )
            self._reply(200, result)
        except (KeyError, RequestError, json.JSONDecodeError) as exc:
            self._reply(400, {"error": str(exc)})
        except Exception:
            LOG.exception("facebook_request_failed")
            self._reply(502, {"error": "upstream_request_failed"})


def serve(settings: Settings) -> None:
    Handler.settings = settings
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    LOG.info("server_started host=%s port=%s impersonate=%s", settings.host, settings.port, settings.impersonate)
    server.serve_forever()
