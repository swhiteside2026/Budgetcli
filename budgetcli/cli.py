import argparse
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .storage import _write_ledger
from budgetcli.models import VALID_CATEGORIES, VALID_FREQUENCIES, BudgetLimit, RecurringTransaction, Transaction
from budgetcli.reports import WARN_THRESHOLD, category_breakdown, check_limits, monthly_summary, overall_balance

console = Console(highlight=False)
from budgetcli.storage import (
    add_recurring,
    add_transaction,
    clear_all,
    delete_transaction,
    export_csv,
    load_limits,
    load_recurring,
    load_transactions,
    save_recurring,
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
        err_console = Console(file=sys.stderr, highlight=False)
        for warning in check_limits(totals, {args.category: limits[args.category]}):
            style = "bold red" if "over" in warning.lower() else "bold yellow"
            err_console.print(warning, style=style)


def cmd_summary(args: argparse.Namespace) -> None:
    today = date.today()
    transactions = load_transactions()
    income, expenses, net = monthly_summary(transactions, today.year, today.month)
    breakdown = category_breakdown(transactions, today.year, today.month)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold", min_width=12)
    table.add_column(justify="right", min_width=12)

    table.add_row("Month", today.strftime("%B %Y"))
    table.add_row("Income", Text(f"+${income:.2f}", style="green"))
    table.add_row("Expenses", f"-${expenses:.2f}")
    net_sign = "+" if net >= 0 else "-"
    table.add_row("Net", Text(f"{net_sign}${abs(net):.2f}", style="green" if net >= 0 else "red"))
    if breakdown:
        top_cat, top_amt = next(iter(breakdown.items()))
        table.add_row("Top spend", f"{top_cat} ${top_amt:.2f}")
    else:
        table.add_row("Top spend", "none")

    console.print(table)


def cmd_report(args: argparse.Namespace) -> None:
    today = date.today()
    transactions = load_transactions()
    breakdown = category_breakdown(transactions, today.year, today.month)
    balance = overall_balance(transactions)

    console.print(f"Spending by category — {today.strftime('%B %Y')}", style="bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(min_width=18)
    table.add_column(justify="right")
    if breakdown:
        for category, total in breakdown.items():
            table.add_row(category, f"${total:.2f}")
    else:
        table.add_row("No expenses this month.", "")
    table.add_section()
    table.add_row("Overall balance", Text(f"${balance:.2f}", style="green" if balance >= 0 else "red"), style="bold")
    console.print(table)


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
        console.print("No transactions found.")
        return
    for t in to_show:
        sign = "+" if t.is_income else "-"
        note_str = f"  {t.note}" if t.note else ""
        line = Text()
        line.append(f"{t.date}  ")
        line.append(f"{sign}${t.amount:<10.2f}", style="green" if t.is_income else "")
        line.append(f"  {t.category:<16}{note_str}")
        console.print(line)


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
        if raw_category and category.lower() not in {c.lower() for c in VALID_CATEGORIES}:
            print(f"Error: category must be one of {VALID_CATEGORIES}")
            return
        note = raw_note if raw_note else t.note
        updated = Transaction(amount=amount, category=category, date=t.date, note=note)
    except ValueError as e:
        print(f"Error: {e}")
        return

    update_transaction(index, updated)
    print(f"Transaction {index + 1} updated.")


def cmd_help(args: argparse.Namespace) -> None:
    entries = [
        (
            "add <amount> <category> [--note TEXT]",
            "Record a new income or expense transaction.",
            'budget add 45.50 food --note "Groceries"',
        ),
        (
            "summary",
            "Show this month's income, expenses, net, and top spending category.",
            "budget summary",
        ),
        (
            "report",
            "Show spending breakdown by category for the current month.",
            "budget report",
        ),
        (
            "list [--month YYYY-MM]",
            "List the last 20 transactions, or all from a specific month.",
            "budget list --month 2026-05",
        ),
        (
            "delete",
            "Pick a transaction from a numbered list and delete it.",
            "budget delete",
        ),
        (
            "edit",
            "Pick a transaction from a numbered list and edit its fields.",
            "budget edit",
        ),
        (
            "clear",
            "Delete all transactions (prompts for confirmation).",
            "budget clear",
        ),
        (
            "export [--from YYYY-MM-DD] [--to YYYY-MM-DD]",
            "Export transactions to transactions.csv. Date range is optional.",
            "budget export --from 2026-05-01 --to 2026-05-31",
        ),
        (
            "recurring add <amount> <category> [--note TEXT] [--frequency monthly]",
            "Set up a new recurring transaction.",
            'budget recurring add 1200 rent --note "Monthly rent" --frequency monthly',
        ),
        (
            "recurring list",
            "Show all recurring transactions and whether each is due this month.",
            "budget recurring list",
        ),
        (
            "recurring apply",
            "Add all recurring transactions that are due this month (skips already-applied ones).",
            "budget recurring apply",
        ),
        (
            "set-limit <category> <amount>",
            "Set a monthly spending limit for a category.",
            "budget set-limit food 300",
        ),
        (
            "limits",
            "Show all budget limits and current month spending against each.",
            "budget limits",
        ),
        (
            "help",
            "Show this help message.",
            "budget help",
        ),
    ]

    print("budget — personal budget tracker\n")
    for usage, description, example in entries:
        print(f"  {usage}")
        print(f"    {description}")
        print(f"    Example: {example}")
        print()


def cmd_recurring_add(args: argparse.Namespace) -> None:
    if args.category.lower() not in {c.lower() for c in VALID_CATEGORIES}:
        console.print(f"Error: category must be one of {VALID_CATEGORIES}")
        sys.exit(1)
    try:
        rt = RecurringTransaction(
            amount=args.amount,
            category=args.category,
            frequency=args.frequency,
            note=args.note or "",
        )
        add_recurring(rt)
        console.print(f"Recurring {rt.frequency} transaction added: {rt.category} ${rt.amount:.2f}")
    except ValueError as e:
        console.print(f"Error: {e}")
        sys.exit(1)


def cmd_recurring_list(args: argparse.Namespace) -> None:
    today = date.today()
    recurring = load_recurring()
    if not recurring:
        console.print("No recurring transactions set up.")
        return
    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Amount", justify="right")
    table.add_column("Category")
    table.add_column("Frequency")
    table.add_column("Note")
    table.add_column("This month")
    for rt in recurring:
        status = Text("due", style="yellow") if rt.is_due(today) else Text("applied", style="green")
        table.add_row(
            Text(f"${rt.amount:.2f}", style="green" if rt.category == "income" else ""),
            rt.category,
            rt.frequency,
            rt.note,
            status,
        )
    console.print(table)


def cmd_recurring_apply(args: argparse.Namespace) -> None:
    today = date.today()
    recurring = load_recurring()
    applied = 0
    for rt in recurring:
        if rt.is_due(today):
            add_transaction(Transaction(amount=rt.amount, category=rt.category, date=today, note=rt.note))
            rt.last_applied = today
            applied += 1
            console.print(f"Applied: {rt.category} ${rt.amount:.2f}")
    save_recurring(recurring)
    if applied == 0:
        console.print("No recurring transactions due.")
    else:
        console.print(f"{applied} transaction(s) applied.")


def cmd_recurring(args: argparse.Namespace) -> None:
    subcommands = {
        "add": cmd_recurring_add,
        "list": cmd_recurring_list,
        "apply": cmd_recurring_apply,
    }
    subcommands[args.recurring_command](args)


def cmd_set_limit(args: argparse.Namespace) -> None:
    try:
        BudgetLimit(category=args.category, amount=args.amount)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    set_limit(args.category, args.amount)
    print(f"Limit set: {args.category} ${args.amount:.2f}/month")


def cmd_limits(args: argparse.Namespace) -> None:
    today = date.today()
    limits = load_limits()
    if not limits:
        console.print("No limits set. Use 'budget set-limit <category> <amount>' to add one.")
        return
    transactions = load_transactions()
    totals = category_breakdown(transactions, today.year, today.month)

    console.print(f"Budget limits — {today.strftime('%B %Y')}", style="bold")
    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Category")
    table.add_column("Spent", justify="right")
    table.add_column("Limit", justify="right")
    table.add_column("Status")

    for category, limit in sorted(limits.items()):
        spent = totals.get(category, 0.0)
        if spent > limit:
            status = Text("OVER", style="bold red")
        elif spent >= limit * WARN_THRESHOLD:
            status = Text("NEAR", style="bold yellow")
        else:
            status = Text("ok", style="green")
        table.add_row(category, f"${spent:.2f}", f"${limit:.2f}", status)

    console.print(table)


def cmd_export(args: argparse.Namespace) -> None:
    from_date = None
    to_date = None

    raw_from = getattr(args, "from_date", None)
    raw_to = getattr(args, "to_date", None)

    if raw_from:
        try:
            from_date = date.fromisoformat(raw_from)
        except ValueError:
            print("Error: --from must be in YYYY-MM-DD format (e.g. 2026-05-01)")
            sys.exit(1)

    if raw_to:
        try:
            to_date = date.fromisoformat(raw_to)
        except ValueError:
            print("Error: --to must be in YYYY-MM-DD format (e.g. 2026-05-31)")
            sys.exit(1)

    path = Path("transactions.csv").resolve()
    export_csv(path, from_date=from_date, to_date=to_date)
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
    export_parser = subparsers.add_parser("export", help="Export all transactions to transactions.csv")
    export_parser.add_argument("--from", dest="from_date", type=str, default=None, metavar="YYYY-MM-DD", help="Export transactions from this date (inclusive)")
    export_parser.add_argument("--to", dest="to_date", type=str, default=None, metavar="YYYY-MM-DD", help="Export transactions up to this date (inclusive)")

    set_limit_parser = subparsers.add_parser("set-limit", help="Set a monthly spending limit for a category")
    set_limit_parser.add_argument("category", choices=VALID_CATEGORIES, help="Category to limit")
    set_limit_parser.add_argument("amount", type=float, help="Monthly spending limit")

    subparsers.add_parser("limits", help="Show all budget limits and current month spend")

    recurring_parser = subparsers.add_parser("recurring", help="Manage recurring transactions")
    recurring_sub = recurring_parser.add_subparsers(dest="recurring_command", required=True)

    rec_add_parser = recurring_sub.add_parser("add", help="Set up a new recurring transaction")
    rec_add_parser.add_argument("amount", type=float, help="Transaction amount")
    rec_add_parser.add_argument("category", choices=VALID_CATEGORIES, help="Transaction category")
    rec_add_parser.add_argument("--note", type=str, default="", help="Optional note")
    rec_add_parser.add_argument(
        "--frequency", choices=VALID_FREQUENCIES, default="monthly", help="Recurrence frequency"
    )

    recurring_sub.add_parser("list", help="List all recurring transactions")
    recurring_sub.add_parser("apply", help="Apply all recurring transactions due this month")

    subparsers.add_parser("help", help="Show a summary of every command with examples")

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
        "recurring": cmd_recurring,
        "help": cmd_help,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
