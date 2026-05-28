import argparse
import csv
import subprocess
from datetime import date
from pathlib import Path

import pytest

import budgetcli.storage as storage
from budgetcli.cli import cmd_export
from budgetcli.models import Transaction


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
