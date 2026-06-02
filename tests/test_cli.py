import argparse
import csv
import subprocess
from datetime import date
from pathlib import Path

import pytest

import budgetcli.storage as storage
from budgetcli.cli import (
    cmd_add, cmd_edit, cmd_export, cmd_help, cmd_limits, cmd_list,
    cmd_recurring_add, cmd_recurring_apply, cmd_recurring_list,
    cmd_set_limit, cmd_summary,
)
from budgetcli.models import Transaction
from unittest.mock import patch


@pytest.fixture(autouse=True)
def tmp_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_file = tmp_path / "ledger.json"
    monkeypatch.setattr(storage, "DATA_FILE", fake_file)
    return fake_file


def _args() -> argparse.Namespace:
    return argparse.Namespace()


def test_export_creates_csv_in_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cmd_export(_args())
    assert (tmp_path / "transactions.csv").exists()


def test_export_csv_contains_correct_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cmd_export(_args())
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["date", "category", "amount", "note"]


def test_export_csv_row_matches_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    t = Transaction(amount=99.99, category="transport", date=date(2026, 5, 10), note="train")
    storage.add_transaction(t)
    cmd_export(_args())
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1] == ["2026-05-10", "transport", "99.99", "train"]


def test_export_empty_ledger_writes_header_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cmd_export(_args())
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1


def test_export_prints_output_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.chdir(tmp_path)
    cmd_export(_args())
    output = capsys.readouterr().out
    expected = str((tmp_path / "transactions.csv").resolve())
    assert expected in output


# --- export --from / --to tests ---

def test_export_from_filters_earlier_transactions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 4, 30)))
    storage.add_transaction(Transaction(amount=20.0, category="food", date=date(2026, 5, 1)))
    cmd_export(argparse.Namespace(from_date="2026-05-01", to_date=None))
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2  # header + 1 row
    assert rows[1][0] == "2026-05-01"


def test_export_to_filters_later_transactions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 31)))
    storage.add_transaction(Transaction(amount=20.0, category="food", date=date(2026, 6, 1)))
    cmd_export(argparse.Namespace(from_date=None, to_date="2026-05-31"))
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2
    assert rows[1][0] == "2026-05-31"


def test_export_from_and_to_together(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    storage.add_transaction(Transaction(amount=5.0, category="food", date=date(2026, 4, 30)))
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 15)))
    storage.add_transaction(Transaction(amount=15.0, category="food", date=date(2026, 6, 1)))
    cmd_export(argparse.Namespace(from_date="2026-05-01", to_date="2026-05-31"))
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2
    assert rows[1][0] == "2026-05-15"


