# J2TEAM Cookie setup

This guide uses **J2TEAM Cookies**, a browser extension that exports cookies from the Facebook session you are already signed in to.

Use only a Facebook account you own or are explicitly authorized to operate. A cookie export is equivalent to a logged-in session. Treat it like a password.

## 1. Export Facebook cookies

1. Open Chrome or Edge profile containing your intended Facebook login.
2. Visit `https://www.facebook.com/` and confirm account is signed in.
3. Open the J2TEAM Cookies extension.
4. Export cookies for the current Facebook site as **JSON**.
5. Save locally as `cookies_fb.json`.

Expected shapes accepted by bridge:

```json
[
  {"domain":".facebook.com","path":"/","secure":true,"name":"c_user","value":"..."}
]
```

or:

```json
{"cookies":[{"domain":".facebook.com","path":"/","secure":true,"name":"c_user","value":"..."}]}
```

Do not paste cookie JSON into chat, commits, workflow parameters, screenshots, or issue tickets.

## 2. Start with Docker Compose

Place cookie file beside `compose.yaml`:

```text
fb-cookie-bridge/
├── compose.yaml
└── cookies_fb.json       # local only; ignored by Git
```

Start:

```bash
docker compose up -d --build
docker compose logs -f fb-cookie-bridge
curl http://localhost:8899/healthz
```

`compose.yaml` mounts it read-only:

```yaml
volumes:
  - ./cookies_fb.json:/run/secrets/facebook_cookies.json:ro
```

The bridge reads this path through `FBCB_COOKIE_FILE`; callers never send cookies to HTTP API.

## 3. Docker run alternative

```bash
docker run --rm -p 8899:8899 \
  -v "$PWD/cookies_fb.json:/run/secrets/facebook_cookies.json:ro" \
  -e FBCB_IMPERSONATE=chrome \
  ghcr.io/mrnim94/fb-cookie-bridge:latest
```

For production, prefer Docker/Compose secrets or an equivalent secret manager. Keep service on a private network; do not publish port `8899` to Internet.

## 4. Verify access

```bash
curl -sS -X POST http://localhost:8899/v1/facebook/request \
  -H 'content-type: application/json' \
  -d '{"method":"GET","url":"https://www.facebook.com/","headers":{"accept":"text/html"}}'
```

Expected result contains upstream `status`, a minimal `headers` map, and `body`. A `200` only means Facebook accepted this request; it does not grant any action beyond account permissions.

## Cookie lifecycle

Facebook can invalidate sessions. Re-export and replace `cookies_fb.json` when login/checkpoint responses appear, then restart the container:

```bash
docker compose restart fb-cookie-bridge
```

Never automate login, CAPTCHA, or checkpoint bypass with this project.
