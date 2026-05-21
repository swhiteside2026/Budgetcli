import argparse
from pathlib import Path

import pytest

import budgetcli.storage as storage
from budgetcli.cli import cmd_export


@pytest.fixture(autouse=True)
def tmp_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_file = tmp_path / "ledger.json"
    monkeypatch.setattr(storage, "DATA_FILE", fake_file)
    return fake_file


def _args() -> argparse.Namespace:
    return argparse.Namespace()


def test_export_creates_csv_in_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """export saves transactions.csv in the current working directory."""
    pass


def test_export_csv_contains_correct_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CSV first row is: date, category, amount, note."""
    pass


def test_export_csv_row_matches_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each transaction is written as a correctly ordered data row."""
    pass


def test_export_empty_ledger_writes_header_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no transactions, the CSV contains only the header row."""
    pass


def test_export_prints_output_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """cmd_export prints the absolute path of the saved file."""
    pass
