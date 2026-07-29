# MomentoAVFSCore — System Documentation

> **AVFS** = **A**nalysis, **V**ocabulary, **F**orecast, **S**trategy — the four-pillar engine at the core of the Momento platform.

This is the authoritative documentation set for the **current system (v4)**. It describes what exists today, exactly as built, before any v5 evolution.

## What this platform is

MomentoAVFSCore is a **modular analytics and forecasting engine** that applies proprietary strategies and inventions to help customers make better-informed decisions in **casino crash games**. It is deliberately game-agnostic: the current, recorded and tested starting point is **Betway crash games** — `aviator` → `skyward` → `skyward-deluxe` — but the pipeline accepts any multiplier stream.

```
Collector -> Ingest API -> Analysis -> Forecast Engine -> Database -> Dashboard
```

## Version history

| Version | Status | Notes |
| --- | --- | --- |
| v1 | Present (legacy) | Different architecture, retained for reference |
| v2 | Failed | Deprecated |
| v3 | Failed | Deprecated |
| **v4** | **Current** | FastAPI + React modular pipeline documented here |
| v5 | Planned | Realtime, robust, intelligent, fully commercial (see roadmap) |

## Documentation map

| Doc | Topic |
| --- | --- |
| [01-architecture.md](01-architecture.md) | High-level architecture, pipeline, kernel, layers |
| [02-backend.md](02-backend.md) | Backend modules, analysis, forecast, vocabulary, patterns |
| [03-frontend.md](03-frontend.md) | Web console, consumer app, screens, state |
| [04-data-and-ingestion.md](04-data-and-ingestion.md) | Round model, storage, ingest methods, formats |
| [05-api-and-realtime.md](05-api-and-realtime.md) | REST routes, WebSocket hub, contracts |
| [06-inventions.md](06-inventions.md) | Invention framework, MomentoFX, trackers, middleware |
| [07-agents-and-workflows.md](07-agents-and-workflows.md) | .devin agent system, skills, workflows |
| [08-deployment-and-config.md](08-deployment-and-config.md) | Config, environments, deployment, security |
| [09-glossary.md](09-glossary.md) | Domain terms and concepts |

## Core principles (unchanged across versions)

1. **Observation before prediction** — understand the present before reasoning about the future.
2. **Immutable raw events** — raw data is never edited; corrections are recorded separately.
3. **Explainability is mandatory** — every prediction carries explanation metadata.
4. **Local vs production independence** — local SQLite dev must always work.
5. **Honest accuracy** — forecasts are scored only against projections recorded *before* the round landed.

## Responsible use

This platform is analytical instrumentation. Forecasts are probabilistic estimates over historical structure, never guarantees; no model can predict a truly random outcome. The autopilot is a paper-trading decision recorder — it never places a real stake.
