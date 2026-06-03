import csv
import io
import json
import re
from datetime import date, datetime
from functools import wraps

from flask import Flask, Response, flash, g, redirect, render_template, request, session, url_for

from budgetcli import auth
from budgetcli.models import VALID_CATEGORIES, RecurringTransaction, Transaction
from budgetcli.reports import category_breakdown, monthly_summary, overall_balance
from budgetcli.storage import Storage

app = Flask(__name__)
app.secret_key = "budgetcli-dev-secret"

THEMES = [
    ("cupcake", "Pink",   "#ec4899"),
    ("dark",    "Dark",   "#1d232a"),
    ("nord",    "Blue",   "#5e81ac"),
    ("forest",  "Green",  "#1eb854"),
    ("dracula", "Purple", "#bd93f9"),
]
_VALID_THEMES = {t[0] for t in THEMES}

# Snapshot of the built-in categories so per-request custom category syncing
# can reset to the base list without cross-user contamination.
_BASE_CATEGORIES: list[str] = list(VALID_CATEGORIES)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.before_request
def _setup_request() -> None:
    if "username" in session:
        g.store = Storage(auth.user_data_path(session["username"]))
        # Reset to built-ins then add this user's custom categories so that
        # Transaction validation sees the right set for the current user.
        VALID_CATEGORIES[:] = _BASE_CATEGORIES
        for cat in g.store.load_custom_categories():
            if cat not in VALID_CATEGORIES:
                VALID_CATEGORIES.append(cat)


