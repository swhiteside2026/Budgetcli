Run the project tests with:

```
python -m pytest tests/ -v --tb=short
```

Read the output. If all tests pass, report the count and stop.

If any tests fail, examine the failure output and the relevant source files to diagnose the root cause, then fix the implementation code. Do not modify existing tests. Re-run the tests after each fix to confirm the failure is resolved. Repeat until all tests pass.
