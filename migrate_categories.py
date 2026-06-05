"""One-time migration: merge mixed-case category duplicates in ledger.json.

Usage:
    python migrate_categories.py [--path data/ledger.json]

What it does
------------
1. Backs up ledger.json → ledger.json.bak (refuses to run if a backup already
   exists, so you won't silently overwrite a previous backup).
2. Groups every category string found in transactions, limits, recurring
   transactions, and custom_categories by its lowercase form.
3. For groups with more than one variant (e.g. "food", "Food", "FOOD"),
   picks the most-used form (most appearances in transactions). Ties are
   broken by preferring the more-capitalised form, then alphabetically.
4. Rewrites all references to the chosen canonical form in a single pass.
5. Prints a summary table and exits.

Safe to re-run: if no duplicates exist the script reports "Nothing to do."
"""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path


def _pick_winner(variants: list[str], txn_counts: Counter) -> str:
    """Choose the canonical form for a group of case-variants."""
    # Most transactions wins; break ties by preferring more capitalised form
    # (more uppercase letters), then lexicographic order.
    return max(
        variants,
        key=lambda v: (txn_counts[v], sum(1 for c in v if c.isupper()), v),
    )


def migrate(ledger_path: Path) -> None:
    if not ledger_path.exists():
        print(f"ERROR: {ledger_path} not found.")
        return

    backup_path = ledger_path.with_suffix(".json.bak")
    if backup_path.exists():
        print(
            f"ERROR: backup {backup_path} already exists.\n"
            "Remove or rename it before running the migration again."
        )
        return

    raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        raw = {"transactions": raw, "limits": {}, "recurring": []}

    transactions: list[dict] = raw.get("transactions", [])
    limits: dict[str, float] = raw.get("limits", {})
    recurring: list[dict] = raw.get("recurring", [])
    custom_cats: list[str] = raw.get("custom_categories", [])

    # ── collect all category strings by lowercase key ──────────────────────────
    groups: dict[str, list[str]] = {}  # lowercase → [variants seen]
    txn_counts: Counter = Counter()

    for t in transactions:
        cat = t.get("category", "")
        if cat:
            groups.setdefault(cat.lower(), [])
            if cat not in groups[cat.lower()]:
                groups[cat.lower()].append(cat)
            txn_counts[cat] += 1

    for k in limits:
        groups.setdefault(k.lower(), [])
        if k not in groups[k.lower()]:
            groups[k.lower()].append(k)

    for r in recurring:
        cat = r.get("category", "")
        if cat:
            groups.setdefault(cat.lower(), [])
            if cat not in groups[cat.lower()]:
                groups[cat.lower()].append(cat)

    for c in custom_cats:
        groups.setdefault(c.lower(), [])
        if c not in groups[c.lower()]:
            groups[c.lower()].append(c)

    # ── find groups that actually need merging ──────────────────────────────────
    merges: dict[str, str] = {}  # old variant → winner
    for lower_key, variants in groups.items():
        if len(variants) <= 1:
            continue
        winner = _pick_winner(variants, txn_counts)
        for v in variants:
            if v != winner:
                merges[v] = winner

    if not merges:
        print("Nothing to do — no mixed-case duplicates found.")
        return

    # ── back up before making any changes ──────────────────────────────────────
    shutil.copy2(ledger_path, backup_path)
    print(f"Backup written → {backup_path}\n")

    # ── apply the rename map ────────────────────────────────────────────────────
    txn_updated = 0
    for t in transactions:
        old = t.get("category", "")
        if old in merges:
            t["category"] = merges[old]
            txn_updated += 1

    new_limits: dict[str, float] = {}
    for k, v in limits.items():
        new_limits[merges.get(k, k)] = v
    raw["limits"] = new_limits

    for r in recurring:
        old = r.get("category", "")
        if old in merges:
            r["category"] = merges[old]

    seen_lower: set[str] = set()
    new_custom: list[str] = []
    for c in custom_cats:
        canonical = merges.get(c, c)
        if canonical.lower() not in seen_lower:
            new_custom.append(canonical)
            seen_lower.add(canonical.lower())
    raw["custom_categories"] = new_custom

    raw["transactions"] = transactions
    raw["recurring"] = recurring

    ledger_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    # ── summary ─────────────────────────────────────────────────────────────────
    print(f"{'Old variant':<25}  {'→  Winner':<25}  Txns affected")
    print("-" * 65)
    for old, winner in sorted(merges.items()):
        n = sum(1 for t in transactions if t.get("category") == winner and old != winner)
        print(f"{old:<25}  →  {winner:<25}  {txn_counts[old]}")
    print(f"\nTotal transactions rewritten: {txn_updated}")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge mixed-case category duplicates in ledger.json")
    parser.add_argument("--path", default="data/ledger.json", help="Path to ledger.json")
    args = parser.parse_args()
    migrate(Path(args.path))
