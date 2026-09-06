import json
import pytest

from fb_cookie_bridge.groups import parse_moderation_response

GROUP_ID = "1263207130787754"

def test_parse_approve_success():
    body = json.dumps({
        "data": {
            "group_approve_pending_story": {
                "group": {"id": GROUP_ID}
            }
        }
    })
    res = parse_moderation_response(body, "APPROVE", GROUP_ID)
    assert res["status"] == "ok"
    assert res["confirmed"] is True

def test_parse_decline_success():
    body = json.dumps({
        "data": {
            "group_content_remove": {
                "group": {"id": GROUP_ID}
            }
        }
    })
    res = parse_moderation_response(body, "DECLINE", GROUP_ID)
    assert res["status"] == "ok"
    assert res["confirmed"] is True

def test_parse_graphql_errors():
    body = json.dumps({
        "errors": [{"code": 1675002, "message": "Incorrect Query"}]
    })
    res = parse_moderation_response(body, "APPROVE", GROUP_ID)
    assert res["status"] == "error"
    assert res["error"] == "graphql_error"
    assert "1675002" in res["error_codes"]
