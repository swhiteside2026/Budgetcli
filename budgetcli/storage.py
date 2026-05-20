import json
from pathlib import Path

from budgetcli.models import Transaction

DATA_FILE: Path = Path(__file__).parent.parent / "data" / "ledger.json"


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_transactions() -> list[Transaction]:
    _ensure_data_file()
    raw: list[dict] = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [Transaction.from_dict(item) for item in raw]


def save_transactions(transactions: list[Transaction]) -> None:
    _ensure_data_file()
    DATA_FILE.write_text(
        json.dumps([t.to_dict() for t in transactions], indent=2),
        encoding="utf-8",
    )


def add_transaction(transaction: Transaction) -> None:
    transactions = load_transactions()
    transactions.append(transaction)
    save_transactions(transactions)


def clear_all() -> None:
    save_transactions([])
