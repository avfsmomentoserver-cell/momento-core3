# 08 · Deployment & Configuration

## Backend essentials

```bash
MOMENTO_API_HOST=0.0.0.0
MOMENTO_API_PORT=8000
MOMENTO_DATABASE_PATH=backend/data/momento.db
MOMENTO_SECRET_KEY=<openssl rand -hex 32>
MOMENTO_OPERATOR_EMAIL=operator@momento.local
MOMENTO_OPERATOR_PASSWORD=<change-me>
MOMENTO_FEED_AUTOSTART=false
MOMENTO_CORS_ORIGINS=<comma-separated>
MOMENTO_CORS_ALLOW_ALL=false
```

## Frontend

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

When unset and not served by a dev server, the frontend falls back to the current origin (correct for reverse-proxied deployments).

## Run commands

```bash
# backend
python3 -m compileall -q momento run_api.py   # syntax check
python3 run_api.py --init-only                # create db and exit
python3 run_api.py --receiver-only            # watcher only
python3 run_api.py --reload                   # dev auto-reload

# frontend
bun run dev
bun run build
bun run lint
```

## Deployment target

Reference deployment: **Debian on Azure** (docs step 13). Recommended: nginx reverse proxy for TLS termination, firewall exposing only required ports, strong secret key, changed operator credentials.

## Security

- Never expose raw historical data; corrections recorded separately with an audit trail.
- Input validation, error handling, rate limiting, auth on all endpoints.
- HTTPS in production.
