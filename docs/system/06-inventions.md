# 06 · Inventions Framework

The **invention system** (`invent/`) lets new analytical products be built in strict isolation from the core, integrating only via a menu link and a route.

## Isolation rules

- Read-only API access to the core system.
- Separate middleware pipeline; independent state.
- No backend, schema, or existing-endpoint modifications.
- Only additions allowed to the main app: one route + one sidebar link.

## Middleware architecture

```
Data Ingester -> Transform Processor -> Analysis Engine -> State Manager -> UI Adapter
```

Files: `invent/middleware/` and `web/src/lib/invent-middleware/` — `dataIngester.ts`, `transformProcessor.ts`, `analysisEngine.ts`, `stateManager.ts`, `momentoFX.ts`, `megaPressure.ts`, `index.ts`.

## Inventions

### Pattern DNA Tracker (`invent/pattern-dna-tracker/`)
Pattern recognition (alternating, streak, time-based), anomaly detection (z-score, multi-severity), AI prediction ranges, DNA magnitude/distribution analysis. Surface: `/dashboard/pattern-dna`.

### Mega Pressure Tracker (`invent/mega-pressure-tracker/`)
Pressure-based analytics; backed by `mega_pressure.py` route. Surface: mega-pressure screen.

### MomentoFX Professional (`invent/MomentoFX/` + `web/src/modules/momentofx-v2/`)
MT5-level forex-style trading interface for crash games, aimed at technically skilled traders.
- TradingView Lightweight Charts with dual-axis zoom
- 8 drawing tools with smart support/resistance suggestions
- Indicators: RSI, MACD, Bollinger, Stochastic, MA(20/50), ATR
- Pattern recognition integrated with core forecast, DNA, and linguistics
- 6 timeframes (1m/5m/15m/1h/4h/1D) with synchronized switching
- Surface: `/dashboard/momento-fx`

See `invent/INVENTION_SUMMARY.md` and `invent/WORKFLOW.md` for the full autonomous invention process.
