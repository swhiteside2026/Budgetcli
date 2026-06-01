import argparse
import csv
import subprocess
from datetime import date
from pathlib import Path

import pytest

import budgetcli.storage as storage
from budgetcli.cli import cmd_add, cmd_export, cmd_limits, cmd_set_limit
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
