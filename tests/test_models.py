import pytest
from datetime import date

from budgetcli.models import BudgetLimit, RecurringTransaction, Transaction, VALID_CATEGORIES


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


def test_empty_category_raises() -> None:
    with pytest.raises(ValueError, match="category"):
        Transaction(amount=10.0, category="", date=date(2026, 5, 1))


def test_custom_category_accepted() -> None:
    t = Transaction(amount=10.0, category="Spotify", date=date(2026, 5, 1))
    assert t.category == "Spotify"


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


def test_budget_limit_empty_category_raises() -> None:
    with pytest.raises(ValueError, match="category"):
        BudgetLimit(category="", amount=100.0)


def test_budget_limit_custom_category_accepted() -> None:
    bl = BudgetLimit(category="Spotify", amount=20.0)
    assert bl.category == "Spotify"


def test_budget_limit_zero_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        BudgetLimit(category="food", amount=0.0)


def test_budget_limit_negative_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        BudgetLimit(category="food", amount=-50.0)


def test_budget_limit_income_category_raises() -> None:
    with pytest.raises(ValueError, match="income"):
        BudgetLimit(category="income", amount=5000.0)


# --- RecurringTransaction tests ---

def test_recurring_valid_creation() -> None:
    rt = RecurringTransaction(amount=1200.0, category="rent", frequency="monthly", note="rent")
    assert rt.amount == 1200.0
    assert rt.category == "rent"
    assert rt.frequency == "monthly"
    assert rt.note == "rent"
    assert rt.last_applied is None


def test_recurring_invalid_amount_raises() -> None:
    with pytest.raises(ValueError, match="amount"):
        RecurringTransaction(amount=0.0, category="rent", frequency="monthly")


def test_recurring_empty_category_raises() -> None:
    with pytest.raises(ValueError, match="category"):
        RecurringTransaction(amount=100.0, category="", frequency="monthly")


def test_recurring_custom_category_accepted() -> None:
    rt = RecurringTransaction(amount=100.0, category="Listerhill Land Mortgage", frequency="monthly")
    assert rt.category == "Listerhill Land Mortgage"


def test_recurring_invalid_frequency_raises() -> None:
    with pytest.raises(ValueError, match="frequency"):
        RecurringTransaction(amount=100.0, category="food", frequency="daily")


def test_recurring_is_due_when_never_applied() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly")
    assert rt.is_due(date(2026, 6, 1)) is True


def test_recurring_is_due_when_applied_same_month() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly", last_applied=date(2026, 6, 15))
    assert rt.is_due(date(2026, 6, 1)) is False


def test_recurring_is_due_when_applied_previous_month() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly", last_applied=date(2026, 5, 1))
    assert rt.is_due(date(2026, 6, 1)) is True


def test_recurring_is_due_different_year_same_month() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly", last_applied=date(2025, 6, 1))
    assert rt.is_due(date(2026, 6, 1)) is True


def test_recurring_last_applied_string_converted() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly", last_applied="2026-06-01")  # type: ignore[arg-type]
    assert rt.last_applied == date(2026, 6, 1)


def test_recurring_to_dict_from_dict_round_trip() -> None:
    original = RecurringTransaction(
        amount=500.0, category="utilities", frequency="monthly",
        note="Electric", last_applied=date(2026, 5, 1),
    )
    restored = RecurringTransaction.from_dict(original.to_dict())
    assert restored.amount == original.amount
    assert restored.category == original.category
    assert restored.frequency == original.frequency
    assert restored.note == original.note
    assert restored.last_applied == original.last_applied


def test_recurring_to_dict_none_last_applied() -> None:
    rt = RecurringTransaction(amount=100.0, category="food", frequency="monthly")
    assert rt.to_dict()["last_applied"] is None
