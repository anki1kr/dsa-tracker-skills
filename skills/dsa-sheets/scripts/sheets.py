#!/usr/bin/env python3
"""Compare popular DSA sheets: Striver A2Z vs Love Babbar 450 vs Apna College.

Commands:
  sheets.py compare [--json]
  sheets.py consensus [--json]
  sheets.py which <id|title> [--json]

Data is derived from DSA Tracker's 370-problem curated dataset and verified /coverage audit.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

CHECKED_DATE = "5 October 2026"
SOURCE_FOOTER = f"Source: https://dsatracker.tech/coverage (checked {CHECKED_DATE})"

# What cannot be derived from problems.json: how many rows each sheet's own website listed when it was re-read, and
# the one-line advice. Both come from https://dsatracker.tech/coverage. Every count of OUR problems is computed from
# the data below, so a refreshed snapshot can never disagree with this script.
SHEET_FACTS = [
    {
        "name": "Striver A2Z",
        "slug": "striver-a2z-tracker",
        "liveRows": 495,
        "bestFor": "Deepest coverage. The default if you have 3+ months and want no gaps.",
    },
    {
        "name": "Love Babbar 450",
        "slug": "love-babbar-450-tracker",
        "liveRows": 445,
        "bestFor": "Balanced classic. Same topic spread, ~20% lighter than A2Z.",
    },
    {
        "name": "Apna College",
        "slug": "apna-college-sheet-tracker",
        "liveRows": 193,
        "bestFor": "Gentlest start of the three for the problems we picked. Start here if you're new.",
    },
]


def coverage(problems: list[dict]) -> dict:
    """Counts of our problems per sheet, per pair of sheets, in all three and in exactly one."""
    names = [s["name"] for s in SHEET_FACTS]
    in_sheet = {n: {p["id"] for p in problems if n in p.get("sheets", [])} for n in names}
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    return {
        "total": len(problems),
        "sheets": [dict(s, curated=len(in_sheet[s["name"]])) for s in SHEET_FACTS],
        # ASCII "&", not the set-intersection sign: Windows consoles (cp1252) cannot print it and the script crashed.
        "overlaps": [{"pair": f"{a} & {b}", "shared": len(in_sheet[a] & in_sheet[b])} for a, b in pairs],
        "all_three": sum(1 for p in problems if len(p.get("sheets", [])) == 3),
        "exactly_one": sum(1 for p in problems if len(p.get("sheets", [])) == 1),
    }


def find_data_file(filename: str) -> Path:
    if "DSA_DATA_DIR" in os.environ:
        p = Path(os.environ["DSA_DATA_DIR"]) / filename
        if p.exists():
            return p

    here = Path(__file__).resolve().parent
    candidates = [here.parent / "data" / filename]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Could not locate {filename} in data/ directories.")


def load_problems() -> list[dict]:
    path = find_data_file("problems.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "problems" in data:
        return data["problems"]
    if isinstance(data, list):
        return data
    raise ValueError("Invalid problems.json structure")


def cmd_compare(args: argparse.Namespace) -> None:
    c = coverage(load_problems())
    if args.json:
        payload = {
            "checked_date": CHECKED_DATE,
            "total_curated_dataset": c["total"],
            "consensus_count": c["all_three"],
            "single_sheet_exclusive": c["exactly_one"],
            "sheets": c["sheets"],
            "overlaps": c["overlaps"],
            "source": f"https://dsatracker.tech/coverage (checked {CHECKED_DATE})",
        }
        print(json.dumps(payload, indent=2))
    else:
        print("Striver A2Z vs Love Babbar 450 vs Apna College: Coverage Comparison")
        print("===================================================================")
        print(f"Sheet coverage in DSA Tracker's {c['total']} curated problems:")
        for s in c["sheets"]:
            print(f"  - {s['name']}: {s['curated']} problems in tracker ({s['liveRows']} live rows on source site)")
            print(f"    Note: {s['bestFor']}")
        print()
        print("Sheet overlaps:")
        for o in c["overlaps"]:
            print(f"  - {o['pair']}: {o['shared']} shared problems")
        print(f"  - Consensus 75 (all three sheets): {c['all_three']} problems")
        print(f"  - In exactly one sheet: {c['exactly_one']} problems")
        print()
        print(SOURCE_FOOTER)


def cmd_consensus(args: argparse.Namespace) -> None:
    problems = load_problems()
    consensus = [p for p in problems if p.get("consensus")]

    # Group by topic
    diff_rank = {"Easy": 0, "Medium": 1, "Hard": 2}
    by_topic: dict[str, list[dict]] = {}
    for p in consensus:
        by_topic.setdefault(p["topic"], []).append(p)

    for t in by_topic:
        by_topic[t].sort(key=lambda p: (diff_rank.get(p.get("difficulty", ""), 9), p["id"]))

    if args.json:
        payload = {
            "total": len(consensus),
            "checked_date": CHECKED_DATE,
            "topics": {
                topic: [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "difficulty": p["difficulty"],
                        "url": p["url"],
                        "practice_url": p.get("practice_url", ""),
                    }
                    for p in plist
                ]
                for topic, plist in sorted(by_topic.items())
            },
            "source": f"https://dsatracker.tech/coverage (checked {CHECKED_DATE})",
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"The Consensus 75 ({len(consensus)} problems agreed upon by all three sheets)")
        print("=========================================================================")
        print("These problems appear simultaneously in Striver A2Z, Love Babbar 450, and Apna College.")
        print()

        for topic in sorted(by_topic.keys()):
            plist = by_topic[topic]
            print(f"## {topic} ({len(plist)})")
            for p in plist:
                print(f"  - {p['title']} (#{p['id']}, {p['difficulty']})")
                print(f"    {p['url']}")
            print()

        print(SOURCE_FOOTER)


def cmd_which(args: argparse.Namespace) -> None:
    query = args.query.strip()
    problems = load_problems()

    matched = None
    # Check if integer ID
    try:
        qid = int(query)
        for p in problems:
            if p["id"] == qid:
                matched = p
                break
    except ValueError:
        pass

    # Check title match (exact or case-insensitive)
    if not matched:
        q_lower = query.lower()
        for p in problems:
            if p["title"].lower() == q_lower:
                matched = p
                break
        # If not exact, check prefix / slug
        if not matched:
            for p in problems:
                if q_lower in p["title"].lower():
                    matched = p
                    break

    if not matched:
        print(f"Error: Problem '{query}' not found in the 370-problem dataset.", file=sys.stderr)
        sys.exit(1)

    sheets = matched.get("sheets", [])
    is_consensus = matched.get("consensus", False)

    if args.json:
        payload = {
            "id": matched["id"],
            "title": matched["title"],
            "topic": matched["topic"],
            "difficulty": matched["difficulty"],
            "sheets": sheets,
            "sheets_count": len(sheets),
            "consensus": is_consensus,
            "url": matched["url"],
            "practice_url": matched.get("practice_url", ""),
            "source": f"https://dsatracker.tech/coverage (checked {CHECKED_DATE})",
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Problem #{matched['id']}: {matched['title']}")
        print(f"Topic: {matched['topic']} | Difficulty: {matched['difficulty']}")
        print(f"DSA Tracker: {matched['url']}")
        if matched.get("practice_url"):
            print(f"Practice: {matched['practice_url']}")
        print()
        print(f"Sheets containing this problem ({len(sheets)}/3):")
        if sheets:
            for s in sheets:
                print(f"  - {s}")
        else:
            print("  - None of the 3 major sheets")
        if is_consensus:
            print("  * Part of the Consensus 75 (appears in all 3 sheets)")
        print()
        print(SOURCE_FOOTER)


def main() -> None:
    parser = argparse.ArgumentParser(description="DSA Tracker sheet comparison utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # compare
    p_comp = subparsers.add_parser("compare", help="Compare coverage across Striver A2Z, Love Babbar 450, and Apna College")
    p_comp.add_argument("--json", action="store_true", help="Output JSON")

    # consensus
    p_cons = subparsers.add_parser("consensus", help="List the Consensus 75 problems grouped by topic")
    p_cons.add_argument("--json", action="store_true", help="Output JSON")

    # which
    p_which = subparsers.add_parser("which", help="Find which sheets contain a specific problem by ID or title")
    p_which.add_argument("query", type=str, help="Problem ID (e.g. 1) or title (e.g. 'Two Sum')")
    p_which.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.command == "compare":
        cmd_compare(args)
    elif args.command == "consensus":
        cmd_consensus(args)
    elif args.command == "which":
        cmd_which(args)


if __name__ == "__main__":
    main()
