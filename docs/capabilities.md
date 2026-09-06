# Capability matrix

| Capability | Status | Public API |
|---|---:|---|
| Facebook HTTPS request with mounted cookie JSON | Ready | `POST /v1/facebook/request` |
| Browser-like transport via `curl_cffi` | Ready | `FBCB_IMPERSONATE` |
| Strict host/method boundary | Ready | Facebook hosts; `GET`, `POST`, `HEAD` |
| Health endpoint | Ready | `GET /healthz` |
| Cookie upload through API | Intentionally unsupported | Mount read-only file instead |
| Arbitrary proxying | Intentionally unsupported | N/A |
| Group pending-post collection | Not part of v0.1 | External workflow/module |
| Post approve/decline actions | Not part of v0.1 | External workflow/module |

The old private `server.py` proof-of-concept included group-specific operations. This public project deliberately starts smaller: reusable authenticated transport first, business operations later as separately reviewed modules.
