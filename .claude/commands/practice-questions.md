You are generating a practice quiz for someone learning Python by building this project. Follow these steps exactly.

**Step 1 — gather context**

Read all of the following:
- `CLAUDE.md` — project overview and conventions
- `CHANGELOG.md` — features shipped so far
- Run `git log --oneline` to see every commit (each commit = a concept worked on)
- Read these source files in full:
  - `budgetcli/models.py`
  - `budgetcli/storage.py`
  - `budgetcli/reports.py`
  - `budgetcli/cli.py`
  - `tests/test_models.py`
  - `tests/test_cli.py`

**Step 2 — identify covered concepts**

From the git history and source files, extract the Python concepts and patterns that have actually been practised in this project. Examples of the kinds of things to look for (not exhaustive):
- dataclasses, type hints, Enums or plain lists for valid values
- argparse subparsers, `add_argument`, `action="version"`
- JSON file I/O, pathlib, auto-creating directories
- Error handling: ValueError, sys.exit(1), specific exception types
- pytest patterns: fixtures, parametrize, patching, testing CLIs via argparse
- CSV export, float precision
- Refactoring for testability (extracting `build_parser`, optional confirm param)
- importlib.metadata for version strings
- Constants vs magic numbers
- Validation logic and guard clauses

Only draw questions from concepts that appear in the actual code or commit history — do not invent topics the project hasn't covered.

**Step 3 — write the quiz**

Generate exactly 10 multiple-choice questions. Format each one like this:

---

**Q1. [short topic tag]** *(easy)*

Question text here?

A) ...
B) ...
C) ...
D) ...

**Answer: B** — one sentence explaining why, and why the others are wrong if it adds value.

---

Rules:
- 4 questions should be *easy* (recall/recognition of a pattern used directly in this codebase)
- 4 questions should be *hard* (reasoning about edge cases, tradeoffs, or "what would happen if…" scenarios)
- 2 questions should be *medium* difficulty
- Spread questions across different concepts — don't ask two questions about the same thing
- For code-based questions, use short snippets drawn from the actual source files in this project
- Wrong answer choices should be plausible, not obviously silly
- Do not number the topic tags — vary them (e.g. *argparse*, *testing*, *error handling*, *dataclasses*, *file I/O*, etc.)
- After Q10, add a one-line score guide: "Score: 9–10 excellent · 6–8 solid · below 6 review X and Y" where X and Y are the two weakest areas based on which questions tend to be harder
