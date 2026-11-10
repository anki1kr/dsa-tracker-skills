#!/usr/bin/env python3
"""Build data snapshot for dsa-tracker-skills.

Extracts a clean, minimal public snapshot of problems from DSA Tracker's curated dataset
and roles from the public API, asserts dataset invariants (370 problems, 75 consensus),
and verifies live problem URLs with rate-limited checks.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "DSA-Tracker" / "app" / "dsa_tracker_dataset.json"
ROLES_API_URL = "https://dsatracker.tech/api/roles"
USER_AGENT = "dsa-tracker-skills-builder/0.1.0 (+https://dsatracker.tech)"


def problem_slug(title: str) -> str:
    """Exact slug function used by DSA Tracker's /problem/[slug] route."""
    cleaned = title.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")


def build_problems(dataset_path: Path) -> dict:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_problems = json.load(f)

    if len(raw_problems) != 370:
        raise ValueError(f"Expected 370 problems, found {len(raw_problems)}")

    curated_sheets = ("Striver A2Z", "Love Babbar 450", "Apna College")
    problems = []

    for p in raw_problems:
        raw_source = p.get("source") or []
        sheets = [s for s in curated_sheets if s in raw_source]
        # Consensus: problem appears in all three sheets
        is_consensus = len({*raw_source}.intersection(curated_sheets)) >= 3
        title = p["title"]
        slug = problem_slug(title)

        # STRICT: ONLY id, title, topic, difficulty, sheets, consensus, url, practice_url
        clean_problem = {
            "id": int(p["id"]),
            "title": str(title),
            "topic": str(p["topic"]),
            "difficulty": str(p["difficulty"]),
            "sheets": sheets,
            "consensus": bool(is_consensus),
            "url": f"https://dsatracker.tech/problem/{slug}",
            "practice_url": str(p.get("link") or ""),
        }
        problems.append(clean_problem)

    consensus_count = sum(1 for p in problems if p["consensus"])
    if consensus_count != 75:
        raise AssertionError(f"Consensus count invariant failed: expected 75, got {consensus_count}")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "built": today_str,
        "source": "https://dsatracker.tech",
        "total": len(problems),
        "consensus_count": consensus_count,
        "problems": problems,
    }


def fetch_roles() -> dict:
    req = urllib.request.Request(ROLES_API_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Roles API returned status {resp.status}")
        payload = json.loads(resp.read().decode("utf-8"))

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "built": today_str,
        "source": "https://dsatracker.tech",
        "roles": payload["roles"],
        "default_role": payload.get("default_role", "SDE / Software Engineer"),
        "role_topic_map": payload["role_topic_map"],
    }


def verify_urls(problems: list[dict], count: int = 15) -> list[str]:
    """Verify live problem URLs sequentially with a 2-second pause."""
    if len(problems) < count:
        sample = problems
    else:
        step = len(problems) // count
        sample = [problems[i * step] for i in range(count)]

    print(f"Verifying {len(sample)} problem URLs from https://dsatracker.tech (2s pause between requests)...")
    verified = []
    for i, p in enumerate(sample, 1):
        url = p["url"]
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                raise AssertionError(f"URL {url} returned HTTP {resp.status}")
        print(f"  [{i}/{len(sample)}] 200 OK: {url}")
        verified.append(url)
        if i < len(sample):
            time.sleep(2.0)
    return verified


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DSA Tracker skills data snapshot")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH, help="Path to dsa_tracker_dataset.json")
    parser.add_argument("--out-dir", type=Path, default=None, help="Write here instead of every skill's own data/ folder")
    parser.add_argument("--skip-verify-urls", action="store_true", help="Skip live URL checks")
    args = parser.parse_args()

    # Each skill carries its own copy: `npx skills add` installs one skill folder, never the repo root.
    skills = Path(__file__).resolve().parent.parent / "skills"
    targets = {
        "problems.json": [skills / "dsa-next" / "data", skills / "dsa-sheets" / "data", skills / "dsa-revise" / "data"],
        "roles.json": [skills / "dsa-next" / "data"],
    }
    if args.out_dir is not None:
        targets = {name: [args.out_dir] for name in targets}

    def write(name: str, payload: dict) -> None:
        for folder in targets[name]:
            folder.mkdir(parents=True, exist_ok=True)
            with open(folder / name, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"Wrote {folder / name}")

    print("Building problems.json...")
    problems_data = build_problems(args.dataset)
    write("problems.json", problems_data)
    print(f"{len(problems_data['problems'])} problems; consensus count verified: {problems_data['consensus_count']}")

    print("\nFetching roles.json...")
    roles_data = fetch_roles()
    write("roles.json", roles_data)
    print(f"{len(roles_data['roles'])} roles")

    if not args.skip_verify_urls:
        print("\nVerifying problem URLs...")
        verify_urls(problems_data["problems"], count=15)
        print("All 15 problem URLs responded with HTTP 200.")
    else:
        print("\nSkipped live URL verification.")


if __name__ == "__main__":
    main()
