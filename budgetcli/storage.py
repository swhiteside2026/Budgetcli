import csv
import json
from pathlib import Path

from budgetcli.models import Transaction

DATA_FILE: Path = Path(__file__).parent.parent / "data" / "ledger.json"


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"transactions": [], "limits": {}}), encoding="utf-8")


def _read_ledger() -> tuple[list[dict], dict[str, float]]:
    _ensure_data_file()
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    # migrate old bare-array format
    if isinstance(raw, list):
        return raw, {}
    return raw.get("transactions", []), raw.get("limits", {})


def _write_ledger(transactions: list[Transaction], limits: dict[str, float]) -> None:
    DATA_FILE.write_text(
        json.dumps({"transactions": [t.to_dict() for t in transactions], "limits": limits}, indent=2),
        encoding="utf-8",
    )


def load_transactions() -> list[Transaction]:
    raw_transactions, _ = _read_ledger()
    return [Transaction.from_dict(item) for item in raw_transactions]


def load_limits() -> dict[str, float]:
    _, limits = _read_ledger()
    return limits


def set_limit(category: str, amount: float) -> None:
    raw_transactions, limits = _read_ledger()
    transactions = [Transaction.from_dict(item) for item in raw_transactions]
    limits[category] = amount
    _write_ledger(transactions, limits)


def remove_limit(category: str) -> None:
    raw_transactions, limits = _read_ledger()
    transactions = [Transaction.from_dict(item) for item in raw_transactions]
    limits.pop(category, None)
    _write_ledger(transactions, limits)


def add_transaction(transaction: Transaction) -> None:
    raw_transactions, limits = _read_ledger()
    transactions = [Transaction.from_dict(item) for item in raw_transactions]
    transactions.append(transaction)
    _write_ledger(transactions, limits)


def clear_all() -> None:
    _, limits = _read_ledger()
    _write_ledger([], limits)


def export_csv(path: Path) -> None:
    """Export all transactions to a CSV file at the given path.

    Writes a header row (date, category, amount, note) followed by one row
    per transaction. Overwrites the file if it already exists.
    """
    transactions = load_transactions()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "category", "amount", "note"])
        for t in transactions:
            writer.writerow([t.date.isoformat(), t.category, round(t.amount, 2), t.note])
