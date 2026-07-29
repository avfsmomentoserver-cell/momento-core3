# 01 · Architecture

## Pipeline

```
Collector -> Ingest API -> Analysis -> Forecast Engine -> Database -> Dashboard
```

## Technology stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite (WAL mode)
- **Frontend**: Vite + React 18 + TypeScript, shadcn/ui, TailwindCSS
- **Realtime**: custom WebSocket hub (single multiplexed connection)
- **Collection**: Playwright browser automation + provably-fair live engine
- **Testing**: unit, integration, replay, historical, live validation

## Architecture layers

1. **Data Collection** — `feed.py`, `watcher.py`, `collector_aviator.js`
2. **Data Storage** — SQLite with `ingest_method` tracking (`api`, `file`, `live-feed`)
3. **Analysis Engine** — `analysis.py` (pure functions), `forecast.py`
4. **API Layer** — modular FastAPI routers in `api/routes/`
5. **Realtime Layer** — `hub.py` broadcasting
6. **Frontend** — React Router + `PlatformProvider` context as single source of truth

## The Momento Kernel

- **Round Event Model** — core data structure for a crash round
- **Database Layer** — SQLAlchemy ORM over SQLite
- **Schema Contracts** — explicit contracts between modules
- **Runtime / Event Bus** — event-driven communication
- **API Contracts** — REST + WebSocket
- **Engine Registry** — plugin system for analyzers (`plugins.py`)

## Intelligence engine chain

```
Pattern -> DNA -> Similarity -> Probability -> Confidence -> Forecast
```

Each engine is replaceable behind a clear contract, independently tested, and produces measurable output.

## Data flow

- **Ingestion**: Collector/Watcher -> `store.ingest_file()` -> Database -> WebSocket broadcast -> Frontend
- **Analysis**: Database -> `store.history()` -> `analysis.analyze()` -> `forecast.forecast()` -> `analysis_payload()` -> API -> Frontend
- **Realtime**: New round -> Database -> `hub.broadcast()` -> WebSocket -> `PlatformProvider` -> UI update

## Key patterns

- Pure analysis functions (no I/O) for testability
- Memoization in `store.analysis_payload()` (1-second TTL)
- Session segmentation by time gaps
- `PlatformProvider` as the single frontend source of truth
