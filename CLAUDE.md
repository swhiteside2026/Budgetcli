# budgetcli

A CLI budget tracker that records income and expenses and shows 
how much the user saved or overspent each month. Stores data 
locally — not a web app, no database, single user only.

## directories
budgetcli/models.py   — Transaction and BudgetLimit dataclasses, VALID_CATEGORIES list
budgetcli/storage.py  — read/write transactions and limits to data/ledger.json
budgetcli/reports.py  — monthly summaries, category calculations, limit warnings
budgetcli/cli.py      — argparse entrypoint, handles all 8 commands
tests/                — mirrors src structure, one file per module
data/                 — gitignored, contains ledger.json at runtime
app.py                — optional Flask web dashboard; reads the same ledger.json
templates/            — Jinja2 templates for the Flask dashboard

## ledger.json format
Both transactions and budget limits are stored in a single JSON object:

  {
    "transactions": [
      { "amount": 45.50, "category": "food", "date": "2026-06-01", "note": "Groceries" }
    ],
    "limits": { "food": 300.0, "transport": 100.0 }
  }

Files in the old bare-array format (a plain list of transaction dicts, from before
the budget-limit feature) are migrated automatically on first read.

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
- transactions.csv cannot be overwritten while open in Excel — close 
  it before running the export command again
- Two Claude Code hooks run silently during development:
  .claude/hooks/post_write_lint.py  — runs ruff check . after every Python file write
  .claude/hooks/pre_commit_test.py  — runs the full test suite before any git commit;
                                      blocks the commit if any test fails

