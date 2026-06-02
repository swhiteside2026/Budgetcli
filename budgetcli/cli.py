import argparse
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from .storage import _write_ledger
from budgetcli.models import VALID_CATEGORIES, BudgetLimit, Transaction
from budgetcli.reports import WARN_THRESHOLD, category_breakdown, check_limits, monthly_summary, overall_balance
from budgetcli.storage import (
    add_transaction,
    clear_all,
    delete_transaction,
    export_csv,
    load_limits,
    load_transactions,
    set_limit,
    update_transaction,
)

LIST_LIMIT = 20


def cmd_add(args: argparse.Namespace) -> None:
    # TODO: support temporary limit suspension per category
    try:
        t = Transaction(
            amount=args.amount,
            category=args.category,
            date=date.today(),
            note=args.note or "",
        )
        add_transaction(t)
        print(f"Added: {args.category} ${args.amount:.2f}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    limits = load_limits()
    if args.category in limits:
        today = date.today()
        totals = category_breakdown(load_transactions(), today.year, today.month)
        for warning in check_limits(totals, {args.category: limits[args.category]}):
            print(warning, file=sys.stderr)


def cmd_summary(args: argparse.Namespace) -> None:
    today = date.today()
    transactions = load_transactions()
    income, expenses, net = monthly_summary(transactions, today.year, today.month)
    breakdown = category_breakdown(transactions, today.year, today.month)
    print(f"{'Month:':<12} {today.strftime('%B %Y')}")
    print(f"{'Income:':<12} +${income:>9.2f}")
    print(f"{'Expenses:':<12} -${expenses:>9.2f}")
    print(f"{'Net:':<12}  ${net:>9.2f}")
    if breakdown:
        top_cat, top_amt = next(iter(breakdown.items()))
        print(f"{'Top spend:':<12}  {top_cat} ${top_amt:.2f}")
    else:
        print(f"{'Top spend:':<12}  none")


def cmd_report(args: argparse.Namespace) -> None:
    today = date.today()
    transactions = load_transactions()
    breakdown = category_breakdown(transactions, today.year, today.month)
    balance = overall_balance(transactions)

    print(f"Spending by category — {today.strftime('%B %Y')}")
    print("-" * 30)
    if breakdown:
        for category, total in breakdown.items():
            print(f"  {category:<16} ${total:>8.2f}")
    else:
        print("  No expenses this month.")
    print("-" * 30)
    print(f"  {'Overall balance':<16} ${balance:>8.2f}")


def cmd_list(args: argparse.Namespace) -> None:
    transactions = load_transactions()

    if args.month:
        try:
            year, month = args.month.split("-")
            year_int, month_int = int(year), int(month)
        except ValueError:
            print("Error: --month must be in YYYY-MM format (e.g. 2026-05)")
            sys.exit(1)
        to_show = [t for t in transactions if t.date.year == year_int and t.date.month == month_int]
    else:
        to_show = transactions[-LIST_LIMIT:]

    if not to_show:
        print("No transactions found.")
        return
    for t in to_show:
        sign = "+" if t.is_income else "-"
        note_str = f"  {t.note}" if t.note else ""
        print(f"{t.date}  {sign}${t.amount:<10.2f}  {t.category:<16}{note_str}")


def cmd_clear(args: argparse.Namespace, confirm: str | None = None) -> None:
    if confirm is None:
        confirm = input('Type "yes" to delete all transactions: ')
    if confirm.strip().lower() == "yes":
        clear_all()
        print("All transactions cleared.")
    else:
        print("Cancelled.")

def cmd_delete(args: argparse.Namespace, confirm: str | None = None) -> None:
    transactions = load_transactions()

    if not transactions:
        print("No transactions to delete.")
        return

    print("Transactions:")
    for i, t in enumerate(transactions, start=1):
        print(f"  {i}. {t.date} {t.category} ${t.amount:.2f} {t.note}")

    if confirm is None:
        confirm = input('Enter the number of the transaction to delete (or "cancel"): ')

    if confirm.strip().lower() == "cancel":
        print("Cancelled.")
        return

    try:
        index = int(confirm.strip()) - 1
        if 0 <= index < len(transactions):
            delete_transaction(index)
            print(f"Transaction {index + 1} deleted.")
        else:
            print(f"Invalid number. Please enter a number between 1 and {len(transactions)}.")
    except ValueError:
        print("Invalid input. Please enter a number or 'cancel'.")


def cmd_edit(args: argparse.Namespace) -> None:
    transactions = load_transactions()

    if not transactions:
        print("No transactions to edit.")
        return

    print("Transactions:")
    for i, t in enumerate(transactions, start=1):
        print(f"  {i}. {t.date} {t.category} ${t.amount:.2f} {t.note}")

    selection = input('Enter the number of the transaction to edit (or "cancel"): ')
    if selection.strip().lower() == "cancel":
        print("Cancelled.")
        return

    try:
        index = int(selection.strip()) - 1
    except ValueError:
        print("Invalid input. Please enter a number or 'cancel'.")
        return

    if not (0 <= index < len(transactions)):
        print(f"Invalid number. Please enter a number between 1 and {len(transactions)}.")
        return

    t = transactions[index]
    raw_amount = input(f"Amount [{t.amount:.2f}]: ").strip()
    raw_category = input(f"Category [{t.category}]: ").strip()
    raw_note = input(f"Note [{t.note}]: ").strip()

    try:
        amount = float(raw_amount) if raw_amount else t.amount
        category = raw_category if raw_category else t.category
        note = raw_note if raw_note else t.note
        updated = Transaction(amount=amount, category=category, date=t.date, note=note)
    except ValueError as e:
        print(f"Error: {e}")
        return

    update_transaction(index, updated)
    print(f"Transaction {index + 1} updated.")


def cmd_set_limit(args: argparse.Namespace) -> None:
    try:
        BudgetLimit(category=args.category, amount=args.amount)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    set_limit(args.category, args.amount)
    print(f"Limit set: {args.category} ${args.amount:.2f}/month")


def cmd_limits(args: argparse.Namespace) -> None:
    # TODO: improve formatting (alignment, color) once a formatting helper exists
    today = date.today()
    limits = load_limits()
    if not limits:
        print("No limits set. Use 'budget set-limit <category> <amount>' to add one.")
        return
    transactions = load_transactions()
    totals = category_breakdown(transactions, today.year, today.month)
    print(f"Budget limits — {today.strftime('%B %Y')}")
    print("-" * 44)
    for category, limit in sorted(limits.items()):
        spent = totals.get(category, 0.0)
        if spent > limit:
            status = "OVER"
        elif spent >= limit * WARN_THRESHOLD:
            status = "NEAR"
        else:
            status = "ok"
        print(f"  {category:<16} ${spent:>7.2f} / ${limit:<9.2f} {status}")
    print("-" * 44)


def cmd_export(args: argparse.Namespace) -> None:
    """Export all transactions to transactions.csv in the current directory.

    Loads all transactions, writes them to CSV, and prints the absolute path
    of the saved file so the user knows where to find it.
    """
    path = Path("transactions.csv").resolve()
    export_csv(path)
    print(f"Exported to {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget", description="Personal budget tracker")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('budgetcli')}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a transaction")
    add_parser.add_argument("amount", type=float, help="Transaction amount")
    add_parser.add_argument(
        "category", choices=VALID_CATEGORIES, help="Transaction category"
    )
    add_parser.add_argument("--note", type=str, default="", help="Optional note")

    subparsers.add_parser("summary", help="Show this month's income, expenses and net")
    subparsers.add_parser("report", help="Show spending breakdown by category")
    list_parser = subparsers.add_parser("list", help="List the last 20 transactions")
    list_parser.add_argument("--month", type=str, default=None, metavar="YYYY-MM", help="Show only transactions from this month")
    subparsers.add_parser("clear", help="Delete all transactions")
    subparsers.add_parser("delete", help="Delete a single transaction")
    subparsers.add_parser("edit", help="Edit an existing transaction")
    subparsers.add_parser("export", help="Export all transactions to transactions.csv")

    set_limit_parser = subparsers.add_parser("set-limit", help="Set a monthly spending limit for a category")
    set_limit_parser.add_argument("category", choices=VALID_CATEGORIES, help="Category to limit")
    set_limit_parser.add_argument("amount", type=float, help="Monthly spending limit")

    subparsers.add_parser("limits", help="Show all budget limits and current month spend")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    commands = {
        "add": cmd_add,
        "summary": cmd_summary,
        "report": cmd_report,
        "list": cmd_list,
        "clear": cmd_clear,
        "delete": cmd_delete,
        "edit": cmd_edit,
        "export": cmd_export,
        "set-limit": cmd_set_limit,
        "limits": cmd_limits,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
