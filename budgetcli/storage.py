import csv
import json
from datetime import date
from pathlib import Path

from budgetcli.models import RecurringTransaction, Transaction

DATA_FILE: Path = Path(__file__).parent.parent / "data" / "ledger.json"


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(
            json.dumps({"transactions": [], "limits": {}, "recurring": []}),
            encoding="utf-8",
        )


def _read_ledger() -> tuple[list[dict], dict[str, float], list[dict]]:
    """Read the full ledger and return (transactions, limits, recurring).

    Transparently migrates the old bare-array format (pre-budget-limits) to the
    current {"transactions": [...], "limits": {...}, "recurring": [...]} structure.
    """
    _ensure_data_file()
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw, {}, []
    return raw.get("transactions", []), raw.get("limits", {}), raw.get("recurring", [])


def _write_ledger(
    transactions: list[dict],
    limits: dict[str, float],
    recurring: list[dict],
) -> None:
    DATA_FILE.write_text(
        json.dumps(
            {"transactions": transactions, "limits": limits, "recurring": recurring},
            indent=2,
        ),
        encoding="utf-8",
    )


def load_transactions() -> list[Transaction]:
    raw_transactions, _, _ = _read_ledger()
    return [Transaction.from_dict(item) for item in raw_transactions]


def load_limits() -> dict[str, float]:
    _, limits, _ = _read_ledger()
    return limits


def set_limit(category: str, amount: float) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    limits[category] = amount
    _write_ledger(raw_transactions, limits, recurring)


def remove_limit(category: str) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    limits.pop(category, None)
    _write_ledger(raw_transactions, limits, recurring)


def add_transaction(transaction: Transaction) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    raw_transactions.append(transaction.to_dict())
    _write_ledger(raw_transactions, limits, recurring)


def clear_all() -> None:
    _, limits, recurring = _read_ledger()
    _write_ledger([], limits, recurring)


def delete_transaction(index: int) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    raw_transactions.pop(index)
    _write_ledger(raw_transactions, limits, recurring)


def update_transaction(index: int, transaction: Transaction) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    raw_transactions[index] = transaction.to_dict()
    _write_ledger(raw_transactions, limits, recurring)


def load_recurring() -> list[RecurringTransaction]:
    _, _, raw_recurring = _read_ledger()
    return [RecurringTransaction.from_dict(r) for r in raw_recurring]


def add_recurring(rt: RecurringTransaction) -> None:
    raw_transactions, limits, raw_recurring = _read_ledger()
    raw_recurring.append(rt.to_dict())
    _write_ledger(raw_transactions, limits, raw_recurring)


def save_recurring(recurring: list[RecurringTransaction]) -> None:
    raw_transactions, limits, _ = _read_ledger()
    _write_ledger(raw_transactions, limits, [r.to_dict() for r in recurring])


def export_csv(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
) -> None:
    """Export transactions to a CSV file at the given path.

    Writes a header row (date, category, amount, note) followed by one row
    per transaction. Overwrites the file if it already exists.
    from_date and to_date are inclusive bounds; omit either to leave that end open.
    """
    transactions = load_transactions()
    if from_date is not None:
        transactions = [t for t in transactions if t.date >= from_date]
    if to_date is not None:
        transactions = [t for t in transactions if t.date <= to_date]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "category", "amount", "note"])
        for t in transactions:
            writer.writerow([t.date.isoformat(), t.category, round(t.amount, 2), t.note])
