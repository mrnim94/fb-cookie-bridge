import json
from pathlib import Path

import pytest

from fb_cookie_bridge.facebook import RequestError, load_cookies, validate_target


def test_load_cookie_array(tmp_path: Path):
    path = tmp_path / "cookies.json"
    path.write_text(json.dumps([{"name": "c_user", "value": "123", "domain": ".facebook.com"}]))
    assert load_cookies(path) == [{"name": "c_user", "value": "123", "domain": ".facebook.com"}]


def test_load_cookie_wrapped_object(tmp_path: Path):
    path = tmp_path / "cookies.json"
    path.write_text(json.dumps({"cookies": [{"name": "xs", "value": "abc"}]}))
    assert load_cookies(path)[0]["name"] == "xs"


@pytest.mark.parametrize("method,url", [
    ("GET", "https://www.facebook.com/groups/123"),
    ("POST", "https://graph.facebook.com/graphql"),
])
def test_accepts_allowed_facebook_targets(method: str, url: str):
    validate_target(method, url)


@pytest.mark.parametrize("method,url,error", [
    ("DELETE", "https://www.facebook.com/", "method_not_allowed"),
    ("GET", "http://www.facebook.com/", "url_not_allowed"),
    ("GET", "https://facebook.com.evil.test/", "url_not_allowed"),
])
def test_rejects_unsafe_target(method: str, url: str, error: str):
    with pytest.raises(RequestError, match=error):
        validate_target(method, url)


def test_openapi_contract_is_present():
    spec = Path(__file__).parents[1] / "docs" / "openapi.yaml"
    text = spec.read_text()
    assert "openapi: 3.1.0" in text
    assert "/v1/facebook/request:" in text
