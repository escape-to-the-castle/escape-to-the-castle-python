from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Action(Enum):
    START = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    JUMP = auto()
    ROLL = auto()
    ANSWER_1 = auto()
    ANSWER_2 = auto()
    ANSWER_3 = auto()
    ANSWER_4 = auto()
    RESTART = auto()
    QUIT = auto()


@dataclass
class OutputState:
    progress: float = 0.0
    lives: int = 3
    coins: int = 0
    feedback: str = "neutral"


class HardwareInterface:
    def poll_actions(self) -> set[Action]:
        raise NotImplementedError

    def update_outputs(self, state: OutputState) -> None:
        pass

    def close(self) -> None:
        pass
