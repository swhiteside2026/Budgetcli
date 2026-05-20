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
