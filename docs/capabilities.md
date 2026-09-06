# Capability matrix

| Capability | Status | Public API Endpoint |
|---|:---:|---|
| Health check | Ready | `GET /healthz` |
| List all pending posts in group (with pagination) | Ready | `GET /v1/groups/{group_id}/pending-posts` |
| Approve pending post into group feed | Ready | `POST /v1/groups/{group_id}/pending-posts/{story_id}:approve` |
| Decline & remove pending post | Ready | `POST /v1/groups/{group_id}/pending-posts/{story_id}:decline` |
| Generic raw Facebook HTTPS request | Ready | `POST /v1/facebook/request` |
| Browser impersonation transport | Ready | `FBCB_IMPERSONATE=chrome` (via `curl_cffi`) |
| J2TEAM cookie file mount | Ready | Read-only JSON volume (`FBCB_COOKIE_FILE`) |
