from datetime import date
from unittest.mock import patch

from budgetcli.models import Transaction
from budgetcli.reports import category_breakdown, check_budget, monthly_summary, overall_balance


def _t(amount: float, category: str, year: int, month: int, day: int = 1) -> Transaction:
    return Transaction(amount=amount, category=category, date=date(year, month, day))


TRANSACTIONS: list[Transaction] = [
    _t(2000.0, "income",        2026, 5),
    _t(  80.0, "food",          2026, 5),
    _t(  40.0, "transport",     2026, 5),
    _t(  30.0, "food",          2026, 5),
    _t(1500.0, "income",        2026, 4),
    _t(  60.0, "entertainment", 2026, 4),
]


def test_monthly_summary_correct_values() -> None:
    income, expenses, net = monthly_summary(TRANSACTIONS, 2026, 5)
    assert income == 2000.0
    assert expenses == 150.0
    assert net == 1850.0


def test_monthly_summary_no_transactions() -> None:
    income, expenses, net = monthly_summary([], 2026, 5)
    assert income == 0.0
    assert expenses == 0.0
    assert net == 0.0


def test_monthly_summary_only_correct_month() -> None:
    income, expenses, net = monthly_summary(TRANSACTIONS, 2026, 4)
    assert income == 1500.0
    assert expenses == 60.0
    assert net == 1440.0


def test_category_breakdown_groups_correctly() -> None:
    breakdown = category_breakdown(TRANSACTIONS, 2026, 5)
    assert breakdown == {"food": 110.0, "transport": 40.0}


def test_category_breakdown_excludes_income() -> None:
    breakdown = category_breakdown(TRANSACTIONS, 2026, 5)
    assert "income" not in breakdown


def test_category_breakdown_sorted_highest_first() -> None:
    breakdown = category_breakdown(TRANSACTIONS, 2026, 5)
    totals = list(breakdown.values())
    assert totals == sorted(totals, reverse=True)


def test_overall_balance() -> None:
    balance = overall_balance(TRANSACTIONS)
    total_income = 2000.0 + 1500.0
    total_expenses = 80.0 + 40.0 + 30.0 + 60.0
    assert balance == total_income - total_expenses


def test_overall_balance_empty() -> None:
    assert overall_balance([]) == 0.0


# --- check_budget tests ---

_BUDGET_TRANSACTIONS: list[Transaction] = [
    _t(2000.0, "income",    2026, 5),
    _t(  80.0, "food",      2026, 5),
    _t(  30.0, "food",      2026, 5),
    _t(  40.0, "transport", 2026, 5),
    _t(  50.0, "food",      2026, 4),  # previous month — should be excluded
]


@patch("budgetcli.reports.date")
def test_check_budget_under_budget(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("food", 200.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 110.0
    assert result["remaining"] == 90.0
    assert result["over_budget"] is False


@patch("budgetcli.reports.date")
def test_check_budget_over_budget(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("food", 100.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 110.0
    assert result["remaining"] == -10.0
    assert result["over_budget"] is True


@patch("budgetcli.reports.date")
def test_check_budget_exactly_at_limit(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("food", 110.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 110.0
    assert result["remaining"] == 0.0
    assert result["over_budget"] is False


@patch("budgetcli.reports.date")
def test_check_budget_no_spending_in_category(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("entertainment", 50.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 0.0
    assert result["remaining"] == 50.0
    assert result["over_budget"] is False


@patch("budgetcli.reports.date")
def test_check_budget_excludes_income(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("income", 500.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 0.0
    assert result["remaining"] == 500.0
    assert result["over_budget"] is False


@patch("budgetcli.reports.date")
def test_check_budget_excludes_other_months(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    result = check_budget("food", 200.0, _BUDGET_TRANSACTIONS)
    assert result["spent"] == 110.0  # April's 50.0 must not be included


@patch("budgetcli.reports.date")
def test_check_budget_decimal_amount(mock_date) -> None:
    mock_date.today.return_value = date(2026, 5, 26)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    transactions = [_t(10.10, "food", 2026, 5)]
    result = check_budget("food", 50.0, transactions)
    assert result["spent"] == 10.10
    assert result["remaining"] == 39.90
    assert result["over_budget"] is False
