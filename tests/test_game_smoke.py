import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.main import Game


def test_game_initializes_and_renders():
    game = Game()
    game.update(1 / 60, set())
    game.draw()

    assert game.running is True
    assert game.state.name in {"PLAYING", "QUESTION", "FEEDBACK", "GAME_OVER", "VICTORY"}
