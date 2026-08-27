from __future__ import annotations

import random
from typing import Iterable


QUESTION_FORMAT_MULTIPLE_CHOICE = "multiple_choice"
QUESTION_FORMAT_FILL_BLANK = "fill_blank"
QUESTION_FORMAT_DIRECT = "direct"


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def auto_detect_format(question: str, answer: str) -> str:
    q = normalize_text(question)
    a = normalize_text(answer)

    if a and a in q and len(a) >= 2:
        return QUESTION_FORMAT_FILL_BLANK
    if q.endswith("？") or q.endswith("?"):
        if len(a.split()) <= 3:
            return QUESTION_FORMAT_DIRECT
    return QUESTION_FORMAT_MULTIPLE_CHOICE


def generate_multiple_choice_options(
    correct_answer: str,
    answer_pool: Iterable[str],
    option_count: int = 4,
) -> list[str]:
    correct = normalize_text(correct_answer)
    pool = [normalize_text(a) for a in answer_pool if normalize_text(a) and normalize_text(a) != correct]
    deduped = list(dict.fromkeys(pool))

    distractor_count = max(0, option_count - 1)
    if len(deduped) >= distractor_count:
        distractors = random.sample(deduped, distractor_count)
    else:
        distractors = deduped[:]
        while len(distractors) < distractor_count:
            distractors.append(f"{correct} (類似選択肢{len(distractors) + 1})")

    options = distractors + [correct]
    random.shuffle(options)
    return options


def generate_question_entries(rows: list[dict[str, str]]) -> list[dict[str, str | list[str]]]:
    answers = [normalize_text(row.get("回答", "")) for row in rows]
    entries: list[dict[str, str | list[str]]] = []

    for row in rows:
        question = normalize_text(row.get("問題", ""))
        answer = normalize_text(row.get("回答", ""))
        explanation = normalize_text(row.get("解説", ""))

        q_format = auto_detect_format(question, answer)
        prompt = question
        options: list[str] = []

        if q_format == QUESTION_FORMAT_FILL_BLANK:
            prompt = question.replace(answer, "____", 1) if answer and answer in question else f"空欄を埋めてください: {question}"
        elif q_format == QUESTION_FORMAT_MULTIPLE_CHOICE:
            options = generate_multiple_choice_options(answer, answers)

        entries.append(
            {
                "question": question,
                "answer": answer,
                "explanation": explanation,
                "format": q_format,
                "prompt": prompt,
                "options": options,
            }
        )

    return entries
