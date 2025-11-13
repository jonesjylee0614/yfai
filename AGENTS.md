# Repository Guidelines

## Project Structure & Module Organization
Keep feature code inside `yfai/`: UI lives in `app/`, orchestration logic in `core/`, provider adapters in `providers/`, MCP plumbing in `mcp/`, and host capabilities in `localops/`. Configuration templates sit under `configs/`, reusable scripts under `scripts/`, and docs in `docs/` or `prototype/`. Automated tests belong in `tests/` (unit) and `test_integration.py` (end‑to‑end); keep fixtures near the specs that rely on them.

## Build, Test & Development Commands
Use Poetry by default: `poetry install` to sync deps, `poetry run yfai` or `poetry run python -m yfai.main` to launch the console, and `poetry run python run.py` for scripted sessions. `poetry run pytest tests/` covers fast feedback, while `poetry run pytest test_integration.py -k critical` exercises full flows. Static checks run via `poetry run ruff check .`, `poetry run ruff format .`, and `poetry run mypy yfai/`.

## Coding Style & Naming Conventions
Target Python 3.11, 4‑space indentation, and Ruff’s 100‑char line limit. Favor type hints on public boundaries, `snake_case` for functions and modules, `PascalCase` for PyQt widgets and service classes, and `UPPER_SNAKE_CASE` for constants or env keys. Keep UI resources in `app/resources` and factor reusable logic into `core/` or `localops/` to avoid bloated widgets. Run `ruff format .` before committing so imports are ordered consistently.

## Testing Guidelines
Add unit tests alongside the module being edited; mirror the filename (e.g., `tests/test_router.py`). Integration scenarios that touch providers, MCP, or local ops should extend `test_integration.py`. Include regression cases whenever reproducing a bug. Aim for meaningful assertions over blanket coverage, and document required fixtures or mocks in the test docstring. Always run `pytest` plus targeted checks for the area you changed.

## Commit & Pull Request Guidelines
Write commits in the imperative (“Add MCP registry health checks”) and scope them to a single concern. Reference related issues or docs inline (e.g., `core:` or `app:` prefixes) so history stays searchable even outside GitHub. Pull requests should include: summary of intent, testing evidence (`pytest`, `ruff`, `mypy` output), configuration steps if new env keys are needed, and screenshots for UI-affecting changes.

## Security & Configuration Tips
Never hardcode secrets; copy `configs/.env.example` to `configs/.env`, populate API keys locally, and document any new variables in that template. Treat `configs/config.yaml` as user-owned—introduce new knobs via sensible defaults and describe them in `docs/` before shipping. When exercising dangerous local operations, ensure guard policies in `security/` are updated and accompanied by tests validating approval flows.
