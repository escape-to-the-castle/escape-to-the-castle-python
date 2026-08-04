import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.game.levels import (
    PHASE_1_PLATFORMS,
    PlatformSpec,
    build_phase_1_layout,
    maximum_jump_rise,
    validate_platform_specs,
)
from src.main import GROUND_Y, Game, PhaseId


def test_game_initializes_and_renders():
    game = Game()
    game.update(1 / 60, set())
    game.draw()

    assert game.running is True
    assert game.state.name in {"MENU", "PLAYING", "QUESTION", "FEEDBACK", "GAME_OVER", "VICTORY"}


def test_gameplay_phase_renders_with_all_visual_constants():
    game = Game()
    game.start_phase(PhaseId.PHASE_1)
    game.update(1 / 60, set())
    game.draw()

    assert game.player.rect.bottom == GROUND_Y


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
    validate_platform_specs(PHASE_1_PLATFORMS)
    layout = build_phase_1_layout()

    actual_rises = [GROUND_Y - platform.rect.top for platform in layout.platforms]
    assert actual_rises == [spec.rise for spec in PHASE_1_PLATFORMS]
    assert PHASE_1_PLATFORMS[4].rise <= maximum_jump_rise()


def test_platform_validation_rejects_an_unreachable_height():
    impossible = (PlatformSpec(x=100, width=100, rise=round(maximum_jump_rise()) + 20),)
    try:
        validate_platform_specs(impossible)
    except ValueError as error:
        assert "exige subida" in str(error)
    else:
        raise AssertionError("Uma plataforma inalcançável deveria ser rejeitada")
