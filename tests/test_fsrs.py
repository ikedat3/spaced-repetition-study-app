from datetime import datetime

from algorithms.fsrs import CardState, FSRSv5Scheduler


def test_fsrs_review_updates_due_and_repetitions():
    scheduler = FSRSv5Scheduler()
    now = datetime(2026, 1, 1)
    state = CardState(stability=1.0, difficulty=5.0, repetitions=0, lapses=0, due_at=now)

    updated = scheduler.review(state, rating="good", review_date=now, correct=True)

    assert updated.repetitions == 1
    assert updated.lapses == 0
    assert updated.due_at > now
