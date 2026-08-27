from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    explanation TEXT,
                    question_format TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    options_json TEXT,
                    due_at TEXT NOT NULL,
                    stability REAL NOT NULL DEFAULT 0.4,
                    difficulty REAL NOT NULL DEFAULT 5.0,
                    repetitions INTEGER NOT NULL DEFAULT 0,
                    lapses INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    user_answer TEXT,
                    scheduled_days INTEGER NOT NULL,
                    stability REAL NOT NULL,
                    difficulty REAL NOT NULL,
                    FOREIGN KEY(card_id) REFERENCES cards(id)
                );
                """
            )

    def bulk_insert_cards(self, entries: list[dict[str, str | list[str]]]) -> int:
        now = datetime.utcnow().isoformat()
        due = datetime.utcnow().isoformat()
        payload = [
            (
                e["question"],
                e["answer"],
                e["explanation"],
                e["format"],
                e["prompt"],
                json.dumps(e["options"], ensure_ascii=False),
                due,
                now,
                now,
            )
            for e in entries
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO cards (
                    question, answer, explanation, question_format, prompt, options_json,
                    due_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            return len(payload)

    def get_card(self, card_id: int):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()

    def get_next_due_card(self):
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM cards
                WHERE due_at <= ?
                ORDER BY due_at ASC, id ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()

    def update_card_schedule(self, card_id: int, stability: float, difficulty: float, repetitions: int, lapses: int, due_at: datetime, state: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE cards
                SET stability = ?, difficulty = ?, repetitions = ?, lapses = ?, due_at = ?, state = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    stability,
                    difficulty,
                    repetitions,
                    lapses,
                    due_at.isoformat(),
                    state,
                    datetime.utcnow().isoformat(),
                    card_id,
                ),
            )

    def insert_review(self, card_id: int, rating: str, correct: bool, user_answer: str, scheduled_days: int, stability: float, difficulty: float) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO reviews (card_id, reviewed_at, rating, correct, user_answer, scheduled_days, stability, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    datetime.utcnow().isoformat(),
                    rating,
                    1 if correct else 0,
                    user_answer,
                    scheduled_days,
                    stability,
                    difficulty,
                ),
            )

    def get_stats(self) -> dict[str, int]:
        now = datetime.utcnow().isoformat()
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
            mastered = conn.execute("SELECT COUNT(*) FROM cards WHERE repetitions >= 5 AND lapses = 0").fetchone()[0]
            due = conn.execute("SELECT COUNT(*) FROM cards WHERE due_at <= ?", (now,)).fetchone()[0]
            reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        return {
            "total_cards": total,
            "mastered_cards": mastered,
            "in_progress_cards": max(total - mastered, 0),
            "due_cards": due,
            "total_reviews": reviews,
        }

    def get_recent_reviews(self, limit: int = 20):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT r.*, c.question
                FROM reviews r
                JOIN cards c ON c.id = r.card_id
                ORDER BY r.reviewed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
