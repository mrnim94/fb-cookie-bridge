"""Tests for cookie upload and status endpoints."""
import json
import tempfile
from pathlib import Path

from fb_cookie_bridge.cookie_ui import (
    cookie_upload_ui,
    handle_cookie_upload,
    handle_cookie_status,
)


def test_upload_ui_returns_html():
    body = cookie_upload_ui()
    assert b"<!DOCTYPE html>" in body
    assert b"Upload" in body


def test_upload_valid_j2team_cookies(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookies = [{"name": "c_user", "value": "123", "domain": ".facebook.com"}]
    status, data = handle_cookie_upload(json.dumps(cookies).encode(), cookie_file)
    assert status == 200
    assert data["cookie_count"] == 1
    assert cookie_file.exists()
    saved = json.loads(cookie_file.read_text())
    assert saved[0]["name"] == "c_user"


def test_upload_wrapped_format(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    wrapped = {"cookies": [{"name": "xs", "value": "abc"}, {"name": "fr", "value": "def"}]}
    status, data = handle_cookie_upload(json.dumps(wrapped).encode(), cookie_file)
    assert status == 200
    assert data["cookie_count"] == 2


def test_upload_rejects_invalid_json(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    status, data = handle_cookie_upload(b"not json{{{", cookie_file)
    assert status == 400
    assert "invalid_json" in data["error"]


def test_upload_rejects_empty_list(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    status, data = handle_cookie_upload(json.dumps([]).encode(), cookie_file)
    assert status == 400
    assert "empty" in data["error"]


def test_upload_rejects_no_valid_cookies(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    status, data = handle_cookie_upload(json.dumps([{"bad": "data"}]).encode(), cookie_file)
    assert status == 400
    assert "no_valid" in data["error"]


def test_upload_overwrites_existing(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text('[{"name":"old","value":"1"}]')
    new = [{"name": "new", "value": "2"}]
    status, data = handle_cookie_upload(json.dumps(new).encode(), cookie_file)
    assert status == 200
    saved = json.loads(cookie_file.read_text())
    assert saved[0]["name"] == "new"


def test_status_missing_file(tmp_path):
    cookie_file = tmp_path / "nope.json"
    status, data = handle_cookie_status(cookie_file)
    assert status == 200
    assert data["valid"] is False


def test_status_valid_file(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text('[{"name":"c_user","value":"123"}]')
    status, data = handle_cookie_status(cookie_file)
    assert status == 200
    assert data["valid"] is True
    assert data["cookie_count"] == 1


def test_status_corrupt_file(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text("not json")
    status, data = handle_cookie_status(cookie_file)
    assert status == 200
    assert data["valid"] is False
