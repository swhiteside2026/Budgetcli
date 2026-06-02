# budgetcli

A command-line budget tracker that records income and expenses and shows how much you saved or overspent each month. Stores data locally in a JSON ledger — no database, no web service, single user only.

## Installation

```
pip install -e .
```

Data is stored in `data/ledger.json`, which is created automatically on first run.

## Usage

```
python -m budgetcli.cli <command> [options]
```

### --version

```
python -m budgetcli.cli --version
```

Output: `budget 0.1.0`

### add

Record a transaction. Amount is treated as an expense unless the category is `income`.

```
python -m budgetcli.cli add <amount> <category> [--note "text"]
```

Valid categories: `income`, `food`, `transport`, `rent`, `utilities`, `entertainment`, `health`, `investment`, `hysa`, `other`

```
python -m budgetcli.cli add 45.50 food --note "Groceries"
python -m budgetcli.cli add 2500.00 income --note "Paycheck"
python -m budgetcli.cli add 1.75 transport
```

If a spending limit is set for the category (see `set-limit`), a warning is printed to stderr when spending reaches 80% of the limit or goes over.

### summary

Show this month's total income, total expenses, and net balance.

```
python -m budgetcli.cli summary
```

### report

Show spending broken down by category for the current month, plus the overall all-time balance.

```
python -m budgetcli.cli report
```

### list

List the 20 most recent transactions.

```
python -m budgetcli.cli list
```

### export

Export all transactions to `transactions.csv` in the current directory.

```
python -m budgetcli.cli export
```

Note: close the file in Excel before re-running export, or the write will fail.

### set-limit

Set a monthly spending limit for a category. The limit is stored in `data/ledger.json` and persists across sessions.

```
python -m budgetcli.cli set-limit <category> <amount>
```

```
python -m budgetcli.cli set-limit food 300
python -m budgetcli.cli set-limit transport 100
```

After each `add`, the CLI prints a warning to stderr if spending in that category is at or above 80% of the limit, or has gone over. Limits cannot be set on the `income` category.

### limits

Show all budget limits alongside current month spending and status.

```
python -m budgetcli.cli limits
```

The status column shows `ok`, `NEAR` (at or above 80% of limit), or `OVER` (exceeded).

### clear

Delete all transactions. Prompts for confirmation. Budget limits are not affected.

```
python -m budgetcli.cli clear
```

## Web dashboard (optional)

A Flask dashboard is available at `app.py`. It reads from the same `data/ledger.json` as the CLI and shows a summary of the current month's spending, budget limit progress bars, and a full transaction list.

Flask is not included in the default dependencies. Install it separately:

```
pip install flask
```

Then run:

```
python app.py
```

Open http://localhost:5000 in a browser.

## Development

```
# Run tests
python -m pytest tests/ -v --tb=short

# Lint
ruff check .

# Format
ruff format .
```

