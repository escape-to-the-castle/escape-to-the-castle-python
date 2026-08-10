import json
from pathlib import Path

from src.education.question_bank import QuestionBank


def test_question_file_structure():
    path = Path(__file__).resolve().parents[1] / "data" / "questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    assert questions
    for question in questions:
        assert len(question["options"]) in range(2, 5)
        assert 0 <= question["correct_index"] < len(question["options"])
        assert question["explanation"]


def test_questions_do_not_repeat_during_a_round():
    path = Path(__file__).resolve().parents[1] / "data" / "questions.json"
    bank = QuestionBank(path)
    expected_count = len(json.loads(path.read_text(encoding="utf-8")))

    selected_ids = [bank.next_question().id for _ in range(expected_count)]

    assert len(selected_ids) == len(set(selected_ids))
    try:
        bank.next_question()
    except RuntimeError as error:
        assert "inéditas" in str(error)
    else:
        raise AssertionError("O banco não deve repetir perguntas ao esgotar a rodada")
