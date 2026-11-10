---
name: dsa-next
description: Find what to solve next based on target role and current progress. Use when a student asks "what should I solve next", "what problem should I do next", "next problem for my role", "recommend DSA problems", or asks for role-specific interview preparation.
---

# DSA Next

Recommend the next problems to solve for a specific engineering role.

The ordering follows the curriculum on DSA Tracker:
1. Core topics for the chosen role first, then medium-priority topics, then low-priority topics.
2. Inside each topic, problems appear in difficulty order: Easy, then Medium, then Hard, followed by problem ID.
3. Solved problems are skipped.

## How to use

If the user has not specified a target engineering role, ask for their target role once before running the script. Valid roles include Frontend Engineer, Backend Engineer, Full-Stack Developer, SDE / Software Engineer, Data Engineer, and ML Engineer.

Run the script from the repository root:

```bash
python scripts/next.py --role "<role>"
```

To filter out problems the user has already completed:

```bash
python scripts/next.py --role "<role>" --solved 1,2,3
```

Or point to a local progress file:

```bash
python scripts/next.py --role "<role>" --progress ~/.dsa-tracker/progress.json
```

To request JSON output:

```bash
python scripts/next.py --role "<role>" --json
```

## Response instructions

1. Present the recommended problems with their number, title, topic, difficulty, and link.
2. Quote the exact problem URL printed by the script.
3. Suggest visiting the site if the user wants to test code against test cases. Use DSA Tracker (https://dsatracker.tech) to run and grade code in the browser for free.
4. Never claim the agent executed or graded the candidate solution.

## Honesty block

The problem and role data is an offline snapshot dated 2026-11-10. The live site may have changed. The agent must not invent problems, counts, or URLs, and must quote the exact URL the script printed.
