# 02 · Backend

Location: `backend/momento/` (core) and `backend/features/` (feature packs).

## Core modules (`backend/momento/`)

| Module | Responsibility |
| --- | --- |
| `analysis.py` | Ladders, resistance, streaks, regimes, edge fit (pure functions) |
| `forecast.py` | Forecast engine: Markov + percentile + DNA blend |
| `store.py` | Storage layer, `analysis_payload()`, normalization, memoization |
| `db.py` | SQLAlchemy models and persistence |
| `feed.py` | Live provably-fair round engine |
| `watcher.py` | File watcher for inbox ingestion |
| `hub.py` | WebSocket broadcast hub |
| `linguistics.py` | Eight-layer semantic vocabulary |
| `orchestrator.py` | Decision orchestrator (patience, speed, risk, mistake prevention) |
| `autopilot.py` | Paper decision recorder + measured paper P&L |
| `plugins.py` | Analyzer registry with live weights |
| `auth.py` | Authentication / authorization |
| `config.py` | Environment-driven configuration |
| `backtest.py` | Backtesting engine |

## Pattern & feature intelligence

- `pattern_discovery.py`, `pattern_discovery_dna.py`, `pattern_discovery_moonshot.py`, `pattern_discovery_pressure.py`
- `incremental_features.py`, `parallel_features.py`, `feature_cache.py`, `feature_alerts.py`
- Vocabulary subsystem: `vocabulary_schema.py`, `vocabulary_processor.py`, `vocabulary_features.py`, `vocabulary_learning.py`, `vocabulary_usage.py`, `vocabulary_auto_import.py`

## Feature packs (`backend/features/`)

| Pack | Contents |
| --- | --- |
| `ai/` | `config.py`, `optimizer.py`, `pattern_learner.py`, `feature_importance.py` |
| `band_analysis/` | `ladders.py`, `relativity.py` |
| `equal_baseline/` | `converter.py`, `trendlines.py` |
| `moonshot_scanner/` | `scanner.py`, `exhaustion.py`, `linguistics.py` |
| `pressure/` | pressure-based analyzers |

## AI configuration (`backend/features/ai/config.py`)

- Optimizer: `optimizer_min_samples`, `optimizer_confidence_threshold`, `optimizer_max_runtime`
- Pattern learner: `learner_window_size`, `learner_min_samples`, `learner_balance_classes`, `learner_feature_threshold`
- ML (future): `ml_enabled` (currently `False`), `ml_framework` (`sklearn`/`xgboost`/`tensorflow`), CV folds, test size

The ML layer is scaffolded but **not yet enabled** — a key v5 entry point.

## Backend function patterns

- **Pure analysis functions** in `analysis.py`: no I/O, take rounds + settings, return dicts, handle empty input.
- **Store functions** in `store.py`: normalize source, parameterized queries, structured dict returns.
- **API endpoints** in `api/routes/`: `source_param` dependency, `Query` validation, broadcast via hub.
