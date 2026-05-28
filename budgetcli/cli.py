import argparse
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from budgetcli.models import VALID_CATEGORIES, BudgetLimit, Transaction
from budgetcli.reports import category_breakdown, check_limits, monthly_summary, overall_balance
from budgetcli.storage import (
    add_transaction,
    clear_all,
    export_csv,
    load_limits,
    load_transactions,
    remove_limit,
    set_limit,
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
    print(f"{'Month:':<12} {today.strftime('%B %Y')}")
    print(f"{'Income:':<12} ${income:>10.2f}")
    print(f"{'Expenses:':<12} ${expenses:>10.2f}")
    print(f"{'Net:':<12} ${net:>10.2f}")


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
    recent = transactions[-LIST_LIMIT:]
    if not recent:
        print("No transactions found.")
        return
    for t in recent:
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
        pct = spent / limit * 100
        if spent > limit:
            status = "OVER"
        elif spent >= limit * 0.80:
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
    subparsers.add_parser("list", help="List the last 20 transactions")
    subparsers.add_parser("clear", help="Delete all transactions")
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
        "export": cmd_export,
        "set-limit": cmd_set_limit,
        "limits": cmd_limits,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
