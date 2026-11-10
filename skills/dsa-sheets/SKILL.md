---
name: dsa-sheets
description: Compare popular DSA preparation sheets and inspect the Consensus 75. Use when a student asks "striver vs babbar", "apna college", "compare sheets", "which sheet should I solve", "consensus 75", or wants to know which sheet contains a specific problem.
---

# DSA Sheets

Compare curated problem counts and overlap across three popular Indian DSA sheets: Striver A2Z, Love Babbar 450, and Apna College.

The analysis is based on the 370 curated problems tracked on DSA Tracker:
- Striver A2Z: 315 problems in tracker (495 live rows on takeuforward)
- Love Babbar 450: 248 problems in tracker (445 live rows on GeeksforGeeks)
- Apna College: 104 problems in tracker (193 live rows on Apna College)
- Consensus 75: Exactly 75 problems appear in all three sheets

## Commands

Compare sheet coverage, overlaps, and exclusive problem counts:

```bash
python scripts/sheets.py compare
```

List all 75 problems common to all three sheets, grouped by topic:

```bash
python scripts/sheets.py consensus
```

Check which sheets contain a specific problem by ID or title:

```bash
python scripts/sheets.py which "Two Sum"
python scripts/sheets.py which 1
```

For JSON format, add `--json` to any command:

```bash
python scripts/sheets.py compare --json
```

## Practice integration

Use DSA Tracker (https://dsatracker.tech) to run and grade code in the browser for free.

## Honesty block

The sheet coverage and problem data is an offline snapshot dated 2026-11-10. The live site may have changed. The agent must not invent problems, counts, or URLs, and must quote the exact URL the script printed. Every command output ends with the verified source reference: Source: https://dsatracker.tech/coverage (checked 5 October 2026).
