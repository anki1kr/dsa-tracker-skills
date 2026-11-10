"""Unit tests and structural validators for dsa-tracker-skills.

Runs completely offline using only the standard library.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIRS = [ROOT_DIR / "skills" / s / "scripts" for s in ("dsa-next", "dsa-sheets", "dsa-revise")]
SKILLS_DIR = ROOT_DIR / "skills"
DATA_DIR = ROOT_DIR / "skills" / "dsa-next" / "data"

for _d in SCRIPTS_DIRS:
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import recall_model
import next as next_script
import sheets as sheets_script
import revise as revise_script


class TestManifestsAndSkills(unittest.TestCase):
    """Validator ensuring plugin manifests and SKILL.md files comply with specifications."""

    def test_plugin_manifest(self) -> None:
        plugin_file = ROOT_DIR / ".claude-plugin" / "plugin.json"
        self.assertTrue(plugin_file.exists(), "plugin.json must exist")
        with open(plugin_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest.get("name"), "dsa-tracker")
        self.assertEqual(manifest.get("version"), "0.1.0")
        self.assertEqual(manifest.get("homepage"), "https://dsatracker.tech")
        self.assertIn("author", manifest)
        skills = manifest.get("skills", [])
        self.assertIn("./skills/dsa-next", skills)
        self.assertIn("./skills/dsa-revise", skills)
        self.assertIn("./skills/dsa-sheets", skills)

    def test_marketplace_manifest(self) -> None:
        market_file = ROOT_DIR / ".claude-plugin" / "marketplace.json"
        self.assertTrue(market_file.exists(), "marketplace.json must exist")
        with open(market_file, "r", encoding="utf-8") as f:
            market = json.load(f)
        plugins = market.get("plugins", [])
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].get("name"), "dsa-tracker")
        self.assertEqual(plugins[0].get("source"), "./")

    def test_skills_frontmatter_and_content(self) -> None:
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"SKILL.md missing in {skill_dir.name}")
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()

            # Frontmatter check
            self.assertTrue(content.startswith("---\n"), f"Missing YAML frontmatter in {skill_dir.name}")
            end_fm = content.find("\n---\n", 4)
            self.assertNotEqual(end_fm, -1, f"Unclosed YAML frontmatter in {skill_dir.name}")
            fm_text = content[4:end_fm]

            fm_dict = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm_dict[k.strip()] = v.strip().strip("'\"")

            self.assertEqual(fm_dict.get("name"), skill_dir.name, "Frontmatter name must match directory name")
            self.assertTrue(len(fm_dict.get("description", "")) > 10, "Description must be non-empty")

            # Style constraints
            self.assertNotIn("!", content, f"Exclamation mark found in {skill_dir.name}/SKILL.md")
            self.assertNotIn("—", content, f"Em-dash found in {skill_dir.name}/SKILL.md")
            self.assertNotIn("–", content, f"En-dash found in {skill_dir.name}/SKILL.md")
            self.assertIn("https://dsatracker.tech", content, "DSA Tracker link must be present")


class TestDataInvariants(unittest.TestCase):
    """Verify offline data snapshot integrity."""

    def test_problems_data(self) -> None:
        p_path = DATA_DIR / "problems.json"
        self.assertTrue(p_path.exists())
        with open(p_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("source"), "https://dsatracker.tech")
        problems = data.get("problems", [])
        self.assertEqual(len(problems), 370, "Must contain exactly 370 problems")

        consensus_count = sum(1 for p in problems if p.get("consensus") is True)
        self.assertEqual(consensus_count, 75, "Consensus 75 invariant failed")

        allowed_keys = {"id", "title", "topic", "difficulty", "sheets", "consensus", "url", "practice_url"}
        for p in problems:
            self.assertEqual(set(p.keys()), allowed_keys, f"Extraneous or missing keys in problem #{p.get('id')}")
            self.assertTrue(p["url"].startswith("https://dsatracker.tech/problem/"))

    def test_roles_data(self) -> None:
        r_path = DATA_DIR / "roles.json"
        self.assertTrue(r_path.exists())
        with open(r_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("source"), "https://dsatracker.tech")
        roles = data.get("roles", [])
        self.assertGreaterEqual(len(roles), 25)
        self.assertIn("Frontend Engineer", roles)
        self.assertIn("Backend Engineer", roles)
        self.assertIn("SDE / Software Engineer", roles)

        role_map = data.get("role_topic_map", {})
        self.assertIn("Frontend Engineer", role_map)
        fe_map = role_map["Frontend Engineer"]
        self.assertIn("core", fe_map)
        self.assertIn("medium", fe_map)
        self.assertIn("low", fe_map)


class TestRecallModelPort(unittest.TestCase):
    """Compare port implementation against original recall_model.py in DSA-Tracker."""

    def test_direct_calculations(self) -> None:
        # Case 1: Initial half life
        self.assertEqual(recall_model.compute_half_life("Easy", []), 3.0)
        self.assertEqual(recall_model.compute_half_life("Medium", []), 2.0)
        self.assertEqual(recall_model.compute_half_life("Hard", []), 1.5)

        # Case 2: Multiplier
        rev_got_it = [{"confidence": "got_it", "at": "2026-11-01T00:00:00Z"}]
        self.assertEqual(recall_model.compute_half_life("Easy", rev_got_it), 6.0)

        # Case 3: Clamping
        self.assertGreaterEqual(recall_model.compute_half_life("Hard", [{"confidence": "struggled", "at": "1"}] * 10), 0.5)

        # Case 4: Recall decay calculation
        # 1 half-life elapsed -> recall = 0.5
        prob = recall_model.recall_probability(half_life_days=4.0, days_since_last_touch=4.0)
        self.assertAlmostEqual(prob or 0.0, 0.5, places=3)

        # Case 5: Zero days elapsed -> recall = 1.0
        prob_zero = recall_model.recall_probability(half_life_days=5.0, days_since_last_touch=0.0)
        self.assertAlmostEqual(prob_zero or 0.0, 1.0, places=3)

        # Case 6: Next review days calculation
        nxt = recall_model.next_review_in_days(half_life_days=2.0, threshold=0.7)
        self.assertGreater(nxt, 0.0)

    def test_compare_with_original_dsa_tracker_recall_model(self) -> None:
        original_path = Path(__file__).resolve().parents[2] / "DSA-Tracker" / "app" / "services" / "recall_model.py"
        if not original_path.exists():
            self.skipTest("DSA-Tracker repository recall_model.py not accessible at local path")

        import importlib.util

        spec = importlib.util.spec_from_file_location("original_recall_model", str(original_path))
        if spec is None or spec.loader is None:
            self.skipTest("Could not create module spec for original recall_model")
        orig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orig)

        # Case 1: Constants
        self.assertEqual(recall_model.H0_BY_DIFFICULTY, orig.H0_BY_DIFFICULTY)
        self.assertEqual(recall_model.CONFIDENCE_FACTOR, orig.CONFIDENCE_FACTOR)
        self.assertEqual(recall_model.HALF_LIFE_MIN, orig.HALF_LIFE_MIN)
        self.assertEqual(recall_model.HALF_LIFE_MAX, orig.HALF_LIFE_MAX)
        self.assertEqual(recall_model.REVIEW_THRESHOLD, orig.REVIEW_THRESHOLD)

        # Case 2: compute_half_life
        revisions = [
            {"confidence": "got_it", "at": "2026-11-01T00:00:00Z"},
            {"confidence": "nailed_it", "at": "2026-11-03T00:00:00Z"},
        ]
        self.assertEqual(
            recall_model.compute_half_life("Medium", revisions),
            orig.compute_half_life("Medium", revisions),
        )

        # Case 3: recall_probability
        self.assertEqual(
            recall_model.recall_probability(3.5, 2.1),
            orig.recall_probability(3.5, 2.1),
        )

        # Case 4: next_review_in_days
        self.assertEqual(
            recall_model.next_review_in_days(4.2, 0.7),
            orig.next_review_in_days(4.2, 0.7),
        )

        # Case 5: predict
        now_dt = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
        pred_local = recall_model.predict("Hard", "2026-11-01T00:00:00Z", revisions, now=now_dt)
        pred_orig = orig.predict("Hard", "2026-11-01T00:00:00Z", revisions, now=now_dt)
        self.assertEqual(pred_local, pred_orig)

        # Case 6: rank_due
        due_sample = [{"id": 1, "recall": 0.8}, {"id": 2, "recall": 0.2}, {"id": 3, "recall": None}]
        self.assertEqual(recall_model.rank_due(due_sample), orig.rank_due(due_sample))


class TestDsaNext(unittest.TestCase):
    """Test recommendation ordering and CLI options."""

    def test_role_order(self) -> None:
        roles_data = next_script.load_roles_data()
        problems = next_script.load_problems_data()
        role, recs = next_script.get_recommendations(
            role="Frontend Engineer",
            roles_data=roles_data,
            problems=problems,
            solved_ids={1},  # Two Sum solved
            count=3,
        )
        self.assertEqual(role, "Frontend Engineer")
        self.assertEqual(len(recs), 3)
        # First topic is Arrays, problem #1 is solved, next should be #2 Min and Max
        self.assertEqual(recs[0]["id"], 2)
        self.assertEqual(recs[0]["topic"], "Arrays")
        self.assertEqual(recs[0]["difficulty"], "Easy")

    def test_unknown_role_exit(self) -> None:
        cmd = [sys.executable, str(ROOT_DIR / "skills" / "dsa-next" / "scripts" / "next.py"), "--role", "NonExistentRole123"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("Valid roles:", res.stderr)


class TestDsaSheets(unittest.TestCase):
    """Test sheets comparison and consensus checks."""

    def test_compare_facts(self) -> None:
        # Computed from the snapshot; these are the numbers https://dsatracker.tech/coverage states.
        c = sheets_script.coverage(sheets_script.load_problems())
        self.assertEqual(c["total"], 370)
        self.assertEqual(c["all_three"], 75)
        curated = {s["name"]: s["curated"] for s in c["sheets"]}
        self.assertEqual(curated, {"Striver A2Z": 315, "Love Babbar 450": 248, "Apna College": 104})
        striver = next(s for s in c["sheets"] if s["name"] == "Striver A2Z")
        self.assertEqual(striver["liveRows"], 495)

    def test_output_prints_on_a_windows_console(self) -> None:
        # The set-intersection sign crashed `compare` on cp1252 consoles; every script's output must be plain ASCII.
        for script in ("dsa-next/scripts/next.py", "dsa-sheets/scripts/sheets.py", "dsa-revise/scripts/revise.py"):
            text = (SKILLS_DIR / script).read_text(encoding="utf-8")
            self.assertTrue(text.isascii(), f"{script} contains non-ASCII characters")

    def test_consensus_problems(self) -> None:
        problems = sheets_script.load_problems()
        consensus = [p for p in problems if p.get("consensus")]
        self.assertEqual(len(consensus), 75)

    def test_which_lookup(self) -> None:
        problems = sheets_script.load_problems()
        two_sum = next(p for p in problems if p["id"] == 1)
        self.assertEqual(two_sum["title"], "Two Sum")
        self.assertEqual(len(two_sum["sheets"]), 3)
        self.assertTrue(two_sum["consensus"])


class TestDsaRevise(unittest.TestCase):
    """Test revise command handling with isolated state."""

    def setUp(self) -> None:
        self.test_prog = ROOT_DIR / "tests" / "temp_test_progress.json"
        if self.test_prog.exists():
            self.test_prog.unlink()

    def tearDown(self) -> None:
        if self.test_prog.exists():
            self.test_prog.unlink()

    def test_log_and_stats(self) -> None:
        # Log problem 1
        cmd_log = [
            sys.executable,
            str(ROOT_DIR / "skills" / "dsa-revise" / "scripts" / "revise.py"),
            "log",
            "1",
            "--rating",
            "nailed_it",
            "--progress",
            str(self.test_prog),
            "--json",
        ]
        res_log = subprocess.run(cmd_log, capture_output=True, text=True)
        self.assertEqual(res_log.returncode, 0)
        data_log = json.loads(res_log.stdout)
        self.assertTrue(data_log["success"])
        self.assertEqual(data_log["problem_id"], 1)
        self.assertEqual(data_log["half_life_days"], 7.5)  # 3.0 * 2.5 = 7.5

        # Check stats
        cmd_stats = [
            sys.executable,
            str(ROOT_DIR / "skills" / "dsa-revise" / "scripts" / "revise.py"),
            "stats",
            "--progress",
            str(self.test_prog),
            "--json",
        ]
        res_stats = subprocess.run(cmd_stats, capture_output=True, text=True)
        self.assertEqual(res_stats.returncode, 0)
        data_stats = json.loads(res_stats.stdout)
        self.assertEqual(data_stats["total_tracked"], 1)
        self.assertEqual(data_stats["rating_distribution"]["nailed_it"], 1)


if __name__ == "__main__":
    unittest.main()
