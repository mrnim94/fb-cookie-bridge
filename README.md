# fb-cookie-bridge

HTTP bridge for Facebook Group moderation and automation workflows. Authenticated using operator-mounted [J2TEAM Cookies](docs/j2team-cookie-setup.md) with [`curl_cffi`](https://github.com/lexiforest/curl_cffi) browser impersonation.

Live Documentation & Interactive API Showcase:
👉 **[https://mrnim94.github.io/fb-cookie-bridge/](https://mrnim94.github.io/fb-cookie-bridge/)**

---

## Features

- **Facebook Group Moderation REST APIs**:
  - `GET /v1/groups/{group_id}/pending-posts`: Crawls and paginates through pending posts using Comet GraphQL.
  - `POST /v1/groups/{group_id}/pending-posts/{story_id}:approve`: Approves story to the group feed.
  - `POST /v1/groups/{group_id}/pending-posts/{story_id}:decline`: Rejects and removes spam story.
- **Low-level Bridge**:
  - `POST /v1/facebook/request`: Secure transport for arbitrary Facebook HTTPS requests with auto-attached session.
- **Zero Headless Overhead**: Ultra lightweight C/Python runtime using `curl_cffi` (~20MB RAM vs 1GB+ with Chrome/Playwright).
- **Security First**: Cookies are mounted read-only from the host; credentials are never passed over the wire.

## Quick Start

1. Export Facebook cookies from your browser session using J2TEAM Cookies into `cookies_fb.json`.
2. Start the bridge container:

```bash
docker compose up -d --build
```

3. Fetch all pending posts in your Facebook group:

```bash
curl -s http://localhost:8899/v1/groups/1263207130787754/pending-posts
```

4. Approve or decline a pending post:

```bash
# Approve
curl -X POST http://localhost:8899/v1/groups/1263207130787754/pending-posts/UzpfSTEwMDA...:approve \
  -H 'Content-Type: application/json'

# Decline
curl -X POST http://localhost:8899/v1/groups/1263207130787754/pending-posts/UzpfSTEwMDA...:decline \
  -H 'Content-Type: application/json'
```

## Documentation

- [Interactive Web Docs](https://mrnim94.github.io/fb-cookie-bridge/)
- [OpenAPI 3.1 Contract](docs/openapi.yaml)
- [J2TEAM Cookie Setup & Mount](docs/j2team-cookie-setup.md)
- [n8n Workflow Integration Guide](docs/integrations.md)
- [Capability Matrix](docs/capabilities.md)

## License

MIT.
