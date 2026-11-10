#!/usr/bin/env python3
"""Recommend what to solve next based on target role and current progress.

Order matches DSA Tracker's role order:
1. Core topics first, then Medium, then Low (from role_topic_map)
2. Within each topic: Easy -> Medium -> Hard, then by problem ID
3. Solved problems are skipped

Data is loaded offline from data/problems.json and data/roles.json.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


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


def load_roles_data() -> dict:
    path = find_data_file("roles.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_problems_data() -> list[dict]:
    path = find_data_file("problems.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "problems" in data:
        return data["problems"]
    if isinstance(data, list):
        return data
    raise ValueError("Invalid problems.json format")


def resolve_solved_ids(cli_solved: str | None, progress_path: Path | None) -> set[int]:
    solved: set[int] = set()

    # 1. Parse progress file if available
    default_progress = Path.home() / ".dsa-tracker" / "progress.json"
    target_path = progress_path if progress_path is not None else default_progress

    if target_path and target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            if isinstance(pdata, dict):
                for sid in pdata.get("solved_ids", []):
                    try:
                        solved.add(int(sid))
                    except (ValueError, TypeError):
                        pass
                for sid in pdata.get("solved", []):
                    try:
                        solved.add(int(sid))
                    except (ValueError, TypeError):
                        pass
                problems_dict = pdata.get("problems", {})
                if isinstance(problems_dict, dict):
                    for k in problems_dict.keys():
                        try:
                            solved.add(int(k))
                        except (ValueError, TypeError):
                            pass
            elif isinstance(pdata, list):
                for sid in pdata:
                    try:
                        solved.add(int(sid))
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass

    # 2. Add explicit --solved argument
    if cli_solved:
        for part in cli_solved.split(","):
            part = part.strip()
            if part:
                try:
                    solved.add(int(part))
                except ValueError:
                    pass

    return solved


def get_recommendations(
    role: str,
    roles_data: dict,
    problems: list[dict],
    solved_ids: set[int],
    count: int = 5,
) -> tuple[str, list[dict]]:
    valid_roles: list[str] = roles_data.get("roles", [])
    role_topic_map: dict[str, dict[str, list[str]]] = roles_data.get("role_topic_map", {})

    # Match role exact or case-insensitive
    matched_role = None
    if role in role_topic_map:
        matched_role = role
    else:
        role_lower = role.lower().strip()
        for r in valid_roles:
            if r.lower() == role_lower:
                matched_role = r
                break

    if not matched_role or matched_role not in role_topic_map:
        print(f"Error: Unknown role '{role}'.", file=sys.stderr)
        print("Valid roles:", file=sys.stderr)
        for r in valid_roles:
            print(f"  - {r}", file=sys.stderr)
        sys.exit(2)

    tier_map = role_topic_map[matched_role]
    core_topics = tier_map.get("core", [])
    medium_topics = tier_map.get("medium", [])
    low_topics = tier_map.get("low", [])

    topic_tier: dict[str, str] = {}
    ordered_topics: list[str] = []
    for t in core_topics:
        topic_tier[t] = "core"
        ordered_topics.append(t)
    for t in medium_topics:
        topic_tier[t] = "medium"
        ordered_topics.append(t)
    for t in low_topics:
        topic_tier[t] = "low"
        ordered_topics.append(t)

    # Any problem topic not covered in the role's tiers
    all_dataset_topics = sorted({p["topic"] for p in problems})
    for t in all_dataset_topics:
        if t not in topic_tier:
            topic_tier[t] = "other"
            ordered_topics.append(t)

    # Group unsolved problems by topic
    diff_rank = {"Easy": 0, "Medium": 1, "Hard": 2}
    by_topic: dict[str, list[dict]] = {}
    for p in problems:
        if p["id"] in solved_ids:
            continue
        by_topic.setdefault(p["topic"], []).append(p)

    # Sort problems within each topic: Easy -> Medium -> Hard, then by ID
    for t, plist in by_topic.items():
        plist.sort(key=lambda p: (diff_rank.get(p.get("difficulty", ""), 9), p["id"]))

    recommendations: list[dict] = []
    for t in ordered_topics:
        plist = by_topic.get(t, [])
        for p in plist:
            item = dict(p)
            item["priority"] = topic_tier.get(t, "core")
            recommendations.append(item)
            if len(recommendations) >= count:
                break
        if len(recommendations) >= count:
            break

    return matched_role, recommendations


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommend what to solve next for a target role")
    parser.add_argument("--role", type=str, required=False, help="Target role name (e.g. 'Frontend Engineer', 'Backend Engineer')")
    parser.add_argument("--solved", type=str, default=None, help="Comma-separated IDs of solved problems (e.g. 1,2,3)")
    parser.add_argument("--progress", type=Path, default=None, help="Path to progress file (default: ~/.dsa-tracker/progress.json)")
    parser.add_argument("--count", type=int, default=5, help="Number of problems to recommend (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
    args = parser.parse_args()

    roles_data = load_roles_data()
    if not args.role:
        print("Error: --role argument is required.", file=sys.stderr)
        print("Valid roles:", file=sys.stderr)
        for r in roles_data.get("roles", []):
            print(f"  - {r}", file=sys.stderr)
        sys.exit(2)

    problems = load_problems_data()
    solved_ids = resolve_solved_ids(args.solved, args.progress)
    matched_role, recommendations = get_recommendations(
        role=args.role,
        roles_data=roles_data,
        problems=problems,
        solved_ids=solved_ids,
        count=args.count,
    )

    if args.json:
        payload = {
            "role": matched_role,
            "count": len(recommendations),
            "problems": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "topic": p["topic"],
                    "difficulty": p["difficulty"],
                    "priority": p["priority"],
                    "url": p["url"],
                    "practice_url": p["practice_url"],
                }
                for p in recommendations
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Target role: {matched_role}")
        print(f"Recommended problems to solve next ({len(recommendations)}):")
        print()
        for i, p in enumerate(recommendations, 1):
            print(f"{i}. {p['title']} (#{p['id']})")
            print(f"   Topic: {p['topic']} ({p['priority']} priority) | Difficulty: {p['difficulty']}")
            print(f"   DSA Tracker: {p['url']}")
            if p.get("practice_url"):
                print(f"   Practice: {p['practice_url']}")
            print()
        print("Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech")


if __name__ == "__main__":
    main()
