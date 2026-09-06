# fb-cookie-bridge

Small HTTP bridge for Facebook requests authenticated by operator-owned cookie exports. Built on [`curl_cffi`](https://github.com/lexiforest/curl_cffi) browser impersonation.

> Use only with Facebook accounts and groups you own or administer. Cookies are credentials: never commit them, send them through request payloads, or expose this service publicly.

## Why

Workflow engines such as n8n need a narrow, repeatable interface. This service owns only transport concerns:

- Loads a read-only Facebook cookie export from disk.
- Uses `curl_cffi` browser impersonation for HTTPS requests.
- Enforces HTTPS, Facebook host allowlist, and `GET`/`POST`/`HEAD` only.
- Emits structured logs without cookie values or request bodies.

Business workflows, GraphQL queries, and moderation policies stay outside this repository.

## Quick start

```bash
cp examples/cookies.example.json cookies_fb.json
# Replace placeholders with a cookie export from an account you operate.
docker compose up --build
```

Health check:

```bash
curl http://localhost:8899/healthz
```

Request bridge:

```bash
curl -X POST http://localhost:8899/v1/facebook/request \
  -H 'content-type: application/json' \
  -d '{
    "method":"GET",
    "url":"https://www.facebook.com/",
    "headers":{"accept":"text/html"}
  }'
```

## API

### `GET /healthz`

Returns `{"status":"ok"}`.

### `POST /v1/facebook/request`

```json
{
  "method": "GET | POST | HEAD",
  "url": "https://www.facebook.com/...",
  "headers": {"accept": "application/json"},
  "body": "optional raw request body"
}
```

Allowed hosts: `facebook.com`, `www.facebook.com`, `m.facebook.com`, `graph.facebook.com`. The bridge rejects cookies supplied by callers, non-HTTPS URLs, redirects outside caller control, and unsafe HTTP methods.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `FBCB_COOKIE_FILE` | `/run/secrets/facebook_cookies.json` | Cookie JSON path |
| `FBCB_HOST` | `0.0.0.0` | Bind address |
| `FBCB_PORT` | `8899` | Listen port |
| `FBCB_IMPERSONATE` | `chrome` | `curl_cffi` browser profile |
| `FBCB_TIMEOUT_SECONDS` | `30` | Upstream timeout |

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```

## Layout

```text
src/fb_cookie_bridge/  # config, transport boundary, HTTP server
examples/              # credential-free example only
tests/                 # trust-boundary unit tests
.github/workflows/     # test and image-build CI
```

## Security model

Run on a private network. Mount cookie files read-only. Keep a network policy in front of this bridge. The API deliberately does not implement arbitrary proxying, credential ingestion, browser automation, or Facebook business actions.

## License

MIT.
