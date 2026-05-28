import pytest
from datetime import date

from budgetcli.models import BudgetLimit, Transaction, VALID_CATEGORIES


def test_valid_transaction_creation() -> None:
    t = Transaction(amount=100.0, category="food", date=date(2026, 5, 1))
    assert t.amount == 100.0
    assert t.category == "food"
    assert t.date == date(2026, 5, 1)
    assert t.note == ""


def test_is_income_true() -> None:
    t = Transaction(amount=1000.0, category="income", date=date(2026, 5, 1))
    assert t.is_income is True


def test_is_income_false() -> None:
    t = Transaction(amount=50.0, category="food", date=date(2026, 5, 1))
    assert t.is_income is False


def test_invalid_category_raises() -> None:
    with pytest.raises(ValueError, match="category"):
        Transaction(amount=10.0, category="nonsense", date=date(2026, 5, 1))


def test_zero_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        Transaction(amount=0.0, category="food", date=date(2026, 5, 1))


def test_negative_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        Transaction(amount=-10.0, category="food", date=date(2026, 5, 1))


def test_date_string_converted() -> None:
    t = Transaction(amount=25.0, category="food", date="2026-05-01")  # type: ignore[arg-type]
    assert t.date == date(2026, 5, 1)
    assert isinstance(t.date, date)


def test_to_dict_from_dict_round_trip() -> None:
    original = Transaction(
        amount=99.99, category="health", date=date(2026, 5, 15), note="Dentist"
    )
    restored = Transaction.from_dict(original.to_dict())
    assert restored.amount == original.amount
    assert restored.category == original.category
    assert restored.date == original.date
    assert restored.note == original.note


def test_to_dict_date_is_string() -> None:
    t = Transaction(amount=10.0, category="food", date=date(2026, 5, 1))
    d = t.to_dict()
    assert isinstance(d["date"], str)
    assert d["date"] == "2026-05-01"


# --- BudgetLimit tests ---

def test_budget_limit_valid() -> None:
    bl = BudgetLimit(category="food", amount=200.0)
    assert bl.category == "food"
    assert bl.amount == 200.0


def test_budget_limit_invalid_category_raises() -> None:
    with pytest.raises(ValueError, match="category"):
        BudgetLimit(category="nonsense", amount=100.0)


def test_budget_limit_zero_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        BudgetLimit(category="food", amount=0.0)


def test_budget_limit_negative_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        BudgetLimit(category="food", amount=-50.0)
