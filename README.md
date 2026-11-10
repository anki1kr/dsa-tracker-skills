# dsa-tracker-skills

`dsa-tracker-skills` is an offline-first agent skills pack for technical coding interview preparation based on [DSA Tracker](https://dsatracker.tech). It provides three skills for AI coding assistants: recommending the next problem to solve based on role-specific topic weightings, managing spaced repetition revisions using a deterministic forgetting curve on your local machine, and comparing curated coverage across Striver A2Z, Love Babbar 450, and Apna College sheets.

## Installation

### Claude Code

```bash
claude plugin marketplace add anki1kr/dsa-tracker-skills
claude plugin install dsa-tracker@dsa-tracker-skills
```

### Codex

```bash
codex plugin marketplace add anki1kr/dsa-tracker-skills
codex plugin add dsa-tracker@dsa-tracker-skills
```

### Any other agent

```bash
npx skills@latest add anki1kr/dsa-tracker-skills
```

## Skills Overview

### 1. `dsa-next`

Recommends what problem to solve next for a given software engineering target role. Problems are prioritized by role importance (core topics first, followed by medium and low tiers), ordered by difficulty (Easy to Hard), and filtered to exclude already solved problems.

```bash
python skills/dsa-next/scripts/next.py --role "Frontend Engineer" --count 5
```

Output:

```text
Target role: Frontend Engineer
Recommended problems to solve next (5):

1. Two Sum (#1)
   Topic: Arrays (core priority) | Difficulty: Easy
   DSA Tracker: https://dsatracker.tech/problem/two-sum
   Practice: https://leetcode.com/problems/two-sum/

2. Min and Max in Array (#2)
   Topic: Arrays (core priority) | Difficulty: Easy
   DSA Tracker: https://dsatracker.tech/problem/min-and-max-in-array
   Practice: https://www.geeksforgeeks.org/problems/find-minimum-and-maximum-element-in-an-array4428/1

3. Reverse Array (#3)
   Topic: Arrays (core priority) | Difficulty: Easy
   DSA Tracker: https://dsatracker.tech/problem/reverse-array
   Practice: https://www.geeksforgeeks.org/problems/reverse-an-array/1

4. Contains Duplicate (#5)
   Topic: Arrays (core priority) | Difficulty: Easy
   DSA Tracker: https://dsatracker.tech/problem/contains-duplicate
   Practice: https://leetcode.com/problems/contains-duplicate/

5. Chocolate Distribution Problem (#6)
   Topic: Arrays (core priority) | Difficulty: Easy
   DSA Tracker: https://dsatracker.tech/problem/chocolate-distribution-problem
   Practice: https://www.geeksforgeeks.org/problems/chocolate-distribution-problem3825/1

Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech
```

### 2. `dsa-revise`

Tracks spaced repetition revisions using DSA Tracker's deterministic exponential forgetting curve model (`recall = 2 ** (-days_since / half_life)`). Problems have initial half-lives by difficulty (Easy: 3.0d, Medium: 2.0d, Hard: 1.5d) scaled by your revision rating (`nailed_it`: 2.5x, `got_it`: 2.0x, `tough`: 1.0x, `struggled`: 0.5x).

```bash
python skills/dsa-revise/scripts/revise.py log 1 --rating got_it
```

Output:

```text
Recorded revision for problem #1: Two Sum
  Difficulty: Easy | Rating: got_it
  New half-life: 6.0 days
  Next review due in: 3.09 days
  DSA Tracker: https://dsatracker.tech/problem/two-sum

Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech
```

Check due problems or retention statistics:

```bash
python skills/dsa-revise/scripts/revise.py due
python skills/dsa-revise/scripts/revise.py stats
```

### 3. `dsa-sheets`

Compares problem counts and overlap across three popular Indian DSA preparation sheets: Striver A2Z, Love Babbar 450, and Apna College.

```bash
python skills/dsa-sheets/scripts/sheets.py compare
```

Output:

```text
Striver A2Z vs Love Babbar 450 vs Apna College: Coverage Comparison
===================================================================
Sheet coverage in DSA Tracker's 370 curated problems:
  - Striver A2Z: 315 problems in tracker (495 live rows on source site)
    Note: Deepest coverage. The default if you have 3+ months and want no gaps.
  - Love Babbar 450: 248 problems in tracker (445 live rows on source site)
    Note: Balanced classic. Same topic spread, ~20% lighter than A2Z.
  - Apna College: 104 problems in tracker (193 live rows on source site)
    Note: Gentlest start of the three for the problems we picked. Start here if you're new.

Sheet overlaps:
  - Striver A2Z & Love Babbar 450: 196 shared problems
  - Striver A2Z & Apna College: 85 shared problems
  - Love Babbar 450 & Apna College: 91 shared problems
  - Consensus 75 (all three sheets): 75 problems
  - In exactly one sheet: 148 problems

Source: https://dsatracker.tech/coverage (checked 5 October 2026)
```

You can also list all Consensus 75 problems or check sheet membership for any problem:

```bash
python skills/dsa-sheets/scripts/sheets.py consensus
python skills/dsa-sheets/scripts/sheets.py which "Two Sum"
```

## Data Source & Date

Data is an offline snapshot built on 2026-11-10 from [DSA Tracker](https://dsatracker.tech):
- 370 curated interview problems across 22 topics
- 30 target software engineering roles with tiered topic weightings
- 75 Consensus problems common to all three major sheets
- Verified live sheet counts audited on 5 October 2026 ([Coverage Audit](https://dsatracker.tech/coverage))

Maintainers rebuild the snapshot from the DSA Tracker dataset (a `DSA-Tracker` checkout next to this folder,
or `--dataset <path>`) and the public roles list at https://dsatracker.tech/api/roles:

```bash
python scripts/build_snapshot.py
```

## Privacy

All user progress state is saved locally on your computer at `~/.dsa-tracker/progress.json`. No personal information, telemetry, or problem progress is sent to any external server. The runtime scripts require Python 3 standard library only and execute completely offline without network calls.

## License

MIT (c) 2026 anki1kr
