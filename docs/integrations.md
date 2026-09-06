# Integration guide

## What `POST /v1/facebook/request` does

It is a **narrow authenticated transport endpoint**:

1. Receives one Facebook HTTPS request from your internal app.
2. Loads Facebook session cookie from a server-side read-only mounted file.
3. Sends request through `curl_cffi` browser impersonation.
4. Returns sanitized upstream status, content type, and body.

It is not an arbitrary web proxy, cookie upload endpoint, Facebook SDK, or business-action API. It only allows Facebook hosts and `GET`, `POST`, `HEAD`.

## cURL client

```bash
curl -sS -X POST http://fb-cookie-bridge:8899/v1/facebook/request \
  -H 'content-type: application/json' \
  -d '{
    "method":"GET",
    "url":"https://www.facebook.com/",
    "headers":{"accept":"text/html"}
  }'
```

## n8n

Add an **HTTP Request** node:

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://fb-cookie-bridge:8899/v1/facebook/request` |
| Send Body | enabled |
| Body Content Type | JSON |
| JSON Body | expression below |

```javascript
={{ {
  method: 'GET',
  url: 'https://www.facebook.com/',
  headers: { accept: 'text/html' }
} }}
```

In Docker Compose, put n8n and bridge on same private Docker network and use service name `fb-cookie-bridge`. Do not put cookie values in n8n credentials, node parameters, execution data, or logs.

## Custom application

```python
import requests

response = requests.post(
    "http://fb-cookie-bridge:8899/v1/facebook/request",
    json={
        "method": "GET",
        "url": "https://www.facebook.com/",
        "headers": {"accept": "text/html"},
    },
    timeout=35,
)
response.raise_for_status()
facebook_response = response.json()
```

## API discovery

- Live contract: `GET /openapi.yaml`
- Repository contract: [`openapi.yaml`](openapi.yaml)
- Import either into Swagger UI, Scalar, Redoc, Postman, or Insomnia.

## Recommended deployment boundary

```text
n8n / internal app
        │ private Docker network
        ▼
fb-cookie-bridge ─── read-only cookie mount
        │ HTTPS
        ▼
Facebook
```

Do not expose bridge directly through public ingress. Add application authentication and network policy before sharing it across teams.
