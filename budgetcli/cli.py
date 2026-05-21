import argparse
import sys
from datetime import date

from budgetcli.models import VALID_CATEGORIES, Transaction
from budgetcli.reports import category_breakdown, monthly_summary, overall_balance
from budgetcli.storage import add_transaction, clear_all, load_transactions


def cmd_add(args: argparse.Namespace) -> None:
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
    recent = transactions[-20:]
    if not recent:
        print("No transactions found.")
        return
    for t in recent:
        sign = "+" if t.is_income else "-"
        note_str = f"  {t.note}" if t.note else ""
        print(f"{t.date}  {sign}${t.amount:<10.2f}  {t.category:<16}{note_str}")


def cmd_clear(args: argparse.Namespace) -> None:
    confirm = input('Type "yes" to delete all transactions: ')
    if confirm.strip().lower() == "yes":
        clear_all()
        print("All transactions cleared.")
    else:
        print("Cancelled.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget", description="Personal budget tracker")
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

    return parser


def main() -> None:
    args = build_parser().parse_args()

    commands = {
        "add": cmd_add,
        "summary": cmd_summary,
        "report": cmd_report,
        "list": cmd_list,
        "clear": cmd_clear,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
