#!/usr/bin/env python3
"""Spaced repetition revision tracker for DSA Tracker problems.

Commands:
  revise.py log <id> --rating <nailed_it|got_it|tough|struggled>
  revise.py due [--threshold 0.7] [--json]
  revise.py stats [--json]

State is kept locally in ~/.dsa-tracker/progress.json.
Uses DSA Tracker's deterministic recall model.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

# Import recall model
try:
    from . import recall_model
except (ImportError, ValueError):
    import recall_model

CONFIDENCE_FACTOR = recall_model.CONFIDENCE_FACTOR
H0_BY_DIFFICULTY = recall_model.H0_BY_DIFFICULTY
HALF_LIFE_MIN = recall_model.HALF_LIFE_MIN
HALF_LIFE_MAX = recall_model.HALF_LIFE_MAX
REVIEW_THRESHOLD = recall_model.REVIEW_THRESHOLD
predict = recall_model.predict
compute_half_life = recall_model.compute_half_life
next_review_in_days = recall_model.next_review_in_days
recall_probability = recall_model.recall_probability
rank_due = recall_model.rank_due


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


def load_problems_map() -> dict[int, dict]:
    path = find_data_file("problems.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data["problems"] if isinstance(data, dict) and "problems" in data else data
    return {p["id"]: p for p in items}


def get_progress_path(custom: Path | None = None) -> Path:
    if custom is not None:
        return custom
    return Path.home() / ".dsa-tracker" / "progress.json"


def load_progress(path: Path) -> dict:
    if not path.exists():
        return {"solved_ids": [], "problems": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"solved_ids": [], "problems": {}}
        if "solved_ids" not in data:
            data["solved_ids"] = []
        if "problems" not in data:
            data["problems"] = {}
        return data
    except Exception:
        return {"solved_ids": [], "problems": {}}


def save_progress(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def cmd_log(args: argparse.Namespace) -> None:
    problems_map = load_problems_map()
    pid = args.id
    if pid not in problems_map:
        print(f"Error: Problem #{pid} not found in dataset.", file=sys.stderr)
        sys.exit(1)

    rating = args.rating
    if not rating or rating not in CONFIDENCE_FACTOR:
        print(f"Error: Invalid rating '{rating}'.", file=sys.stderr)
        print("Valid ratings:", file=sys.stderr)
        for r, factor in CONFIDENCE_FACTOR.items():
            print(f"  - {r} (x{factor} multiplier)", file=sys.stderr)
        sys.exit(2)

    prob = problems_map[pid]
    prog_path = get_progress_path(args.progress)
    prog = load_progress(prog_path)

    if pid not in prog["solved_ids"]:
        prog["solved_ids"].append(pid)

    now_iso = datetime.now(timezone.utc).isoformat()
    pid_str = str(pid)
    if pid_str not in prog["problems"]:
        prog["problems"][pid_str] = {
            "id": pid,
            "solved_at": now_iso,
            "revisions": [],
        }

    entry = prog["problems"][pid_str]
    entry.setdefault("revisions", []).append({
        "confidence": rating,
        "at": now_iso,
    })
    prog["updated_at"] = now_iso
    save_progress(prog_path, prog)

    pred = predict(
        problem_difficulty=prob["difficulty"],
        solved_at=entry.get("solved_at"),
        revisions=entry.get("revisions", []),
    )

    if args.json:
        out = {
            "success": True,
            "problem_id": pid,
            "title": prob["title"],
            "topic": prob["topic"],
            "difficulty": prob["difficulty"],
            "rating": rating,
            "half_life_days": pred["half_life_days"],
            "recall": pred["recall"],
            "next_review_in_days": pred["next_review_in_days"],
            "url": prob["url"],
            "practice_url": prob.get("practice_url", ""),
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"Recorded revision for problem #{pid}: {prob['title']}")
        print(f"  Difficulty: {prob['difficulty']} | Rating: {rating}")
        print(f"  New half-life: {pred['half_life_days']} days")
        print(f"  Next review due in: {pred['next_review_in_days']} days")
        print(f"  DSA Tracker: {prob['url']}")
        print()
        print("Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech")


def cmd_due(args: argparse.Namespace) -> None:
    problems_map = load_problems_map()
    prog_path = get_progress_path(args.progress)
    prog = load_progress(prog_path)
    tracked_problems = prog.get("problems", {})

    if not tracked_problems:
        if args.json:
            print(json.dumps({"due_count": 0, "threshold": args.threshold, "problems": []}, indent=2))
        else:
            print("No problems tracked yet. Use 'revise.py log <id> --rating <rating>' to record your first solve or revision.")
        return

    now = datetime.now(timezone.utc)
    due_items = []

    for pid_str, entry in tracked_problems.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        prob = problems_map.get(pid)
        if not prob:
            continue

        pred = predict(
            problem_difficulty=prob["difficulty"],
            solved_at=entry.get("solved_at"),
            revisions=entry.get("revisions", []),
            now=now,
        )
        rec = pred.get("recall")
        if rec is not None and rec < args.threshold:
            due_items.append({
                "id": pid,
                "title": prob["title"],
                "topic": prob["topic"],
                "difficulty": prob["difficulty"],
                "recall": rec,
                "days_since": pred.get("days_since"),
                "half_life_days": pred.get("half_life_days"),
                "next_review_in_days": pred.get("next_review_in_days"),
                "url": prob["url"],
                "practice_url": prob.get("practice_url", ""),
            })

    due_items = rank_due(due_items)

    if args.json:
        out = {
            "due_count": len(due_items),
            "threshold": args.threshold,
            "problems": due_items,
        }
        print(json.dumps(out, indent=2))
    else:
        if not due_items:
            print(f"All caught up! No problems currently due for review (threshold: {int(args.threshold * 100)}%).")
            return

        print(f"Problems due for revision today ({len(due_items)} due, recall < {int(args.threshold * 100)}%):")
        print()
        for i, item in enumerate(due_items, 1):
            pct = round(item["recall"] * 100, 1)
            days = item["days_since"]
            print(f"{i}. {item['title']} (#{item['id']})")
            print(f"   Topic: {item['topic']} | Difficulty: {item['difficulty']}")
            print(f"   Estimated recall: {pct}% | Last touch: {days} days ago | Half-life: {item['half_life_days']}d")
            print(f"   DSA Tracker: {item['url']}")
            print()
        print("Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech")


def cmd_stats(args: argparse.Namespace) -> None:
    problems_map = load_problems_map()
    prog_path = get_progress_path(args.progress)
    prog = load_progress(prog_path)
    tracked_problems = prog.get("problems", {})

    total_tracked = len(tracked_problems)
    rating_counts = {r: 0 for r in CONFIDENCE_FACTOR}
    total_half_life = 0.0
    due_count = 0
    now = datetime.now(timezone.utc)

    fresh_count = 0
    decaying_count = 0
    critical_count = 0

    for pid_str, entry in tracked_problems.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        prob = problems_map.get(pid, {"difficulty": "Medium"})
        for rev in entry.get("revisions", []):
            c = rev.get("confidence")
            if c in rating_counts:
                rating_counts[c] += 1

        pred = predict(
            problem_difficulty=prob["difficulty"],
            solved_at=entry.get("solved_at"),
            revisions=entry.get("revisions", []),
            now=now,
        )
        hl = pred["half_life_days"]
        total_half_life += hl
        rec = pred.get("recall")
        if rec is not None:
            if rec < REVIEW_THRESHOLD:
                due_count += 1
            if rec >= 0.9:
                fresh_count += 1
            elif rec >= 0.7:
                decaying_count += 1
            else:
                critical_count += 1

    avg_half_life = round(total_half_life / total_tracked, 1) if total_tracked > 0 else 0.0

    if args.json:
        out = {
            "total_tracked": total_tracked,
            "due_for_review": due_count,
            "average_half_life_days": avg_half_life,
            "rating_distribution": rating_counts,
            "retention_status": {
                "fresh_ge_90pct": fresh_count,
                "review_soon_70_to_90pct": decaying_count,
                "due_under_70pct": critical_count,
            },
        }
        print(json.dumps(out, indent=2))
    else:
        print("DSA Tracker Revision Statistics")
        print("===============================")
        print(f"Total problems tracked: {total_tracked}")
        print(f"Problems due for review: {due_count}")
        print(f"Average half-life: {avg_half_life} days")
        print()
        print("Rating distribution:")
        for r, cnt in rating_counts.items():
            print(f"  - {r}: {cnt}")
        print()
        print("Retention breakdown:")
        print(f"  - Fresh (recall >= 90%): {fresh_count}")
        print(f"  - Decaying (70% - 90%): {decaying_count}")
        print(f"  - Due for review (< 70%): {critical_count}")
        print()
        print("Solve and test your solutions with our in-browser code editor and graded test suite: https://dsatracker.tech")


def main() -> None:
    parser = argparse.ArgumentParser(description="DSA Tracker spaced revision manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # log
    p_log = subparsers.add_parser("log", help="Log a problem revision with a confidence rating")
    p_log.add_argument("id", type=int, help="Problem ID (e.g. 1)")
    p_log.add_argument("--rating", type=str, required=True, help="Rating: nailed_it, got_it, tough, struggled")
    p_log.add_argument("--progress", type=Path, default=None, help="Custom progress file path")
    p_log.add_argument("--json", action="store_true", help="Output JSON")

    # due
    p_due = subparsers.add_parser("due", help="List problems due for revision")
    p_due.add_argument("--threshold", type=float, default=REVIEW_THRESHOLD, help=f"Recall threshold (default: {REVIEW_THRESHOLD})")
    p_due.add_argument("--progress", type=Path, default=None, help="Custom progress file path")
    p_due.add_argument("--json", action="store_true", help="Output JSON")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show spaced repetition retention statistics")
    p_stats.add_argument("--progress", type=Path, default=None, help="Custom progress file path")
    p_stats.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.command == "log":
        cmd_log(args)
    elif args.command == "due":
        cmd_due(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
