import csv
import json
import secrets
from datetime import date, datetime
from pathlib import Path

from budgetcli.models import RecurringTransaction, Transaction

DATA_FILE: Path = Path(__file__).parent.parent / "data" / "ledger.json"

_BUILTIN_CATS: frozenset[str] = frozenset({
    "income", "food", "transport", "rent", "utilities",
    "entertainment", "health", "investment", "hysa", "other",
})


# ── private helpers (path=None → use DATA_FILE at call time, so monkeypatch works) ──

def _ensure_data_file(path: Path | None = None) -> None:
    p = path if path is not None else DATA_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(
            json.dumps({"transactions": [], "limits": {}, "recurring": []}),
            encoding="utf-8",
        )


def _read_ledger(path: Path | None = None) -> tuple[list[dict], dict[str, float], list[dict]]:
    p = path if path is not None else DATA_FILE
    _ensure_data_file(p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw, {}, []
    return raw.get("transactions", []), raw.get("limits", {}), raw.get("recurring", [])


def _write_ledger(
    transactions: list[dict],
    limits: dict[str, float],
    recurring: list[dict],
    path: Path | None = None,
) -> None:
    p = path if path is not None else DATA_FILE
    _ensure_data_file(p)
    try:
        existing = json.loads(p.read_text(encoding="utf-8"))
        raw: dict = existing if isinstance(existing, dict) else {}
    except (json.JSONDecodeError, FileNotFoundError):
        raw = {}
    raw.update({"transactions": transactions, "limits": limits, "recurring": recurring})
    p.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def _read_raw(path: Path | None = None) -> dict:
    p = path if path is not None else DATA_FILE
    _ensure_data_file(p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {"transactions": raw, "limits": {}, "recurring": []}


# ── module-level functions (CLI public API, unchanged signatures) ──

def load_transactions() -> list[Transaction]:
    raw_transactions, _, _ = _read_ledger()
    return [Transaction.from_dict(item) for item in raw_transactions]


def load_limits() -> dict[str, float]:
    _, limits, _ = _read_ledger()
    return limits


def set_limit(category: str, amount: float) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    limits[category] = amount
    _write_ledger(raw_transactions, limits, recurring)


def remove_limit(category: str) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    limits.pop(category, None)
    _write_ledger(raw_transactions, limits, recurring)


def add_transaction(transaction: Transaction) -> None:
    p = DATA_FILE
    raw = _read_raw(p)
    cats: list[str] = raw.get("custom_categories", [])
    if transaction.category.lower() not in _BUILTIN_CATS | {c.lower() for c in cats}:
        cats.append(transaction.category)
        raw["custom_categories"] = cats
    txns: list[dict] = raw.get("transactions", [])
    txns.append(transaction.to_dict())
    raw["transactions"] = txns
    p.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def clear_all() -> None:
    _, limits, recurring = _read_ledger()
    _write_ledger([], limits, recurring)


def delete_transaction(index: int) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    raw_transactions.pop(index)
    _write_ledger(raw_transactions, limits, recurring)


def update_transaction(index: int, transaction: Transaction) -> None:
    raw_transactions, limits, recurring = _read_ledger()
    raw_transactions[index] = transaction.to_dict()
    _write_ledger(raw_transactions, limits, recurring)


def load_recurring() -> list[RecurringTransaction]:
    _, _, raw_recurring = _read_ledger()
    return [RecurringTransaction.from_dict(r) for r in raw_recurring]


def add_recurring(rt: RecurringTransaction) -> None:
    raw_transactions, limits, raw_recurring = _read_ledger()
    raw_recurring.append(rt.to_dict())
    _write_ledger(raw_transactions, limits, raw_recurring)


def save_recurring(recurring: list[RecurringTransaction]) -> None:
    raw_transactions, limits, _ = _read_ledger()
    _write_ledger(raw_transactions, limits, [r.to_dict() for r in recurring])


def load_custom_categories() -> list[str]:
    return _read_raw().get("custom_categories", [])


def add_custom_category(name: str) -> None:
    p = DATA_FILE
    raw = _read_raw(p)
    cats: list[str] = raw.get("custom_categories", [])
    if name not in cats:
        cats.append(name)
    raw["custom_categories"] = cats
    p.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def remove_custom_category(name: str) -> None:
    p = DATA_FILE
    raw = _read_raw(p)
    cats: list[str] = raw.get("custom_categories", [])
    if name in cats:
        cats.remove(name)
    raw["custom_categories"] = cats
    p.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def export_csv(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
) -> None:
    """Export transactions to a CSV file at the given path.

    Writes a header row (date, category, amount, note) followed by one row
    per transaction. Overwrites the file if it already exists.
    from_date and to_date are inclusive bounds; omit either to leave that end open.
    """
    transactions = load_transactions()
    if from_date is not None:
        transactions = [t for t in transactions if t.date >= from_date]
    if to_date is not None:
        transactions = [t for t in transactions if t.date <= to_date]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "category", "amount", "note"])
        for t in transactions:
            writer.writerow([t.date.isoformat(), t.category, round(t.amount, 2), t.note])


