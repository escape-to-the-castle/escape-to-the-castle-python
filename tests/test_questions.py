import json
from pathlib import Path


def test_question_file_structure():
    path = Path(__file__).resolve().parents[1] / "data" / "questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    assert questions
    for question in questions:
        assert len(question["options"]) in range(2, 5)
        assert 0 <= question["correct_index"] < len(question["options"])
        assert question["explanation"]
