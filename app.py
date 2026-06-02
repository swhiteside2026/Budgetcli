import csv
import io
import re
from datetime import date

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from budgetcli.models import VALID_CATEGORIES, RecurringTransaction, Transaction
from budgetcli.reports import category_breakdown, monthly_summary, overall_balance
from budgetcli.storage import (
    add_custom_category,
    add_recurring,
    add_transaction,
    delete_transaction,
    load_custom_categories,
    load_limits,
    load_recurring,
    load_transactions,
    remove_custom_category,
    remove_limit,
    save_recurring,
    set_limit,
    update_transaction,
)

app = Flask(__name__)
app.secret_key = "budgetcli-dev-secret"


@app.before_request
def _sync_custom_categories() -> None:
    for cat in load_custom_categories():
        if cat not in VALID_CATEGORIES:
            VALID_CATEGORIES.append(cat)


def _all_categories() -> list[str]:
    custom = load_custom_categories()
    return VALID_CATEGORIES + [c for c in custom if c not in VALID_CATEGORIES]


def _budget_data(
    transactions: list[Transaction],
    limits: dict[str, float],
    year: int,
    month: int,
) -> list[dict]:
    spent = category_breakdown(transactions, year, month)
    result = []
    for cat, limit in limits.items():
        cat_spent = spent.get(cat, 0.0)
        pct = min(cat_spent / limit * 100, 100) if limit > 0 else 0
        over = cat_spent > limit
        near = not over and cat_spent >= limit * 0.8
        result.append({
            "category": cat,
            "limit": limit,
            "spent": cat_spent,
            "pct": round(pct, 1),
            "bar_class": "progress-error" if over else ("progress-warning" if near else "progress-primary"),
            "label_class": "text-error font-bold" if over else "",
            "status": "OVER" if over else ("NEAR" if near else "OK"),
            "status_class": "badge-error" if over else ("badge-warning" if near else "badge-primary"),
        })
    return result


@app.context_processor
def inject_globals() -> dict:
    txns = load_transactions()
    bal = overall_balance(txns)
    return {"global_balance": bal, "global_balance_abs": abs(bal)}


@app.route("/")
def dashboard() -> str:
    today = date.today()
    transactions = load_transactions()
    limits = load_limits()
    income, expenses, savings = monthly_summary(transactions, today.year, today.month)
    balance = overall_balance(transactions)
    budget_data = _budget_data(transactions, limits, today.year, today.month)
    recent = sorted(transactions, key=lambda t: t.date, reverse=True)[:10]
    return render_template(
        "dashboard.html",
        transactions=recent,
        budget_data=budget_data,
        income=income,
        expenses=expenses,
        savings=savings,
        savings_abs=abs(savings),
        balance=balance,
        balance_abs=abs(balance),
        month_label=today.strftime("%B %Y"),
        total_count=len(transactions),
    )


@app.route("/transactions")
def transactions() -> str:
    all_txns = load_transactions()
    indexed = sorted(enumerate(all_txns), key=lambda x: x[1].date, reverse=True)
    return render_template(
        "transactions.html",
        indexed_transactions=indexed,
        categories=_all_categories(),
        today=date.today().isoformat(),
    )


