from utils.question_generator import generate_multiple_choice_options, generate_question_entries


def test_multiple_choice_options_have_four_entries_and_correct_answer():
    options = generate_multiple_choice_options("東京", ["大阪", "名古屋", "福岡", "札幌"])
    assert len(options) == 4
    assert "東京" in options
    assert len(set(options)) == 4


def test_generate_question_entries_creates_expected_fields():
    rows = [{"問題": "日本の首都は？", "回答": "東京", "解説": "説明"}]
    entries = generate_question_entries(rows)
    assert len(entries) == 1
    assert entries[0]["question"] == "日本の首都は？"
    assert entries[0]["answer"] == "東京"
    assert "format" in entries[0]
