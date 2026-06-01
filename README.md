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

Valid categories: `food`, `transport`, `housing`, `entertainment`, `health`, `income`, `other`

```
python -m budgetcli.cli add 45.50 food --note "Groceries"
python -m budgetcli.cli add 2500.00 income --note "Paycheck"
python -m budgetcli.cli add 1.75 transport
```

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

### clear

Delete all transactions. Prompts for confirmation.

```
python -m budgetcli.cli clear
```

## Development

```
# Run tests
python -m pytest tests/ -v --tb=short

# Lint
ruff check .

# Format
ruff format .
```
