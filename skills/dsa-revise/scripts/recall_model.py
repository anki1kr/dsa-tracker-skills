"""Recall probability model: port of DSA Tracker's recall_model.py.

Deterministic exponential forgetting curve with per-problem half-life.
Standard library only.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

H0_BY_DIFFICULTY: dict[str, float] = {"Easy": 3.0, "Medium": 2.0, "Hard": 1.5}
CONFIDENCE_FACTOR: dict[str, float] = {
    "nailed_it": 2.5,
    "got_it": 2.0,
    "tough": 1.0,
    "struggled": 0.5,
}
HALF_LIFE_MIN: float = 0.5
HALF_LIFE_MAX: float = 365.0
REVIEW_THRESHOLD: float = 0.7


def _as_utc_naive(dt: datetime | str | None) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        if not dt:
            return None
        try:
            if dt.endswith("Z"):
                dt = dt[:-1] + "+00:00"
            parsed = datetime.fromisoformat(dt)
            return _as_utc_naive(parsed)
        except Exception:
            return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _days_since(last_touch: datetime | str | None, now: datetime | None = None) -> float | None:
    last = _as_utc_naive(last_touch)
    if last is None:
        return None
    ref = _as_utc_naive(now or datetime.now(timezone.utc))
    delta = ref - last
    if delta.total_seconds() < 0:
        return 0.0
    return delta.total_seconds() / 86400.0


def recall_probability(half_life_days: float, days_since_last_touch: float | None) -> float | None:
    if days_since_last_touch is None:
        return None
    if half_life_days <= 0:
        return 0.0
    prob = 2.0 ** (-days_since_last_touch / half_life_days)
    return max(0.0, min(1.0, prob))


def compute_half_life(difficulty: str, revisions: list[dict]) -> float:
    base = H0_BY_DIFFICULTY.get(difficulty, H0_BY_DIFFICULTY["Medium"])
    half_life = base
    for rev in sorted(revisions, key=lambda r: r.get("at") or ""):
        confidence = rev.get("confidence")
        if confidence in CONFIDENCE_FACTOR:
            half_life *= CONFIDENCE_FACTOR[confidence]
    return max(HALF_LIFE_MIN, min(HALF_LIFE_MAX, half_life))


def last_touch_time(solved_at: str | None, revisions: list[dict]) -> datetime | str | None:
    if not revisions:
        return solved_at
    latest_rev = max(revisions, key=lambda r: r.get("at") or "")
    rev_at = latest_rev.get("at")
    if rev_at:
        return rev_at
    return solved_at


def next_review_in_days(half_life_days: float, threshold: float = REVIEW_THRESHOLD) -> float:
    if half_life_days <= 0:
        return 0.0
    if threshold <= 0:
        return float("inf")
    if threshold >= 1:
        return 0.0
    days = -half_life_days * math.log2(threshold)
    return max(0.0, days)


def predict(
    problem_difficulty: str,
    solved_at: str | None,
    revisions: list[dict],
    now: datetime | None = None,
) -> dict[str, Any]:
    half_life = compute_half_life(problem_difficulty, revisions)
    last = last_touch_time(solved_at, revisions)
    days = _days_since(last, now)
    rec = recall_probability(half_life, days) if days is not None else None
    nxt = next_review_in_days(half_life) if days is not None else 0.0
    return {
        "half_life_days": round(half_life, 1),
        "recall": round(rec, 4) if rec is not None else None,
        "days_since": round(days, 2) if days is not None else None,
        "next_review_in_days": round(nxt, 2),
    }


def rank_due(items: list[dict]) -> list[dict]:
    def sort_key(item: dict) -> tuple[int, float]:
        rec = item.get("recall")
        if rec is None:
            return (1, 0.0)
        return (0, rec)

    return sorted(items, key=sort_key)
