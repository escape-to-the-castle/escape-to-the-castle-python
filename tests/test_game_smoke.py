import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.game.assets import compose_platform_strip
from src.game.config import DEATH_ANIMATION_SECONDS, PLAYER_HEIGHT, PLAYER_ROLL_HEIGHT
from src.game.entities import Player
from src.game.levels import (
    PHASE_1_PLATFORMS,
    PlatformSpec,
    build_phase_1_layout,
    maximum_jump_rise,
    validate_platform_specs,
)
from src.hardware.interface import Action
from src.hardware.keyboard import KeyboardHardware
from src.main import GROUND_Y, Game, GameState, PhaseId


def test_platform_strip_joins_detailed_tiles_without_stretching():
    colors = ((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))
    tiles = tuple(pygame.Surface((16, 16), pygame.SRCALPHA) for _ in colors)
    for tile, color in zip(tiles, colors):
        tile.fill(color)

    strip = compose_platform_strip(tiles, 70)

    assert strip.get_size() == (70, 16)
    assert strip.get_at((0, 0)) == colors[0]
    assert strip.get_at((15, 0)) == colors[0]
    assert strip.get_at((16, 0)) == colors[1]
    assert strip.get_at((32, 0)) == colors[2]
    assert strip.get_at((48, 0)) == colors[0]
    assert strip.get_at((69, 0)) == colors[1]


def test_platform_asset_keeps_each_original_tile_intact():
    game = Game()
    platform_rows = game.sprites["platform_rows"]
    assert isinstance(platform_rows, list)

    tiles = platform_rows[0]
    assert [tile.get_size() for tile in tiles] == [(16, 16)] * 3

    strip = compose_platform_strip(tiles, 144)
    for index in range(9):
        actual = strip.subsurface(pygame.Rect(index * 16, 0, 16, 16))
        expected = tiles[index % len(tiles)]
        assert pygame.image.tobytes(actual, "RGBA") == pygame.image.tobytes(expected, "RGBA")


def test_air_platform_uses_the_platform_tiles():
    game = Game()
    rect = pygame.Rect(20, 120, 70, 16)
    game.screen.fill((0, 0, 0))

    game.draw_platform(rect)

    strip = game.get_platform_strip(rect.width)
    assert strip is not None
    expected = pygame.Surface(rect.size)
    expected.fill((0, 0, 0))
    expected.blit(strip, (0, 0))
    actual = game.screen.subsurface(rect)
    assert pygame.image.tobytes(actual, "RGB") == pygame.image.tobytes(expected, "RGB")


def test_game_initializes_and_renders():
    game = Game()
    game.update(1 / 60, set())
    game.draw()

    assert game.running is True
    assert game.state.name in {"MENU", "PLAYING", "QUESTION", "FEEDBACK", "DYING", "GAME_OVER", "VICTORY"}


def test_knight_animation_rows_are_loaded_without_label_cells():
    game = Game()

    assert len(game.sprites["player_idle"]) == 4
    assert len(game.sprites["player_run"]) == 16
    assert len(game.sprites["player_roll"]) == 8
    assert len(game.sprites["player_hit"]) == 4
    assert len(game.sprites["player_death"]) == 4


def test_keyboard_maps_down_key_to_roll():
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))

    assert Action.ROLL in KeyboardHardware().poll_actions()


def test_roll_reduces_hitbox_and_waits_for_room_to_stand():
    player = Player(100, GROUND_Y)
    floor = pygame.Rect(0, GROUND_Y, 1000, 80)
    low_ceiling = pygame.Rect(0, GROUND_Y - PLAYER_ROLL_HEIGHT - 16, 1000, 16)
    original_bottom = player.rect.bottom

    player.update(0.0, 0, False, True, 1, 1000, [floor, low_ceiling])

    assert player.is_rolling
    assert player.rect.height == PLAYER_ROLL_HEIGHT
    assert player.rect.bottom == original_bottom

    player.update(player.ROLL_DURATION + 0.1, 0, False, False, 1, 1000, [floor, low_ceiling])
    assert player.is_rolling

    player.update(0.0, 0, False, False, 1, 1000, [floor])
    assert not player.is_rolling
    assert player.rect.height == PLAYER_HEIGHT
    assert player.rect.bottom == original_bottom


def test_only_rolling_player_fits_below_a_low_platform():
    floor = pygame.Rect(0, GROUND_Y, 1000, 80)
    low_platform = pygame.Rect(100, GROUND_Y - PLAYER_ROLL_HEIGHT - 16, 180, 16)
    player = Player(60, GROUND_Y)

    player.update(0.2, 1, False, False, 1, 1000, [floor, low_platform])
    assert player.x == 60

    player.update(0.2, 1, False, True, 1, 1000, [floor, low_platform])
    assert player.is_rolling
    assert player.x > 100


def test_damage_does_not_pause_or_reset_the_player_and_has_grace_period():
    game = Game()
    game.start_phase(PhaseId.PROTOTYPE)
    original_position = (game.player.x, game.player.y)

    game.on_hazard("spike")

    assert game.lives == 2
    assert game.state == GameState.PLAYING
    assert (game.player.x, game.player.y) == original_position
    assert game.invulnerable_until == game.animation_time + 0.5

    game.on_hazard("spike")
    assert game.lives == 2

    game.update(0.25, {Action.MOVE_RIGHT})
    assert game.state == GameState.PLAYING
    assert game.player.x > original_position[0]


def test_non_hole_death_finishes_animation_before_game_over():
    game = Game()
    game.start_phase(PhaseId.PROTOTYPE)
    game.lives = 1

    game.on_hazard("spike")

    assert game.state == GameState.DYING
    game.update(DEATH_ANIMATION_SECONDS - 0.01, set())
    assert game.state == GameState.DYING
    game.update(0.02, set())
    assert game.state == GameState.GAME_OVER


def test_hole_death_skips_the_death_animation():
    game = Game()
    game.start_phase(PhaseId.PHASE_1)
    game.lives = 1

    game.on_hazard("hole")

    assert game.state == GameState.GAME_OVER
    assert game.death_animation_started is None


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
