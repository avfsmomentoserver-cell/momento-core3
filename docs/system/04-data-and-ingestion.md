# 04 · Data & Ingestion

## Round event model

The atomic unit is a **round**: a single crash-curve outcome with a multiplier and timestamp, plus source and `ingest_method` metadata. Raw events are immutable; corrections are stored separately.

## Sources (current, tested)

Betway crash games, in the order recorded and validated:

1. `aviator`
2. `skyward`
3. `skyward-deluxe`

The pipeline is source-agnostic; new sources require only a collector and a `normalize_source()` entry.

## Storage

- SQLite in WAL mode, path via `MOMENTO_DATABASE_PATH` (default `backend/data/momento.db`).
- `ingest_method` tracked per row: `api`, `file`, `live-feed`.
- Sessions segmented by time gaps.

## Ingestion methods

1. **REST push** — `POST /api/v1/ingest`
2. **File watcher** — drop JSON/CSV/TXT into `backend/data/inbox/`
3. **Live engine** — provably-fair, cryptographically verifiable round generator

## Accepted formats

- JSON arrays or objects (keys `rounds`/`data`/`results`/`items`/`history`/`records`)
- CSV with or without header
- Plain list of numbers
- Multipliers read from `multiplier`, `value`, `crash_point`, `result`, or `payout`
- Timestamps: ISO-8601, epoch seconds, or epoch milliseconds

## Example

```bash
curl -X POST localhost:8000/api/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source":"aviator","rounds":[{"multiplier":2.41},{"multiplier":1.08}]}'
```
