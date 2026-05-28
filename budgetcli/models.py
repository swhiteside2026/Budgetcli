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
        if self.amount == 0:
            raise ValueError("amount must not be zero")
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


@dataclass
class BudgetLimit:
    category: str
    amount: float

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
