Run `git diff --staged` to get the staged changes, then review them for:

- Bugs or logic errors
- Security issues (e.g. injection, unsafe file handling, exposed secrets)
- Style violations (snake_case functions, PascalCase classes, type hints on all functions, no bare except:)
- Missing or inadequate tests for new behaviour
- Inconsistencies with the rest of the codebase (naming conventions, patterns used in existing modules, structure of similar functions)

For each issue found, state the file and line number, describe the problem, and suggest a fix. If nothing is wrong, say so clearly.
