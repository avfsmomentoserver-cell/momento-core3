# 03 · Frontend

Location: `web/` (Vite + React + TypeScript).

## Structure

- `src/components/` — `admin/`, `charts/`, `console/`, `layout/`, `panels/`, `ui/` (shadcn/ui)
- `src/hooks/` — shared React hooks
- `src/lib/` — utilities incl. `invent-middleware/`
- `src/modules/momentofx-v2/` — MomentoFX professional module (components, hooks, services, types, utils)
- `src/pages/` — `app/` (consumer), `auth/`, `dashboard/` (operator)
- `src/state/` — global state / `PlatformProvider`
- `src/test/` — frontend tests

## Eight sub-projects and their surfaces

| Sub-project | Surface |
| --- | --- |
| Collector & Ingest | `/dashboard/ingest` |
| Analysis Core | `/dashboard` |
| MomentoLinguistics | `/dashboard/linguistics` |
| Forecast Engine | `/dashboard/studio` |
| Decision Orchestrator | `/orchestrator` |
| Autopilot Ledger | `/dashboard/autopilot` |
| Plugin Inventory | `/inventory` |
| Consumer App | `/app` |

## Twenty screens

**Operator console**: Command Center, Market, Ladder Telemetry, Resistance, Moonshot Finder, DNA Hunter, Forecast Studio, Linguistics, Orchestrator, Autopilot, Plugin Inventory, Ingest Console, Sources, Bird's Eye, Build Steps, Master Settings, Users, Round Testing.

**Consumer app**: Today, Pro Predictions, Charts, Premium.

## Data strategy (Command Center pattern)

- File-based rounds with `ingest_method="file"` for stability.
- File-based analysis via `store.analysis_payload(..., ingest_method="file")`.
- WebSocket invalidation on `ingest:scan` events.
- Consistent polling intervals (`POLL.rounds`, `POLL.analysis`, `POLL.slow`).

## Component library

shadcn/ui + TailwindCSS. Common: `AppShell`, `Panel`, `StatTile`, `Button`, `Input`, `Label`, `EmptyState`, `StateBadge`, `RoundsFeed`. Semantic colors: signal, caution, critical, info. Lucide React icons.