def _all_categories() -> list[str]:
    custom = g.store.load_custom_categories()
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
    current_theme = session.get("theme", "cupcake")
    base: dict = {
        "current_theme": current_theme,
        "themes": THEMES,
        "current_user": session.get("username"),
    }
    if "username" not in session:
        return {**base, "global_balance": 0, "global_balance_abs": 0}
    txns = g.store.load_transactions()
    bal = overall_balance(txns)
    return {**base, "global_balance": bal, "global_balance_abs": abs(bal)}


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if auth.verify_user(username, password):
            session["username"] = username.lower()
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        err = auth.validate_username(username)
        if err:
            flash(err, "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif auth.user_exists(username):
            flash("That username is already taken.", "error")
        else:
            auth.create_user(username, password)
            session["username"] = username.lower()
            flash("Account created! Welcome to BudgetBalancer.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


# ── Theme route (no login required) ──────────────────────────────────────────

@app.route("/theme/set", methods=["POST"])
def set_theme():
    theme = request.form.get("theme", "cupcake")
    if theme in _VALID_THEMES:
        session["theme"] = theme
    return redirect(request.referrer or url_for("dashboard"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard() -> str:
    today = date.today()
    transactions = g.store.load_transactions()
    limits = g.store.load_limits()
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


# ── Transactions ──────────────────────────────────────────────────────────────

@app.route("/transactions")
@login_required
def transactions() -> str:
    all_txns = g.store.load_transactions()
    indexed = sorted(enumerate(all_txns), key=lambda x: x[1].date, reverse=True)
    return render_template(
        "transactions.html",
        indexed_transactions=indexed,
        categories=_all_categories(),
        today=date.today().isoformat(),
    )


@app.route("/transactions/add", methods=["POST"])
@login_required
def add_transaction_route():
    try:
        txn = Transaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            date=request.form["date"],
            note=request.form.get("note", ""),
        )
        g.store.add_transaction(txn)
        flash("Transaction added.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("transactions"))


@app.route("/transactions/<int:idx>/delete", methods=["POST"])
@login_required
def delete_transaction_route(idx: int):
    try:
        g.store.delete_transaction(idx)
        flash("Transaction deleted.", "success")
    except IndexError:
        flash("Transaction not found.", "error")
    return redirect(url_for("transactions"))


@app.route("/transactions/<int:idx>/edit", methods=["POST"])
@login_required
def edit_transaction_route(idx: int):
    try:
        txn = Transaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            date=request.form["date"],
            note=request.form.get("note", ""),
        )
        g.store.update_transaction(idx, txn)
        flash("Transaction updated.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("transactions"))


# ── Budget limits ─────────────────────────────────────────────────────────────

@app.route("/limits")
@login_required
def limits() -> str:
    today = date.today()
    current_limits = g.store.load_limits()
    transactions = g.store.load_transactions()
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
@login_required
def set_limit_route():
    try:
        category = request.form["category"]
        amount = float(request.form["amount"])
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        g.store.set_limit(category, amount)
        flash(f"Limit set: {category} → ${amount:.2f}/month.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("limits"))


@app.route("/limits/<category>/delete", methods=["POST"])
@login_required
def delete_limit_route(category: str):
    g.store.remove_limit(category)
    flash(f"Limit removed for {category}.", "success")
    return redirect(url_for("limits"))


# ── Recurring ─────────────────────────────────────────────────────────────────

@app.route("/recurring")
@login_required
def recurring() -> str:
    today = date.today()
    rec_list = g.store.load_recurring()
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
@login_required
def add_recurring_route():
    try:
        rt = RecurringTransaction(
            amount=float(request.form["amount"]),
            category=request.form["category"],
            frequency="monthly",
            note=request.form.get("note", ""),
        )
        g.store.add_recurring(rt)
        flash("Recurring transaction added.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("recurring"))


@app.route("/recurring/apply", methods=["POST"])
@login_required
def apply_recurring_route():
    today = date.today()
    rec_list = g.store.load_recurring()
    applied = 0
    for rt in rec_list:
        if rt.is_due(today):
            g.store.add_transaction(
                Transaction(amount=rt.amount, category=rt.category, date=today, note=rt.note)
            )
            rt.last_applied = today
            applied += 1
    g.store.save_recurring(rec_list)
    label = "success" if applied else "info"
    plural = "s" if applied != 1 else ""
    flash(f"Applied {applied} recurring transaction{plural}.", label)
    return redirect(url_for("recurring"))


@app.route("/recurring/<int:idx>/delete", methods=["POST"])
@login_required
def delete_recurring_route(idx: int):
    rec_list = g.store.load_recurring()
    if 0 <= idx < len(rec_list):
        rec_list.pop(idx)
        g.store.save_recurring(rec_list)
        flash("Recurring transaction removed.", "success")
    else:
        flash("Not found.", "error")
    return redirect(url_for("recurring"))


# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/export")
@login_required
def export() -> str:
    today = date.today()
    return render_template(
        "export.html",
        default_from=date(today.year, today.month, 1).isoformat(),
        default_to=today.isoformat(),
    )


@app.route("/export/download")
@login_required
def export_download():
    from_str = request.args.get("from_date", "")
    to_str = request.args.get("to_date", "")
    try:
        from_date = date.fromisoformat(from_str) if from_str else None
        to_date = date.fromisoformat(to_str) if to_str else None
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for("export"))

    txns = g.store.load_transactions()
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


# ── Categories ────────────────────────────────────────────────────────────────

@app.route("/categories")
@login_required
def categories() -> str:
    custom = g.store.load_custom_categories()
    txns = g.store.load_transactions()
    rec = g.store.load_recurring()
    used: set[str] = {t.category for t in txns} | {r.category for r in rec}
    return render_template(
        "categories.html",
        default_categories=VALID_CATEGORIES,
        custom_categories=custom,
        used_categories=used,
    )


@app.route("/categories/add", methods=["POST"])
@login_required
def add_category_route():
    raw = request.form.get("name", "").strip().lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "", raw)
    if len(name) < 2 or len(name) > 30 or name.startswith("-") or name.endswith("-"):
        flash("Category name must be 2–30 characters, letters/numbers/hyphens, no leading or trailing hyphens.", "error")
        return redirect(url_for("categories"))
    if name in _all_categories():
        flash(f'Category "{name}" already exists.', "error")
        return redirect(url_for("categories"))
    g.store.add_custom_category(name)
    VALID_CATEGORIES.append(name)
    flash(f'Category "{name}" added.', "success")
    return redirect(url_for("categories"))


@app.route("/categories/<name>/delete", methods=["POST"])
@login_required
def delete_category_route(name: str):
    custom = g.store.load_custom_categories()
    if name not in custom:
        flash(f'"{name}" is a built-in category and cannot be deleted.', "error")
        return redirect(url_for("categories"))
    g.store.remove_custom_category(name)
    if name in VALID_CATEGORIES:
        VALID_CATEGORIES.remove(name)
    flash(f'Category "{name}" removed.', "success")
    return redirect(url_for("categories"))


# ── Excel Import ──────────────────────────────────────────────────────────────

def _parse_import_date(s: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s!r}")


@app.route("/import")
@login_required
def import_excel():
    return render_template("import.html", step="upload", categories=_all_categories())


@app.route("/import/upload", methods=["POST"])
@login_required
def import_upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("import_excel"))

    fname = file.filename.lower()
    if not (fname.endswith(".xlsx") or fname.endswith(".xls")):
        flash("Only .xlsx and .xls files are accepted.", "error")
        return redirect(url_for("import_excel"))

    try:
        if fname.endswith(".xlsx"):
            import openpyxl

            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
            ws = wb.active

            def _to_str(v) -> str:
                if v is None:
                    return ""
                if isinstance(v, datetime):
                    return v.date().isoformat()
                if isinstance(v, date):
                    return v.isoformat()
                return str(v).strip()

            string_rows = [[_to_str(c) for c in row] for row in ws.iter_rows(values_only=True)]
        else:
            import xlrd

            wb = xlrd.open_workbook(file_contents=file.read())
            ws = wb.sheet_by_index(0)

            def _xlrd_str(cell) -> str:
                if cell.ctype == xlrd.XL_CELL_DATE:
                    return xlrd.xldate_as_datetime(cell.value, wb.datemode).date().isoformat()
                if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    return ""
                if cell.ctype == xlrd.XL_CELL_NUMBER:
                    v = cell.value
                    return str(int(v)) if v == int(v) else str(v)
                return str(cell.value).strip()

            string_rows = [
                [_xlrd_str(ws.cell(i, j)) for j in range(ws.ncols)]
                for i in range(ws.nrows)
            ]
    except Exception as e:
        flash(f"Could not read Excel file: {e}", "error")
        return redirect(url_for("import_excel"))

    if not string_rows:
        flash("The file is empty.", "error")
        return redirect(url_for("import_excel"))

    headers = string_rows[0]
    data_rows = [r for r in string_rows[1:] if any(c for c in r)]

    if not data_rows:
        flash("No data rows found (the file only has a header row).", "error")
        return redirect(url_for("import_excel"))

    _ALIASES: dict[str, list[str]] = {
        "date":     ["date", "transaction date", "trans date", "txn date", "trans. date"],
        "amount":   ["amount", "value", "sum", "total", "price", "debit", "credit"],
        "category": ["category", "cat", "type", "transaction type", "txn type"],
        "note":     ["note", "notes", "description", "desc", "memo", "comment", "details", "narration"],
    }
    detected: dict[str, int] = {}
    for field, aliases in _ALIASES.items():
        for i, h in enumerate(headers):
            if h.lower().strip() in aliases and field not in detected:
                detected[field] = i

    temp_path = auth.user_data_path(session["username"]).parent / "import_temp.json"
    temp_path.write_text(
        json.dumps({"headers": headers, "rows": data_rows, "detected": detected}),
        encoding="utf-8",
    )

    return redirect(url_for("import_preview"))


@app.route("/import/preview")
@login_required
def import_preview():
    temp_path = auth.user_data_path(session["username"]).parent / "import_temp.json"
    if not temp_path.exists():
        flash("No import in progress. Please upload a file first.", "error")
        return redirect(url_for("import_excel"))

    data = json.loads(temp_path.read_text(encoding="utf-8"))
    return render_template(
        "import.html",
        step="preview",
        headers=data["headers"],
        preview_rows=data["rows"][:50],
        total_rows=len(data["rows"]),
        detected=data["detected"],
        categories=_all_categories(),
    )


@app.route("/import/confirm", methods=["POST"])
@login_required
def import_confirm():
    temp_path = auth.user_data_path(session["username"]).parent / "import_temp.json"
    if not temp_path.exists():
        flash("No import in progress.", "error")
        return redirect(url_for("import_excel"))

    data = json.loads(temp_path.read_text(encoding="utf-8"))
    rows = data["rows"]

    mapping: dict[str, int] = {}
    for field in ("date", "amount", "category", "note"):
        val = request.form.get(f"col_{field}", "-1")
        try:
            col_idx = int(val)
            if col_idx >= 0:
                mapping[field] = col_idx
        except ValueError:
            pass

    if "date" not in mapping or "amount" not in mapping:
        flash("You must map both the Date and Amount columns.", "error")
        return redirect(url_for("import_preview"))

    default_category = request.form.get("default_category", "other")
    all_cats = _all_categories()
    if default_category not in all_cats:
        default_category = "other"

    saved = 0
    skipped = 0
    for row in rows:
        try:
            raw_date = row[mapping["date"]].strip() if mapping["date"] < len(row) else ""
            raw_amount = (
                row[mapping["amount"]].strip().lstrip("$").replace(",", "")
                if mapping["amount"] < len(row) else ""
            )
            raw_cat = (
                row[mapping["category"]].strip().lower()
                if "category" in mapping and mapping["category"] < len(row)
                else ""
            )
            raw_note = (
                row[mapping["note"]].strip()
                if "note" in mapping and mapping["note"] < len(row)
                else ""
            )

            if not raw_date or not raw_amount:
                skipped += 1
                continue

            txn_date = _parse_import_date(raw_date)
            amount = abs(float(raw_amount))
            if amount == 0.0:
                skipped += 1
                continue

            category = raw_cat if raw_cat in all_cats else default_category
            g.store.add_transaction(
                Transaction(amount=amount, category=category, date=txn_date, note=raw_note[:200])
            )
            saved += 1
        except (ValueError, IndexError):
            skipped += 1

    temp_path.unlink(missing_ok=True)

    if saved:
        msg = f"Imported {saved} transaction{'s' if saved != 1 else ''}."
        if skipped:
            msg += f" {skipped} row{'s' if skipped != 1 else ''} skipped (invalid or empty)."
        flash(msg, "success")
    else:
        flash(
            "No transactions could be imported. Check that your file has valid date and amount columns.",
            "error",
        )

    return redirect(url_for("transactions"))


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
