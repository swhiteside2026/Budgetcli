# Transaction data model
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

VALID_CATEGORIES: list[str] = [
    "income", "food", "transport", "rent", "utilities",
    "entertainment", "health", "investment", "hysa", "other",
]


@dataclass
class Transaction:
    amount: float
    category: str
    date: date
    note: str = field(default="")
    source: str = field(default="manual")

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        if not self.category.strip():
            raise ValueError("category cannot be empty")
        if isinstance(self.date, str):
            self.date = date.fromisoformat(self.date)

    @property
    def is_income(self) -> bool:
        return self.category.lower() == "income"

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "category": self.category,
            "date": self.date.isoformat(),
            "note": self.note,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        return cls(
            amount=float(data["amount"]),
            category=data["category"],
            date=data["date"],
            note=data.get("note", ""),
            source=data.get("source", "manual"),
        )


VALID_FREQUENCIES: list[str] = ["weekly", "biweekly", "monthly", "annually"]


def _add_months(d: date, n: int) -> date:
    """Return d shifted forward by n calendar months, clamping to the last day of the target month."""
    m = d.month + n
    y = d.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def _add_years(d: date, n: int) -> date:
    """Return d shifted forward by n years, falling back to Mar 1 for Feb-29 in non-leap years."""
    try:
        return date(d.year + n, d.month, d.day)
    except ValueError:
        return date(d.year + n, 3, 1)


@dataclass
class RecurringTransaction:
    amount: float
    category: str
    frequency: str
    note: str = field(default="")
    last_applied: date | None = field(default=None)
    effective_date: date | None = field(default=None)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        if not self.category.strip():
            raise ValueError("category cannot be empty")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {VALID_FREQUENCIES}")
        if isinstance(self.last_applied, str):
            self.last_applied = date.fromisoformat(self.last_applied)
        if isinstance(self.effective_date, str):
            self.effective_date = date.fromisoformat(self.effective_date)

    def is_due(self, today: date) -> bool:
        start = self.effective_date or date.min
        if today < start:
            return False
        if self.last_applied is None:
            return True
        if self.frequency == "weekly":
            return (today - self.last_applied).days >= 7
        if self.frequency == "biweekly":
            return (today - self.last_applied).days >= 14
        if self.frequency == "annually":
            return today.year != self.last_applied.year
        # monthly (default)
        return today.year != self.last_applied.year or today.month != self.last_applied.month

    def next_due_date(self, today: date) -> date | None:
        """The concrete date this rule will next fire, or None if already due."""
        if self.is_due(today):
            return None
        if self.last_applied is None:
            return self.effective_date or today
        if self.frequency == "weekly":
            return self.last_applied + timedelta(days=7)
        if self.frequency == "biweekly":
            return self.last_applied + timedelta(days=14)
        if self.frequency == "annually":
            return _add_years(self.last_applied, 1)
        # monthly
        return _add_months(self.last_applied, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "category": self.category,
            "frequency": self.frequency,
            "note": self.note,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecurringTransaction":
        return cls(
            amount=float(data["amount"]),
            category=data["category"],
            frequency=data.get("frequency", "monthly"),
            note=data.get("note", ""),
            last_applied=data.get("last_applied"),
            effective_date=data.get("effective_date"),
        )


@dataclass
class BudgetLimit:
    category: str
    amount: float

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ValueError("category cannot be empty")
        if self.category.lower() == "income":
            raise ValueError("budget limits cannot be set on the income category")
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
