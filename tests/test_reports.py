from datetime import date

from budgetcli.models import Transaction
from budgetcli.reports import category_breakdown, monthly_summary, overall_balance


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
