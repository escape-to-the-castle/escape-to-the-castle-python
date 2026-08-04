import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.game.entities import Player
from src.main import GROUND_Y, Game, PhaseId


def test_game_initializes_and_renders():
    game = Game()
    game.update(1 / 60, set())
    game.draw()

    assert game.running is True
    assert game.state.name in {"MENU", "PLAYING", "QUESTION", "FEEDBACK", "GAME_OVER", "VICTORY"}


def test_phase_1_hole_respawn_is_on_solid_ground():
    game = Game()
    game.start_phase(PhaseId.PHASE_1)
    safe_x = game.last_safe_x

    # Being airborne over the first hole must not replace the checkpoint.
    game.player.x = 580
    game.player.y = 500
    game.player.on_ground = False
    game.on_hazard("hole")

    assert game.player.x == safe_x
    assert game.player.rect.bottom == GROUND_Y
    assert not any(game.player.rect.colliderect(hole.rect) for hole in game.holes)
    assert any(
        game.player.rect.left >= segment.rect.left and game.player.rect.right <= segment.rect.right
        for segment in game.ground_segments
    )


def test_phase_1_platform_height_steps_are_reachable():
    game = Game()
    layout = game.build_phase_1_layout()
    maximum_jump_rise = Player.JUMP_SPEED**2 / (2 * Player.GRAVITY)
    highest_reachable_rise = 0

    for platform in sorted(layout.platforms, key=lambda item: item.rect.x):
        platform_rise = GROUND_Y - platform.rect.top
        assert platform_rise - highest_reachable_rise <= maximum_jump_rise
        highest_reachable_rise = max(highest_reachable_rise, platform_rise)