def test_export_date_bounds_are_inclusive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 1)))
    storage.add_transaction(Transaction(amount=20.0, category="food", date=date(2026, 5, 31)))
    cmd_export(argparse.Namespace(from_date="2026-05-01", to_date="2026-05-31"))
    with open(tmp_path / "transactions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3  # header + 2 rows


def test_export_invalid_from_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cmd_export(argparse.Namespace(from_date="05-2026-01", to_date=None))
    assert exc.value.code == 1
    assert "YYYY-MM-DD" in capsys.readouterr().out


def test_export_invalid_to_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cmd_export(argparse.Namespace(from_date=None, to_date="not-a-date"))
    assert exc.value.code == 1
    assert "YYYY-MM-DD" in capsys.readouterr().out


def test_version_flag() -> None:
    result = subprocess.run(
        ["python", "-m", "budgetcli.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "budget 0.1.0" in result.stdout + result.stderr


# --- set-limit tests ---

def test_set_limit_prints_confirmation(capsys: pytest.CaptureFixture) -> None:
    args = argparse.Namespace(category="food", amount=300.0)
    cmd_set_limit(args)
    out = capsys.readouterr().out
    assert "food" in out
    assert "300.00" in out


def test_set_limit_persists(capsys: pytest.CaptureFixture) -> None:
    args = argparse.Namespace(category="food", amount=300.0)
    cmd_set_limit(args)
    assert storage.load_limits() == {"food": 300.0}


def test_set_limit_invalid_amount_exits(capsys: pytest.CaptureFixture) -> None:
    args = argparse.Namespace(category="food", amount=-50.0)
    with pytest.raises(SystemExit) as exc:
        cmd_set_limit(args)
    assert exc.value.code == 1


# --- limits command tests ---

def test_limits_shows_no_limits_message(capsys: pytest.CaptureFixture) -> None:
    cmd_limits(_args())
    out = capsys.readouterr().out
    assert "No limits set" in out


def test_limits_shows_category_and_spend(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 300.0)
    cmd_limits(_args())
    out = capsys.readouterr().out
    assert "food" in out
    assert "300.00" in out


def test_limits_status_ok(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 300.0)
    # No transactions — 0% spent
    cmd_limits(_args())
    out = capsys.readouterr().out
    assert "ok" in out


def test_limits_status_near(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 100.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        storage.add_transaction(Transaction(amount=85.0, category="food", date=date(2026, 5, 1)))
        cmd_limits(_args())
    out = capsys.readouterr().out
    assert "NEAR" in out


def test_limits_status_over(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 100.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        storage.add_transaction(Transaction(amount=110.0, category="food", date=date(2026, 5, 1)))
        cmd_limits(_args())
    out = capsys.readouterr().out
    assert "OVER" in out


# --- cmd_add warning tests ---

def test_add_warning_to_stderr_when_near_limit(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 100.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        args = argparse.Namespace(amount=85.0, category="food", note="")
        cmd_add(args)
    assert "Warning" in capsys.readouterr().err


def test_add_warning_to_stderr_when_over_limit(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 100.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        args = argparse.Namespace(amount=110.0, category="food", note="")
        cmd_add(args)
    assert "Warning" in capsys.readouterr().err


def test_add_warning_not_on_stdout(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 100.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        args = argparse.Namespace(amount=85.0, category="food", note="")
        cmd_add(args)
    captured = capsys.readouterr()
    assert "Warning" not in captured.out


def test_add_no_warning_when_under_threshold(capsys: pytest.CaptureFixture) -> None:
    storage.set_limit("food", 300.0)
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        args = argparse.Namespace(amount=50.0, category="food", note="")
        cmd_add(args)
    assert capsys.readouterr().err == ""


def test_add_no_warning_when_no_limit_set(capsys: pytest.CaptureFixture) -> None:
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 28)
        args = argparse.Namespace(amount=50.0, category="food", note="")
        cmd_add(args)
    assert capsys.readouterr().err == ""


# --- cmd_edit tests ---

def _add_transaction(amount: float, category: str, note: str = "") -> None:
    storage.add_transaction(Transaction(amount=amount, category=category, date=date(2026, 5, 1), note=note))


def test_edit_no_transactions_prints_message(capsys: pytest.CaptureFixture) -> None:
    cmd_edit(_args())
    assert "No transactions to edit" in capsys.readouterr().out


def test_edit_cancel_aborts(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food", "lunch")
    with patch("builtins.input", return_value="cancel"):
        cmd_edit(_args())
    assert "Cancelled" in capsys.readouterr().out
    assert storage.load_transactions()[0].amount == 10.0


def test_edit_invalid_selection_non_numeric(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food")
    with patch("builtins.input", return_value="abc"):
        cmd_edit(_args())
    assert "Invalid input" in capsys.readouterr().out


def test_edit_invalid_selection_out_of_range(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food")
    with patch("builtins.input", return_value="99"):
        cmd_edit(_args())
    assert "Invalid number" in capsys.readouterr().out


def test_edit_updates_all_fields(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food", "lunch")
    with patch("builtins.input", side_effect=["1", "25.00", "transport", "taxi"]):
        cmd_edit(_args())
    t = storage.load_transactions()[0]
    assert t.amount == 25.0
    assert t.category == "transport"
    assert t.note == "taxi"
    assert "updated" in capsys.readouterr().out


def test_edit_keeps_originals_on_empty_input(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food", "lunch")
    with patch("builtins.input", side_effect=["1", "", "", ""]):
        cmd_edit(_args())
    t = storage.load_transactions()[0]
    assert t.amount == 10.0
    assert t.category == "food"
    assert t.note == "lunch"


def test_edit_preserves_original_date(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food")
    with patch("builtins.input", side_effect=["1", "20.0", "", ""]):
        cmd_edit(_args())
    assert storage.load_transactions()[0].date == date(2026, 5, 1)


def test_edit_invalid_amount_prints_error(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food")
    with patch("builtins.input", side_effect=["1", "notanumber", "", ""]):
        cmd_edit(_args())
    assert "Error" in capsys.readouterr().out
    assert storage.load_transactions()[0].amount == 10.0


def test_edit_invalid_category_prints_error(capsys: pytest.CaptureFixture) -> None:
    _add_transaction(10.0, "food")
    with patch("builtins.input", side_effect=["1", "", "invalidcat", ""]):
        cmd_edit(_args())
    assert "Error" in capsys.readouterr().out
    assert storage.load_transactions()[0].category == "food"


# --- cmd_list --month tests ---

def test_list_month_shows_only_matching_transactions(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 1)))
    storage.add_transaction(Transaction(amount=20.0, category="food", date=date(2026, 6, 1)))
    cmd_list(argparse.Namespace(month="2026-05"))
    out = capsys.readouterr().out
    assert "2026-05-01" in out
    assert "2026-06-01" not in out


def test_list_month_empty_result(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 1)))
    cmd_list(argparse.Namespace(month="2026-04"))
    assert "No transactions found" in capsys.readouterr().out


def test_list_no_month_returns_recent(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=10.0, category="food", date=date(2026, 5, 1)))
    storage.add_transaction(Transaction(amount=20.0, category="food", date=date(2026, 6, 1)))
    cmd_list(argparse.Namespace(month=None))
    out = capsys.readouterr().out
    assert "2026-05-01" in out
    assert "2026-06-01" in out


def test_list_month_invalid_format_exits(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_list(argparse.Namespace(month="may-2026"))
    assert exc.value.code == 1
    assert "YYYY-MM" in capsys.readouterr().out


# --- cmd_summary tests ---

def test_summary_income_has_plus_sign(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=1000.0, category="income", date=date(2026, 5, 1)))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 1)
        cmd_summary(_args())
    assert "+$" in capsys.readouterr().out


def test_summary_expenses_has_minus_sign(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=50.0, category="food", date=date(2026, 5, 1)))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 1)
        cmd_summary(_args())
    assert "-$" in capsys.readouterr().out


def test_summary_top_spend_shows_highest_category(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=200.0, category="rent", date=date(2026, 5, 1)))
    storage.add_transaction(Transaction(amount=50.0, category="food", date=date(2026, 5, 1)))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 1)
        cmd_summary(_args())
    assert "rent" in capsys.readouterr().out


def test_summary_top_spend_none_when_no_expenses(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=1000.0, category="income", date=date(2026, 5, 1)))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 1)
        cmd_summary(_args())
    assert "none" in capsys.readouterr().out


def test_summary_net_line_present(capsys: pytest.CaptureFixture) -> None:
    storage.add_transaction(Transaction(amount=1000.0, category="income", date=date(2026, 5, 1)))
    storage.add_transaction(Transaction(amount=200.0, category="food", date=date(2026, 5, 1)))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 1)
        cmd_summary(_args())
    assert "Net" in capsys.readouterr().out


# --- cmd_help tests ---

def test_help_prints_header(capsys: pytest.CaptureFixture) -> None:
    cmd_help(_args())
    assert "budget" in capsys.readouterr().out


def test_help_contains_all_commands(capsys: pytest.CaptureFixture) -> None:
    cmd_help(_args())
    out = capsys.readouterr().out
    for command in ("add", "summary", "report", "list", "delete", "edit", "clear", "export", "recurring", "set-limit", "limits", "help"):
        assert command in out


def test_help_contains_examples(capsys: pytest.CaptureFixture) -> None:
    cmd_help(_args())
    assert "Example:" in capsys.readouterr().out


def test_help_shows_flags(capsys: pytest.CaptureFixture) -> None:
    cmd_help(_args())
    out = capsys.readouterr().out
    assert "--month" in out
    assert "--from" in out
    assert "--to" in out


# --- recurring command tests ---

def _recurring_args(**kwargs) -> argparse.Namespace:
    defaults = {"amount": 100.0, "category": "food", "note": "", "frequency": "monthly"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_recurring_add_prints_confirmation(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=1200.0, category="rent"))
    out = capsys.readouterr().out
    assert "rent" in out
    assert "1200.00" in out


def test_recurring_add_persists(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food", note="lunch"))
    loaded = storage.load_recurring()
    assert len(loaded) == 1
    assert loaded[0].amount == 50.0
    assert loaded[0].note == "lunch"


def test_recurring_add_invalid_amount_exits(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_recurring_add(_recurring_args(amount=-10.0))
    assert exc.value.code == 1


def test_recurring_add_invalid_category_exits(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc:
        cmd_recurring_add(_recurring_args(category="nonsense"))
    assert exc.value.code == 1


def test_recurring_list_empty(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_list(_args())
    assert "No recurring" in capsys.readouterr().out


def test_recurring_list_shows_entries(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=1200.0, category="rent", note="Rent"))
    cmd_recurring_list(_args())
    out = capsys.readouterr().out
    assert "rent" in out
    assert "1200.00" in out
    assert "monthly" in out


def test_recurring_list_due_status(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args())
    cmd_recurring_list(_args())
    assert "due" in capsys.readouterr().out


def test_recurring_apply_adds_transaction(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food"))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.fromisoformat = date.fromisoformat
        cmd_recurring_apply(_args())
    assert len(storage.load_transactions()) == 1
    assert storage.load_transactions()[0].amount == 50.0


def test_recurring_apply_updates_last_applied(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food"))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.fromisoformat = date.fromisoformat
        cmd_recurring_apply(_args())
    assert storage.load_recurring()[0].last_applied == date(2026, 6, 1)


def test_recurring_apply_skips_already_applied(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food"))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.fromisoformat = date.fromisoformat
        cmd_recurring_apply(_args())
        cmd_recurring_apply(_args())
    assert len(storage.load_transactions()) == 1


def test_recurring_apply_no_due_message(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food"))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.fromisoformat = date.fromisoformat
        cmd_recurring_apply(_args())
        capsys.readouterr()
        cmd_recurring_apply(_args())
    assert "No recurring transactions due" in capsys.readouterr().out


def test_recurring_apply_prints_count(capsys: pytest.CaptureFixture) -> None:
    cmd_recurring_add(_recurring_args(amount=50.0, category="food"))
    cmd_recurring_add(_recurring_args(amount=1200.0, category="rent"))
    with patch("budgetcli.cli.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.fromisoformat = date.fromisoformat
        cmd_recurring_apply(_args())
    out = capsys.readouterr().out
    assert "2 transaction(s) applied" in out
