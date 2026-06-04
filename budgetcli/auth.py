import json
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

_DATA_ROOT: Path = Path(__file__).parent.parent / "data"
_ACCOUNTS_FILE: Path = _DATA_ROOT / "accounts.json"

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{2,30}$")


def validate_username(username: str) -> str | None:
    """Returns an error string if invalid, None if valid."""
    if not _USERNAME_RE.match(username):
        return "Username must be 2–30 characters: letters, numbers, _ or -."
    return None


def _load_accounts() -> dict[str, str]:
    if not _ACCOUNTS_FILE.exists():
        return {}
    return json.loads(_ACCOUNTS_FILE.read_text(encoding="utf-8"))


def _save_accounts(accounts: dict[str, str]) -> None:
    _DATA_ROOT.mkdir(parents=True, exist_ok=True)
    _ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2), encoding="utf-8")


def user_exists(username: str) -> bool:
    return username.lower() in _load_accounts()


def create_user(username: str, password: str) -> None:
    accounts = _load_accounts()
    accounts[username.lower()] = generate_password_hash(password)
    _save_accounts(accounts)


def verify_user(username: str, password: str) -> bool:
    accounts = _load_accounts()
    key = username.lower()
    if key not in accounts:
        return False
    return check_password_hash(accounts[key], password)


def change_password(username: str, new_password: str) -> None:
    accounts = _load_accounts()
    accounts[username.lower()] = generate_password_hash(new_password)
    _save_accounts(accounts)


def user_data_path(username: str) -> Path:
    return _DATA_ROOT / "users" / username.lower() / "ledger.json"


def find_user_by_email(email: str) -> str | None:
    """Return the username whose ledger.json has a matching email, or None."""
    if not email:
        return None
    users_dir = _DATA_ROOT / "users"
    if not users_dir.exists():
        return None
    target = email.strip().lower()
    for user_dir in users_dir.iterdir():
        if not user_dir.is_dir():
            continue
        ledger = user_dir / "ledger.json"
        if not ledger.exists():
            continue
        try:
            data = json.loads(ledger.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("email", "").lower() == target:
                return user_dir.name
        except (json.JSONDecodeError, OSError):
            continue
    return None


def find_user_by_reset_token(token: str) -> str | None:
    """Return the username whose ledger.json has this unexpired token, or None."""
    if not token:
        return None
    users_dir = _DATA_ROOT / "users"
    if not users_dir.exists():
        return None
    now = datetime.utcnow()
    for user_dir in users_dir.iterdir():
        if not user_dir.is_dir():
            continue
        ledger = user_dir / "ledger.json"
        if not ledger.exists():
            continue
        try:
            data = json.loads(ledger.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("reset_token") == token:
                expiry_str = data.get("reset_token_expiry", "")
                if expiry_str and now < datetime.fromisoformat(expiry_str):
                    return user_dir.name
        except (json.JSONDecodeError, OSError, ValueError):
            continue
    return None


def generate_reset_token() -> tuple[str, str]:
    """Return (token, expiry_iso) — token valid for 30 minutes (UTC)."""
    token = secrets.token_urlsafe(32)
    expiry_iso = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
    return token, expiry_iso
