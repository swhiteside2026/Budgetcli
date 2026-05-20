# budgetcli

A CLI budget tracker that records income and expenses and shows 
how much the user saved or overspent each month. Stores data 
locally — not a web app, no database, single user only.

## directories
budgetcli/models.py   — Transaction dataclass and VALID_CATEGORIES list
budgetcli/storage.py  — read/write transactions to data/ledger.json
budgetcli/reports.py  — monthly summaries and category calculations
budgetcli/cli.py      — argparse entrypoint, handles all 5 commands
tests/                — mirrors src structure, one file per module
data/                 — gitignored, contains ledger.json at runtime

## commands
Run tests:   python -m pytest tests/ -v --tb=short
Lint:        ruff check .
Format:      ruff format .
Run locally: python -m budgetcli.cli add 45.50 food --note "Groceries"

## conventions
- snake_case functions, PascalCase classes
- Type hints required on all functions
- No bare except: — always catch specific exceptions like ValueError

## gotchas
- data/ is gitignored — won't exist after a fresh clone, storage.py 
  creates it automatically on first run
- Use python -m budgetcli.cli not budgetcli directly — the scripts 
  folder may not be on PATH
