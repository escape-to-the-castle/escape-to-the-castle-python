from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: int
    category: str
    difficulty: int
    text: str
    options: list[str]
    correct_index: int
    explanation: str


class QuestionBank:
    def __init__(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as file:
            raw_questions = json.load(file)

        self._questions = [Question(**item) for item in raw_questions]
        if not self._questions:
            raise ValueError("O banco de perguntas está vazio.")
        self._remaining_questions: list[Question] = []
        self.reset_round()

    def reset_round(self) -> None:
        """Prepara uma rodada com cada pergunta aparecendo no máximo uma vez."""
        self._remaining_questions = self._questions.copy()
        random.shuffle(self._remaining_questions)

    def next_question(self) -> Question:
        if not self._remaining_questions:
            raise RuntimeError("Não há mais perguntas inéditas nesta rodada.")
        return self._remaining_questions.pop()
