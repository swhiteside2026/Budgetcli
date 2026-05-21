import csv

import pytest
from datetime import date
from pathlib import Path

import budgetcli.storage as storage
from budgetcli.models import Transaction


@pytest.fixture(autouse=True)
def tmp_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_file = tmp_path / "ledger.json"
    monkeypatch.setattr(storage, "DATA_FILE", fake_file)
    return fake_file


def _make_transaction(amount: float = 50.0, category: str = "food") -> Transaction:
    return Transaction(amount=amount, category=category, date=date(2026, 5, 1))


def test_load_returns_empty_when_no_file_exists() -> None:
    result = storage.load_transactions()
    assert result == []


def test_add_and_load_single_transaction() -> None:
    t = _make_transaction()
    storage.add_transaction(t)
    loaded = storage.load_transactions()
    assert len(loaded) == 1
    assert loaded[0].amount == t.amount
    assert loaded[0].category == t.category
    assert loaded[0].date == t.date


def test_add_multiple_transactions() -> None:
    t1 = _make_transaction(amount=50.0, category="food")
    t2 = _make_transaction(amount=1000.0, category="income")
    t3 = _make_transaction(amount=30.0, category="transport")
    storage.add_transaction(t1)
    storage.add_transaction(t2)
    storage.add_transaction(t3)
    loaded = storage.load_transactions()
    assert len(loaded) == 3
    assert loaded[1].category == "income"


def test_clear_all_wipes_transactions() -> None:
    storage.add_transaction(_make_transaction())
    storage.add_transaction(_make_transaction(amount=20.0, category="health"))
    storage.clear_all()
    assert storage.load_transactions() == []


def test_export_csv_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    assert out.exists()


def test_export_csv_header_row(tmp_path: Path) -> None:
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["date", "category", "amount", "note"]


def test_export_csv_data_row_matches_transaction(tmp_path: Path) -> None:
    t = Transaction(amount=42.5, category="food", date=date(2026, 5, 1), note="lunch")
    storage.add_transaction(t)
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1] == ["2026-05-01", "food", "42.5", "lunch"]


def test_export_csv_empty_ledger_writes_header_only(tmp_path: Path) -> None:
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1


def test_export_csv_multiple_rows_preserves_order(tmp_path: Path) -> None:
    t1 = Transaction(amount=100.0, category="income", date=date(2026, 5, 1), note="salary")
    t2 = Transaction(amount=20.0, category="food", date=date(2026, 5, 2), note="")
    storage.add_transaction(t1)
    storage.add_transaction(t2)
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3
    assert rows[1][1] == "income"
    assert rows[2][1] == "food"


def test_export_csv_note_with_comma_and_quote(tmp_path: Path) -> None:
    t = Transaction(amount=5.0, category="food", date=date(2026, 5, 1), note='coffee, "oat milk"')
    storage.add_transaction(t)
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1][3] == 'coffee, "oat milk"'


def test_export_csv_second_export_overwrites_first(tmp_path: Path) -> None:
    t1 = Transaction(amount=10.0, category="food", date=date(2026, 5, 1), note="first")
    t2 = Transaction(amount=20.0, category="food", date=date(2026, 5, 2), note="second")
    storage.add_transaction(t1)
    out = tmp_path / "transactions.csv"
    storage.export_csv(out)
    storage.add_transaction(t2)
    storage.export_csv(out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3  # header + 2 transactions, not 4 (header + 1 + header + 2)