@app.route("/transactions/add", methods=["POST"])
def add_transaction_route():
    try:
        txn = Transaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            date=request.form["date"],
            note=request.form.get("note", ""),
        )
        add_transaction(txn)
        flash("Transaction added.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("transactions"))


@app.route("/transactions/<int:idx>/delete", methods=["POST"])
def delete_transaction_route(idx: int):
    try:
        delete_transaction(idx)
        flash("Transaction deleted.", "success")
    except IndexError:
        flash("Transaction not found.", "error")
    return redirect(url_for("transactions"))


@app.route("/transactions/<int:idx>/edit", methods=["POST"])
def edit_transaction_route(idx: int):
    try:
        txn = Transaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            date=request.form["date"],
            note=request.form.get("note", ""),
        )
        update_transaction(idx, txn)
        flash("Transaction updated.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("transactions"))


@app.route("/limits")
def limits() -> str:
    today = date.today()
    current_limits = load_limits()
    transactions = load_transactions()
    budget_data = _budget_data(transactions, current_limits, today.year, today.month)
    available = [c for c in _all_categories() if c != "income"]
    return render_template(
        "limits.html",
        budget_data=budget_data,
        current_limits=current_limits,
        available_categories=available,
        month_label=today.strftime("%B %Y"),
    )


@app.route("/limits/set", methods=["POST"])
def set_limit_route():
    try:
        category = request.form["category"]
        amount = float(request.form["amount"])
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        set_limit(category, amount)
        flash(f"Limit set: {category} → ${amount:.2f}/month.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("limits"))


@app.route("/limits/<category>/delete", methods=["POST"])
def delete_limit_route(category: str):
    remove_limit(category)
    flash(f"Limit removed for {category}.", "success")
    return redirect(url_for("limits"))


@app.route("/recurring")
def recurring() -> str:
    today = date.today()
    rec_list = load_recurring()
    indexed = [(i, r, r.is_due(today)) for i, r in enumerate(rec_list)]
    due_count = sum(1 for _, _, due in indexed if due)
    return render_template(
        "recurring.html",
        indexed_recurring=indexed,
        categories=_all_categories(),
        today=today,
        due_count=due_count,
    )


@app.route("/recurring/add", methods=["POST"])
def add_recurring_route():
    try:
        rt = RecurringTransaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            frequency="monthly",
            note=request.form.get("note", ""),
        )
        add_recurring(rt)
        flash("Recurring transaction added.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("recurring"))


@app.route("/recurring/apply", methods=["POST"])
def apply_recurring_route():
    today = date.today()
    rec_list = load_recurring()
    applied = 0
    for rt in rec_list:
        if rt.is_due(today):
            add_transaction(
                Transaction(amount=rt.amount, category=rt.category, date=today, note=rt.note)
            )
            rt.last_applied = today
            applied += 1
    save_recurring(rec_list)
    label = "success" if applied else "info"
    plural = "s" if applied != 1 else ""
    flash(f"Applied {applied} recurring transaction{plural}.", label)
    return redirect(url_for("recurring"))


@app.route("/recurring/<int:idx>/delete", methods=["POST"])
def delete_recurring_route(idx: int):
    rec_list = load_recurring()
    if 0 <= idx < len(rec_list):
        rec_list.pop(idx)
        save_recurring(rec_list)
        flash("Recurring transaction removed.", "success")
    else:
        flash("Not found.", "error")
    return redirect(url_for("recurring"))


@app.route("/export")
def export() -> str:
    today = date.today()
    return render_template(
        "export.html",
        default_from=date(today.year, today.month, 1).isoformat(),
        default_to=today.isoformat(),
    )


@app.route("/export/download")
def export_download():
    from_str = request.args.get("from_date", "")
    to_str = request.args.get("to_date", "")
    try:
        from_date = date.fromisoformat(from_str) if from_str else None
        to_date = date.fromisoformat(to_str) if to_str else None
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for("export"))

    txns = load_transactions()
    if from_date:
        txns = [t for t in txns if t.date >= from_date]
    if to_date:
        txns = [t for t in txns if t.date <= to_date]
    txns = sorted(txns, key=lambda t: t.date)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "category", "amount", "note"])
    for t in txns:
        writer.writerow([t.date.isoformat(), t.category, round(t.amount, 2), t.note])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@app.route("/categories")
def categories() -> str:
    custom = load_custom_categories()
    txns = load_transactions()
    rec = load_recurring()
    used: set[str] = {t.category for t in txns} | {r.category for r in rec}
    return render_template(
        "categories.html",
        default_categories=VALID_CATEGORIES,
        custom_categories=custom,
        used_categories=used,
    )


@app.route("/categories/add", methods=["POST"])
def add_category_route():
    raw = request.form.get("name", "").strip().lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "", raw)
    if len(name) < 2 or len(name) > 30 or name.startswith("-") or name.endswith("-"):
        flash("Category name must be 2–30 characters, letters/numbers/hyphens, no leading or trailing hyphens.", "error")
        return redirect(url_for("categories"))
    if name in _all_categories():
        flash(f'Category "{name}" already exists.', "error")
        return redirect(url_for("categories"))
    add_custom_category(name)
    VALID_CATEGORIES.append(name)
    flash(f'Category "{name}" added.', "success")
    return redirect(url_for("categories"))


@app.route("/categories/<name>/delete", methods=["POST"])
def delete_category_route(name: str):
    if name in VALID_CATEGORIES and name not in load_custom_categories():
        flash(f'"{name}" is a built-in category and cannot be deleted.', "error")
        return redirect(url_for("categories"))
    remove_custom_category(name)
    if name in VALID_CATEGORIES:
        VALID_CATEGORIES.remove(name)
    flash(f'Category "{name}" removed.', "success")
    return redirect(url_for("categories"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
