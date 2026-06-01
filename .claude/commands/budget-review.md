Run the following three commands and capture their output:

```
python -m budgetcli.cli summary
python -m budgetcli.cli limits
python -m budgetcli.cli report
```

Then write a single plain-English paragraph (4–6 sentences) summarising the user's financial health for the current month. The paragraph must cover:

- **On track**: which categories or the overall balance are in good shape
- **Over budget**: any categories that have exceeded their limit (status OVER), or a note if none are over
- **Watch out**: categories at NEAR status (≥80 % of limit but not yet over), or any other signals worth flagging (e.g. net spending is negative, a category has no limit set but spend looks high)

Write in a friendly, direct tone — no bullet points, no headers, just a paragraph the user can read in under 30 seconds. Do not repeat the raw numbers verbatim; summarise and contextualise them.