# ── Storage class (per-user data paths for the web app) ──

class Storage:
    """Wraps ledger I/O for a specific file path (one instance per authenticated user)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load_transactions(self) -> list[Transaction]:
        raw_txns, _, _ = _read_ledger(self._path)
        return [Transaction.from_dict(item) for item in raw_txns]

    def load_limits(self) -> dict[str, float]:
        _, limits, _ = _read_ledger(self._path)
        return limits

    def set_limit(self, category: str, amount: float) -> None:
        raw_txns, limits, recurring = _read_ledger(self._path)
        limits[category] = amount
        _write_ledger(raw_txns, limits, recurring, self._path)

    def remove_limit(self, category: str) -> None:
        raw_txns, limits, recurring = _read_ledger(self._path)
        limits.pop(category, None)
        _write_ledger(raw_txns, limits, recurring, self._path)

    def add_transaction(self, transaction: Transaction) -> None:
        raw = _read_raw(self._path)
        cats: list[str] = raw.get("custom_categories", [])
        if transaction.category.lower() not in _BUILTIN_CATS | {c.lower() for c in cats}:
            cats.append(transaction.category)
            raw["custom_categories"] = cats
        txns: list[dict] = raw.get("transactions", [])
        txns.append(transaction.to_dict())
        raw["transactions"] = txns
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def delete_transaction(self, index: int) -> None:
        raw_txns, limits, recurring = _read_ledger(self._path)
        raw_txns.pop(index)
        _write_ledger(raw_txns, limits, recurring, self._path)

    def update_transaction(self, index: int, transaction: Transaction) -> None:
        raw_txns, limits, recurring = _read_ledger(self._path)
        raw_txns[index] = transaction.to_dict()
        _write_ledger(raw_txns, limits, recurring, self._path)

    def load_recurring(self) -> list[RecurringTransaction]:
        _, _, raw_recurring = _read_ledger(self._path)
        return [RecurringTransaction.from_dict(r) for r in raw_recurring]

    def add_recurring(self, rt: RecurringTransaction) -> None:
        raw_txns, limits, raw_recurring = _read_ledger(self._path)
        raw_recurring.append(rt.to_dict())
        _write_ledger(raw_txns, limits, raw_recurring, self._path)

    def save_recurring(self, recurring: list[RecurringTransaction]) -> None:
        raw_txns, limits, _ = _read_ledger(self._path)
        _write_ledger(raw_txns, limits, [r.to_dict() for r in recurring], self._path)

    def load_custom_categories(self) -> list[str]:
        return _read_raw(self._path).get("custom_categories", [])

    def add_custom_category(self, name: str) -> None:
        raw = _read_raw(self._path)
        cats: list[str] = raw.get("custom_categories", [])
        if name not in cats:
            cats.append(name)
        raw["custom_categories"] = cats
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def remove_custom_category(self, name: str) -> None:
        raw = _read_raw(self._path)
        cats: list[str] = raw.get("custom_categories", [])
        if name in cats:
            cats.remove(name)
        raw["custom_categories"] = cats
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def load_suppressed_categories(self) -> list[str]:
        """Return built-in category names that have been renamed and should be hidden."""
        return _read_raw(self._path).get("suppressed_categories", [])

    def rename_category(self, old_name: str, new_name: str, *, suppress_old: bool = False) -> int:
        """Cascade-rename a category across all data in a single atomic read/write.

        suppress_old=True when the old name is a built-in: adds it to the
        suppressed list so _all_categories() filters it out after a restart,
        and ensures new_name is stored in custom_categories for persistence.

        Returns the number of transactions whose category was updated.
        """
        old_lower = old_name.lower()
        raw = _read_raw(self._path)

        # transactions
        count = 0
        for t in raw.get("transactions", []):
            if t.get("category", "").lower() == old_lower:
                t["category"] = new_name
                count += 1

        # limits — rebuild dict preserving insertion order for other keys
        raw["limits"] = {
            (new_name if k.lower() == old_lower else k): v
            for k, v in raw.get("limits", {}).items()
        }

        # recurring transactions
        for r in raw.get("recurring", []):
            if r.get("category", "").lower() == old_lower:
                r["category"] = new_name

        # custom_categories list
        cats: list[str] = raw.get("custom_categories", [])
        raw["custom_categories"] = [new_name if c.lower() == old_lower else c for c in cats]

        if suppress_old:
            suppressed: list[str] = raw.get("suppressed_categories", [])
            if old_lower not in {s.lower() for s in suppressed}:
                suppressed.append(old_name)
            raw["suppressed_categories"] = suppressed
            # Ensure new_name persists in custom after a server restart
            new_cats: list[str] = raw["custom_categories"]
            if new_name.lower() not in {c.lower() for c in new_cats}:
                new_cats.append(new_name)

        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return count

    def load_profile(self) -> dict:
        raw = _read_raw(self._path)
        return {
            "display_name": raw.get("display_name", ""),
            "email": raw.get("email", ""),
            "phone": raw.get("phone", ""),
            "default_theme": raw.get("default_theme", ""),
        }

    def save_profile(self, profile: dict) -> None:
        raw = _read_raw(self._path)
        raw.update(profile)
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def save_reset_token(self, token: str, expiry_iso: str) -> None:
        raw = _read_raw(self._path)
        raw["reset_token"] = token
        raw["reset_token_expiry"] = expiry_iso
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def clear_reset_token(self) -> None:
        raw = _read_raw(self._path)
        raw.pop("reset_token", None)
        raw.pop("reset_token_expiry", None)
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def load_alert_threshold(self) -> int:
        return int(_read_raw(self._path).get("alert_threshold", 80))

    def save_alert_threshold(self, threshold: int) -> None:
        raw = _read_raw(self._path)
        raw["alert_threshold"] = threshold
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def load_notifications(self) -> list[dict]:
        return _read_raw(self._path).get("notifications", [])

    def save_notifications(self, notifications: list[dict]) -> None:
        raw = _read_raw(self._path)
        raw["notifications"] = notifications
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def add_notification(self, message: str, notif_type: str, category: str = "") -> dict | None:
        """Append a notification, deduplicating against existing unread ones for the same category.

        Returns the new notification dict if it was inserted, or None if it was suppressed by
        the dedup logic (so callers can tell whether something actually fired).
        """
        raw = _read_raw(self._path)
        notifications = raw.get("notifications", [])
        if category:
            for n in notifications:
                if n.get("read") or n.get("category") != category:
                    continue
                n_type = n.get("type", "")
                if notif_type == "near" and n_type in ("near", "over"):
                    return None
                if notif_type == "over" and n_type == "over":
                    return None
        new_notif = {
            "id": secrets.token_hex(8),
            "message": message,
            "type": notif_type,
            "category": category,
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        notifications.insert(0, new_notif)
        raw["notifications"] = notifications[:50]
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return new_notif

    def mark_all_read(self) -> None:
        raw = _read_raw(self._path)
        for n in raw.get("notifications", []):
            n["read"] = True
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def delete_notification(self, notif_id: str) -> None:
        raw = _read_raw(self._path)
        raw["notifications"] = [n for n in raw.get("notifications", []) if n.get("id") != notif_id]
        self._path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
