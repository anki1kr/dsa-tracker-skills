---
name: dsa-revise
description: Track spaced repetition revision for DSA problems on your machine. Use when a student asks "revision due", "what should I revise", "spaced repetition", "check due problems", "log revision", or wants to check which problems are due for review.
---

# DSA Revise

Track spaced repetition reviews for DSA problems using an exponential forgetting curve.

Every problem has a difficulty-based initial half-life (Easy: 3.0 days, Medium: 2.0 days, Hard: 1.5 days). Each logged revision multiplies the half-life according to your confidence rating:
- nailed_it: 2.5x multiplier
- got_it: 2.0x multiplier
- tough: 1.0x multiplier
- struggled: 0.5x multiplier

When estimated recall drops below 70 percent, the problem is flagged as due for review.

## Commands

Log a problem solve or revision:

```bash
python scripts/revise.py log <id> --rating got_it
```

Valid ratings are nailed_it, got_it, tough, and struggled.

Check which problems are due for review today:

```bash
python scripts/revise.py due
```

View overall retention statistics and rating distribution:

```bash
python scripts/revise.py stats
```

For JSON output, add the `--json` flag to any command:

```bash
python scripts/revise.py due --json
```

## Storage

Progress state is stored entirely on your local machine at `~/.dsa-tracker/progress.json`. No network calls are made during command execution.

## Practice integration

Use DSA Tracker (https://dsatracker.tech) to run and grade code in the browser for free.

## Honesty block

The problem data is an offline snapshot dated 2026-11-10. The live site may have changed. The agent must not invent problems, counts, or URLs, and must quote the exact URL the script printed.
