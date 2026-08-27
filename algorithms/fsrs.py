from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


RATINGS = {"again", "hard", "good", "easy"}


@dataclass
class CardState:
    stability: float = 0.4
    difficulty: float = 5.0
    repetitions: int = 0
    lapses: int = 0
    due_at: datetime | None = None


class FSRSv5Scheduler:
    """Lightweight FSRSv5-inspired scheduler for practical web usage."""

    def __init__(self) -> None:
        self.interval_factor = {
            "again": 0.1,
            "hard": 0.6,
            "good": 1.0,
            "easy": 1.5,
        }

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _next_interval_days(self, stability: float, rating: str) -> int:
        days = round(max(0.04, stability) * self.interval_factor[rating])
        return max(1, days)

    def review(
        self,
        state: CardState,
        rating: str,
        review_date: datetime | None = None,
        correct: bool | None = None,
    ) -> CardState:
        if rating not in RATINGS:
            raise ValueError(f"Unknown rating: {rating}")

        now = review_date or datetime.utcnow()
        correct_answer = correct if correct is not None else rating in {"good", "easy"}

        if not correct_answer or rating == "again":
            new_difficulty = self._clamp(state.difficulty + 0.6, 1.0, 10.0)
            new_stability = self._clamp(state.stability * 0.45, 0.1, 365.0)
            lapses = state.lapses + 1
            repetitions = max(0, state.repetitions - 1)
        else:
            rating_bonus = {"hard": 0.85, "good": 1.2, "easy": 1.5}[rating]
            difficulty_shift = {"hard": 0.15, "good": -0.05, "easy": -0.15}[rating]
            new_difficulty = self._clamp(state.difficulty + difficulty_shift, 1.0, 10.0)
            growth = 1.0 + ((11 - new_difficulty) / 10.0) * rating_bonus
            new_stability = self._clamp(state.stability * growth, 0.1, 3650.0)
            lapses = state.lapses
            repetitions = state.repetitions + 1

        next_days = self._next_interval_days(new_stability, rating)
        due_at = now + timedelta(days=next_days)

        return CardState(
            stability=new_stability,
            difficulty=new_difficulty,
            repetitions=repetitions,
            lapses=lapses,
            due_at=due_at,
        )
