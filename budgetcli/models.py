# Transaction data model
from dataclasses import dataclass, field
from datetime import date
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

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        if isinstance(self.date, str):
            self.date = date.fromisoformat(self.date)

    @property
    def is_income(self) -> bool:
        return self.category == "income"

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "category": self.category,
            "date": self.date.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        return cls(
            amount=float(data["amount"]),
            category=data["category"],
            date=data["date"],
            note=data.get("note", ""),
        )


VALID_FREQUENCIES: list[str] = ["monthly"]


@dataclass
class RecurringTransaction:
    amount: float
    category: str
    frequency: str
    note: str = field(default="")
    last_applied: date | None = field(default=None)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {VALID_FREQUENCIES}")
        if isinstance(self.last_applied, str):
            self.last_applied = date.fromisoformat(self.last_applied)

    def is_due(self, today: date) -> bool:
        if self.last_applied is None:
            return True
        return self.last_applied.year != today.year or self.last_applied.month != today.month

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "category": self.category,
            "frequency": self.frequency,
            "note": self.note,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecurringTransaction":
        return cls(
            amount=float(data["amount"]),
            category=data["category"],
            frequency=data["frequency"],
            note=data.get("note", ""),
            last_applied=data.get("last_applied"),
        )


@dataclass
class BudgetLimit:
    category: str
    amount: float

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        if self.category == "income":
            raise ValueError("budget limits cannot be set on the income category")
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
