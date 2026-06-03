import json
import re
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


def user_data_path(username: str) -> Path:
    return _DATA_ROOT / "users" / username.lower() / "ledger.json"
