from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from algorithms.fsrs import CardState, FSRSv5Scheduler
from models import Database
from utils.question_generator import (
    QUESTION_FORMAT_MULTIPLE_CHOICE,
    generate_question_entries,
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-me",
        DATABASE=os.path.join(app.root_path, "database.db"),
    )

    if test_config:
        app.config.update(test_config)

    db = Database(app.config["DATABASE"])
    db.init_db()
    scheduler = FSRSv5Scheduler()

    @app.get("/")
    def index():
        return render_template("index.html", stats=db.get_stats())

    @app.get("/study")
    def study():
        return render_template("study.html")

    @app.get("/history")
    def history():
        rows = db.get_recent_reviews(limit=50)
        return render_template("history.html", rows=rows)

    @app.post("/import_csv")
    def import_csv():
        upload = request.files.get("file")
        if not upload:
            flash("CSVファイルを選択してください。", "error")
            return redirect(url_for("index"))

        try:
            text = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            required = {"問題", "回答", "解説"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                flash("CSVヘッダーは 問題, 回答, 解説 が必要です。", "error")
                return redirect(url_for("index"))

            rows = []
            for row in reader:
                if not row.get("問題") or not row.get("回答"):
                    continue
                rows.append({"問題": row["問題"], "回答": row["回答"], "解説": row.get("解説", "")})

            if not rows:
                flash("有効なデータ行がありません。", "error")
                return redirect(url_for("index"))

            entries = generate_question_entries(rows)
            inserted = db.bulk_insert_cards(entries)
            flash(f"{inserted}件の問題を取り込みました。", "success")
        except Exception as exc:
            flash(f"取り込みに失敗しました: {exc}", "error")

        return redirect(url_for("index"))

    @app.get("/api/next-question")
    def api_next_question():
        card = db.get_next_due_card()
        if not card:
            return jsonify({"done": True, "message": "復習対象のカードはありません。"})

        options = json.loads(card["options_json"] or "[]")
        return jsonify(
            {
                "done": False,
                "card": {
                    "id": card["id"],
                    "question": card["question"],
                    "prompt": card["prompt"],
                    "format": card["question_format"],
                    "options": options,
                },
            }
        )

    @app.post("/api/answer")
    def api_answer():
        payload = request.get_json(silent=True) or {}
        card_id = int(payload.get("card_id", 0))
        card = db.get_card(card_id)
        if not card:
            return jsonify({"error": "card not found"}), 404

        user_answer = (payload.get("user_answer") or "").strip()
        expected = (card["answer"] or "").strip()
        correct = bool(payload.get("correct")) if "correct" in payload else user_answer == expected

        rating = payload.get("rating")
        if rating not in {"again", "hard", "good", "easy"}:
            rating = "good" if correct else "again"

        state = CardState(
            stability=float(card["stability"]),
            difficulty=float(card["difficulty"]),
            repetitions=int(card["repetitions"]),
            lapses=int(card["lapses"]),
            due_at=datetime.fromisoformat(card["due_at"]),
        )
        updated = scheduler.review(state, rating=rating, review_date=datetime.utcnow(), correct=correct)

        scheduled_days = max((updated.due_at - datetime.utcnow()).days, 1)
        next_state = "learning" if updated.repetitions < 5 else "review"

        db.update_card_schedule(
            card_id=card_id,
            stability=updated.stability,
            difficulty=updated.difficulty,
            repetitions=updated.repetitions,
            lapses=updated.lapses,
            due_at=updated.due_at,
            state=next_state,
        )
        db.insert_review(
            card_id=card_id,
            rating=rating,
            correct=correct,
            user_answer=user_answer,
            scheduled_days=scheduled_days,
            stability=updated.stability,
            difficulty=updated.difficulty,
        )

        return jsonify(
            {
                "correct": correct,
                "correct_answer": expected,
                "explanation": card["explanation"],
                "next_review_at": updated.due_at.isoformat(),
                "rating": rating,
            }
        )

    @app.get("/api/stats")
    def api_stats():
        return jsonify(db.get_stats())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
