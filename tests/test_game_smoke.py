import os
from unittest.mock import Mock, call, patch

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.game.assets import compose_platform_strip
from src.game.config import (
    DEATH_ANIMATION_SECONDS,
    PLAYER_HEIGHT,
    PLAYER_ROLL_HEIGHT,
    PLAYER_SPEED,
    PLAYER_SPEED_BOOST_MULTIPLIER,
    SCREEN_HEIGHT,
)
from src.game.entities import Player
from src.game.levels import (
    PHASE_1_PLATFORMS,
    PHASE_2_PLATFORMS,
    PlatformSpec,
    build_phase_1_layout,
    build_phase_2_layout,
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
    assert game.state.name in {"INTRO", "MENU", "PLAYING", "QUESTION", "FEEDBACK", "DYING", "GAME_OVER", "VICTORY"}


def test_knight_animation_rows_are_loaded_without_label_cells():
    game = Game()

    assert len(game.sprites["player_idle"]) == 4
    assert len(game.sprites["player_run"]) == 16
    assert len(game.sprites["player_roll"]) == 8
    assert len(game.sprites["player_hit"]) == 4
    assert len(game.sprites["player_death"]) == 4


def test_all_gameplay_sounds_are_loaded():
    game = Game()

    assert set(game.sounds) == {"coin", "jump", "hurt", "power_up"}
    assert all(sound is not None for sound in game.sounds.values())


def test_returning_to_menu_stops_every_active_sound():
    game = Game()
    sounds = {name: Mock() for name in game.sounds}
    game.sounds = sounds

    game.show_main_menu()

    assert all(sound.stop.call_count == 1 for sound in sounds.values())


def test_receiving_shield_does_not_start_a_buzzer_sound():
    game = Game()
    game.start_phase(PhaseId.PROTOTYPE)
    game.current_question = game.question_bank.next_question()
    game.question_started = 100.0
    game.streak = 2

    with patch("src.main.time.monotonic", return_value=103.0), patch.object(
        game, "play_sound"
    ) as play_sound:
        game.resolve_answer(game.current_question.correct_index)

    assert play_sound.call_args_list == [call("coin")]
    assert game.has_shield
    assert game.speed_boost_until > 103.0


def test_jump_sound_plays_only_when_a_jump_really_starts():
    game = Game()
    game.start_phase(PhaseId.PROTOTYPE)

    with patch.object(game, "play_sound") as play_sound:
        game.update(1 / 60, {Action.JUMP})
        game.update(1 / 60, {Action.JUMP})

    assert play_sound.call_args_list == [call("jump")]


def test_hurt_sound_plays_for_spike_and_hole_damage():
    for cause in ("spike", "hole"):
        game = Game()
        game.start_phase(PhaseId.PHASE_1)

        with patch.object(game, "play_sound") as play_sound:
            game.on_hazard(cause)

        play_sound.assert_called_once_with("hurt")


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


def test_intro_accepts_any_start_action_before_opening_menu():
    game = Game()
    assert game.state == GameState.INTRO

    game.update(1 / 60, {Action.START})

    assert game.state == GameState.MENU


def test_menu_does_not_reveal_question_counts():
    game = Game()
    game.show_main_menu()
    rendered_texts: list[str] = []

    original_draw_text = game.draw_text

    def record_text(text, *args, **kwargs):
        rendered_texts.append(text)
        return original_draw_text(text, *args, **kwargs)

    with patch.object(game, "draw_text", side_effect=record_text):
        game.draw_main_menu()

    assert not any("pergunta" in text.lower() for text in rendered_texts)


def test_red_button_restarts_after_game_over():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    game.state = GameState.GAME_OVER

    game.update(1 / 60, {Action.ANSWER_1})

    assert game.state == GameState.MENU


def test_questions_show_button_colors_instead_of_numbers():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    game.current_question = game.question_bank.next_question()
    rendered_texts: list[str] = []
    original_draw_text = game.draw_text

    def record_text(text, *args, **kwargs):
        rendered_texts.append(text)
        return original_draw_text(text, *args, **kwargs)

    with patch.object(game, "draw_text", side_effect=record_text):
        game.draw_question()

    assert any(text.startswith("VERMELHO:") for text in rendered_texts)
    assert any(text.startswith("AMARELO:") for text in rendered_texts)
    assert any(text.startswith("AZUL:") for text in rendered_texts)
    assert any(text.startswith("VERDE:") for text in rendered_texts)


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


def test_phase_2_layout_is_distinct_and_reachable():
    validate_platform_specs(PHASE_2_PLATFORMS)
    phase_1 = build_phase_1_layout()
    phase_2 = build_phase_2_layout()

    assert phase_2.name == "Fase 2"
    assert phase_2.world_width > phase_1.world_width
    assert len(phase_2.portals) == 6
    assert len(phase_2.holes) == 4
    assert len(phase_2.moving_obstacles) == 3
    assert phase_2.castle.rect.right == phase_2.world_width - 10


def test_phase_2_question_platforms_require_precise_but_possible_jumps():
    layout = build_phase_2_layout()
    # Pares de plataforma de aproximação e plataforma com pergunta.
    platform_jumps = ((0, 1), (4, 5), (6, 7))

    for source_index, target_index in platform_jumps:
        source = layout.platforms[source_index]
        target = layout.platforms[target_index]
        player = Player(source.rect.right - Player.WIDTH, GROUND_Y)
        player.y = float(source.rect.top - Player.HEIGHT)

        for frame in range(120):
            player.update(1 / 60, 1, frame == 0, False, 1, layout.world_width, [source.rect, target.rect])
            if player.on_ground and frame > 3:
                break

        assert player.on_ground
        assert player.rect.bottom == target.rect.top
        assert target.rect.width <= 150

    # Nenhuma plataforma elevada com pergunta pode ser alcançada do chão.
    for target_index in (1, 5, 7):
        assert PHASE_2_PLATFORMS[target_index].rise > maximum_jump_rise()


def test_elevated_question_portals_cannot_be_triggered_from_below():
    # Portais 1, 3 e 4 ficam sobre plataformas elevadas.
    for portal_index in (1, 3, 4):
        game = Game()
        game.start_phase(PhaseId.PHASE_2)
        portal = game.portals[portal_index]
        game.player.x = float(portal.rect.x)

        for frame in range(90):
            actions = {Action.JUMP} if frame == 0 else set()
            game.update(1 / 60, actions)
            assert game.state == GameState.PLAYING

        assert portal.rect.bottom < min(
            platform.rect.top
            for platform in game.platforms
            if platform.rect.left <= portal.rect.centerx <= platform.rect.right
        )



def test_phase_2_holes_can_be_crossed_with_the_player_physics():
    layout = build_phase_2_layout()
    solids = [obj.rect for obj in layout.ground_segments] + [obj.rect for obj in layout.platforms]

    for hole in layout.holes:
        player = Player(hole.rect.left - Player.WIDTH, GROUND_Y)
        for frame in range(120):
            player.update(1 / 60, 1, frame == 0, False, 1, layout.world_width, solids)
            if player.on_ground and frame > 0:
                break
            assert player.y <= SCREEN_HEIGHT + 40

        assert player.on_ground
        assert player.rect.left >= hole.rect.right


def test_phase_2_has_a_safe_landing_area_after_every_hole():
    layout = build_phase_2_layout()
    minimum_landing_area = 100
    ground_hazards = [
        obstacle.rect.left
        for obstacle in layout.obstacles
        if obstacle.rect.bottom == GROUND_Y
    ] + [
        obstacle.min_x
        for obstacle in layout.moving_obstacles
        if obstacle.y + obstacle.height == GROUND_Y
    ]

    for hole in layout.holes:
        hazards_after_hole = [x for x in ground_hazards if x >= hole.rect.right]
        next_hazard_x = min(hazards_after_hole, default=layout.castle.rect.left)
        assert next_hazard_x - hole.rect.right >= minimum_landing_area


def test_menu_opens_phase_2_without_changing_existing_phases():
    game = Game()
    prototype_width = game.active_layout.world_width

    game.update(1 / 60, {Action.START})
    game.update(1 / 60, {Action.ANSWER_3})
    game.update(1 / 60, set())
    game.draw()

    assert game.active_layout.name == "Fase 2"
    assert game.player.rect.bottom == GROUND_Y
    assert build_phase_1_layout().name == "Fase 1"
    assert prototype_width == 2600


def test_phase_2_obstacles_move_and_remain_inside_their_patrols():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    initial_positions = [obstacle.rect.x for obstacle in game.moving_obstacles]

    for _ in range(180):
        game.update(1 / 60, set())

    assert [obstacle.rect.x for obstacle in game.moving_obstacles] != initial_positions
    assert all(
        obstacle.min_x <= obstacle.rect.x <= obstacle.max_x
        for obstacle in game.moving_obstacles
    )


def test_fast_correct_answer_applies_and_expires_speed_boost():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    game.current_question = game.question_bank.next_question()
    game.question_started = 100.0

    with patch("src.main.time.monotonic", return_value=103.0):
        game.resolve_answer(game.current_question.correct_index)

    assert game.speed_boost_until > 103.0
    assert "velocidade" in game.feedback_text

    game.state = GameState.PLAYING
    with patch("src.main.time.monotonic", return_value=106.0):
        game.update(1 / 60, set())
    assert game.player.speed == PLAYER_SPEED * PLAYER_SPEED_BOOST_MULTIPLIER

    with patch("src.main.time.monotonic", return_value=game.speed_boost_until + 0.1):
        game.update(1 / 60, set())
    assert game.player.speed == PLAYER_SPEED


def test_question_symbol_disappears_only_after_the_answer():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    portal = game.portals[0]
    game.player.x = float(portal.rect.x)

    game.update(1 / 60, set())

    assert game.state == GameState.QUESTION
    assert game.active_portal_index == 0
    assert 0 not in game.triggered_portals

    assert game.current_question is not None
    game.resolve_answer(game.current_question.correct_index)

    assert game.active_portal_index is None
    assert 0 in game.triggered_portals

    background = (1, 2, 3)
    game.screen.fill(background)
    game.draw_portal(portal.rect, triggered=True)
    assert game.screen.get_at(portal.rect.center)[:3] == background


def test_question_marker_uses_a_coin_sized_hitbox():
    layout = build_phase_2_layout()
    assert all(marker.rect.size == (24, 24) for marker in layout.portals)


def test_losing_shield_does_not_open_feedback_modal():
    game = Game()
    game.start_phase(PhaseId.PHASE_2)
    game.has_shield = True
    lives_before_hazard = game.lives

    game.on_hazard("spike")

    assert game.has_shield is False
    assert game.lives == lives_before_hazard
    assert game.state == GameState.PLAYING
    assert game.feedback_text == ""

    with patch.object(game, "draw_player") as draw_player:
        game.draw()
    assert draw_player.call_args.args[1] is False
