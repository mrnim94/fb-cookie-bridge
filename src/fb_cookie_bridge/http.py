from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Settings
from .cookie_ui import cookie_upload_ui, handle_cookie_upload, handle_cookie_status
from .facebook import FacebookClient, RequestError
from .groups import GroupsService

LOG = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    settings: Settings
    client: FacebookClient
    groups: GroupsService

    def log_message(self, format: str, *args) -> None:
        LOG.info("http %s", format % args)

    def _reply(self, status: int, data: dict | list) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._reply(200, {"status": "ok"})
            return

        if self.path == "/cookie":
            body = cookie_upload_ui()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/v1/cookie/status":
            status_code, data = handle_cookie_status(self.settings.cookie_file)
            self._reply(status_code, data)
            return

        if self.path == "/openapi.yaml":
            spec = Path(__file__).parents[2] / "docs" / "openapi.yaml"
            try:
                body = spec.read_bytes()
            except FileNotFoundError:
                self._reply(404, {"error": "openapi_not_installed"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/yaml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # GET /v1/groups/{group_id}/pending-posts
        m_get = re.match(r"^/v1/groups/([^/?#]+)/pending-posts(?:\?(.*))?$", self.path)
        if m_get:
            group_id = m_get.group(1)
            try:
                posts = self.groups.get_pending_posts(group_id)
                self._reply(200, {"status": "ok", "groupId": group_id, "count": len(posts), "posts": posts})
            except Exception as exc:
                LOG.exception("get_pending_posts_failed")
                self._reply(500, {"error": "fetch_failed", "detail": str(exc)})
            return

        self._reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        # 0. POST /v1/cookie/upload
        if self.path == "/v1/cookie/upload":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                status_code, data = handle_cookie_upload(body, self.settings.cookie_file)
                self._reply(status_code, data)
            except Exception:
                LOG.exception("cookie_upload_failed")
                self._reply(500, {"error": "upload_failed"})
            return

        # 1. POST /v1/facebook/request
        if self.path == "/v1/facebook/request":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise RequestError("body_must_be_object")
                result = self.client.request(
                    payload.get("method", "GET"), payload["url"], payload.get("headers"), payload.get("body")
                )
                self._reply(200, result)
            except (KeyError, RequestError, json.JSONDecodeError) as exc:
                self._reply(400, {"error": str(exc)})
            except Exception:
                LOG.exception("facebook_request_failed")
                self._reply(502, {"error": "upstream_request_failed"})
            return

        # 2. POST /v1/groups/{group_id}/pending-posts/{story_id}:approve or :decline
        m_mod = re.match(r"^/v1/groups/([^/]+)/pending-posts/([^/:]+):(approve|decline)$", self.path)
        if m_mod:
            group_id = m_mod.group(1)
            story_id = m_mod.group(2)
            action = m_mod.group(3).upper()
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length)) if length > 0 else {}
                member_id = body.get("memberId") or body.get("authorId")
                res = self.groups.moderate_post(action, group_id, story_id, member_id)
                self._reply(200, res)
            except (RequestError, json.JSONDecodeError) as exc:
                self._reply(400, {"error": str(exc)})
            except Exception as exc:
                LOG.exception("moderate_post_failed")
                self._reply(500, {"error": "moderate_failed", "detail": str(exc)})
            return

        self._reply(404, {"error": "not_found"})


def serve(settings: Settings) -> None:
    client = FacebookClient(settings.cookie_file, settings.impersonate, settings.timeout_seconds)
    groups = GroupsService(client)
    Handler.settings = settings
    Handler.client = client
    Handler.groups = groups
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    LOG.info("server_started host=%s port=%s impersonate=%s", settings.host, settings.port, settings.impersonate)
    server.serve_forever()
