from datetime import date

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


# TODO: make configurable per-limit or globally via a `budget config` command
WARN_THRESHOLD: float = 0.80


def check_limits(
    category_totals: dict[str, float], limits: dict[str, float]
) -> list[str]:
    """Return warning strings for categories at or near their monthly limit.

    Limits always apply to the full calendar month-to-date. Two warning levels:
    - near: spent >= WARN_THRESHOLD of limit (but not over)
    - over: spent exceeds limit
    """
    warnings: list[str] = []
    for category, limit in limits.items():
        spent = category_totals.get(category, 0.0)
        if spent > limit:
            warnings.append(
                f"Warning: {category} is over budget (${spent:.2f} spent, ${limit:.2f} limit)"
            )
        elif spent >= limit * WARN_THRESHOLD:
            warnings.append(
                f"Warning: {category} is near its limit (${spent:.2f} of ${limit:.2f} spent)"
            )
    return warnings


def check_budget(
    category: str, limit: float, transactions: list[Transaction]
) -> dict[str, float | bool]:
    today = date.today()
    spent = sum(
        t.amount
        for t in transactions
        if t.date.year == today.year
        and t.date.month == today.month
        and t.category == category
        and not t.is_income
    )
    return {"spent": spent, "remaining": limit - spent, "over_budget": spent > limit}
