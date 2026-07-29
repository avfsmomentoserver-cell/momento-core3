# 07 · Agents & Workflows

Configuration lives in `.devin/` (mirrored by the reusable `mdos-package/`).

## Config (`.devin/config.json`)

- Project: Momento Core Platform, version **4.0.0**
- Default agent: `ag_admin`
- Entry point: `all_prompts`, skills-first
- Fallback hierarchy: skills -> project_admin -> specialist_agents -> general_purpose
- Execution modes: `low_credit_efficient` (max depth 2) and `full_power` (max depth 5)
- Requirements collected first: goal, scope, constraints, acceptance_criteria, timeline

## Specialist agents (`.devin/AGENTS.md`)

`ag_admin` (orchestration), `ag_arch` (architecture), `ag_backend`, `ag_frontend`, `ag_db`, `ag_collector`, `ag_forecast`, `ag_devops`, `ag_docs`, `ag_qa`, `ag_mentor` (teaching in four layers).

## Skills (`.devin/skills/`)

`fastapi.md`, `react.md`, `playwright.md`, `sqlite.md`, `testing.md`, `forecast.md`, `docs.md`, `momento-core-standards.md`.

## Workflows (`.devin/workflows/`)

- `/standard-task`: Understand -> Design -> Implement -> Test -> Document -> Review
- `/new-feature`: Purpose -> Necessity -> Separation -> Measurement -> Evolution -> Implement
- `/architecture-review`: Read current -> Find weaknesses -> Design target -> ADR -> Migration plan
- `/deployment`: Build -> Validate -> Stage -> Promote -> Monitor
