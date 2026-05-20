from budgetcli.models import Transaction


def monthly_summary(
    transactions: list[Transaction], year: int, month: int
) -> tuple[float, float, float]:
    filtered = [t for t in transactions if t.date.year == year and t.date.month == month]
    income = sum(t.amount for t in filtered if t.is_income)
    expenses = sum(t.amount for t in filtered if not t.is_income)
    return income, expenses, income - expenses


def category_breakdown(
    transactions: list[Transaction], year: int, month: int
) -> dict[str, float]:
    filtered = [
        t for t in transactions
        if t.date.year == year and t.date.month == month and not t.is_income
    ]
    totals: dict[str, float] = {}
    for t in filtered:
        totals[t.category] = totals.get(t.category, 0.0) + t.amount
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def overall_balance(transactions: list[Transaction]) -> float:
    income = sum(t.amount for t in transactions if t.is_income)
    expenses = sum(t.amount for t in transactions if not t.is_income)
    return income - expenses
