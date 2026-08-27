import io

from app import create_app


def test_import_and_answer_flow(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app({"TESTING": True, "DATABASE": str(db_path), "SECRET_KEY": "test"})
    client = app.test_client()

    csv_content = "問題,回答,解説\n日本の首都は？,東京,説明\n"
    res = client.post(
        "/import_csv",
        data={"file": (io.BytesIO(csv_content.encode("utf-8")), "cards.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert res.status_code == 200

    next_q = client.get("/api/next-question")
    payload = next_q.get_json()
    assert payload["done"] is False
    card_id = payload["card"]["id"]

    ans = client.post("/api/answer", json={"card_id": card_id, "user_answer": "東京"})
    ans_json = ans.get_json()
    assert ans_json["correct"] is True
    assert "next_review_at" in ans_json
