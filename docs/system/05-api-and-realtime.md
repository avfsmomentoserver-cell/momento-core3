# 05 · API & Realtime

## FastAPI application

Entry: `backend/run_api.py`; app assembled in `backend/momento/api/app.py`; shared dependencies in `api/deps.py`; schemas in `api/schemas.py`.

Interactive OpenAPI docs at `/docs`; health at `/api/v1/health`.

## Route modules (`backend/momento/api/routes/`)

| Router | Purpose |
| --- | --- |
| `core.py` | Health, platform meta |
| `platform.py` | Platform snapshot / provider payload |
| `rounds.py` | Round listing and paging |
| `analysis.py` | Analysis payloads |
| `forecasts.py` | Forecast projections and scoring |
| `engines.py` | Engine registry |
| `features.py` | Feature extraction endpoints |
| `market.py` | Market view |
| `mega_pressure.py` | Mega-pressure tracker feed |
| `backtest.py` / `backtest_enhanced.py` | Backtesting |
| `ingest.py` | Ingestion endpoints |
| `vocabulary.py` | Linguistics vocabulary |
| `users.py` | User management |
| `ws.py` | WebSocket endpoint |

## Realtime

`hub.py` broadcasts events (e.g. `ingest:scan`, feature updates) over a single multiplexed WebSocket. Frontend `PlatformProvider` subscribes and invalidates React Query caches on relevant events.

## Contracts

- Every prediction returned carries explanation metadata.
- Forecasts are recorded before the round lands (honest-accuracy contract).
- Event contracts must be preserved by backend changes.
