from __future__ import annotations

import sys
import time
from enum import Enum, auto
from pathlib import Path

import pygame

from .education.question_bank import Question, QuestionBank
from .game.assets import compose_platform_strip, load_brackeys_sprites
from .game.config import (
    DAMAGE_INVULNERABILITY_SECONDS,
    DEATH_ANIMATION_SECONDS,
    FPS,
    GROUND_Y,
    HIT_ANIMATION_SECONDS,
    PLAYER_ROLL_DURATION_SECONDS,
    PLAYER_SPRITE_SIZE,
    PLAYER_SPEED,
    PLAYER_SPEED_BOOST_MULTIPLIER,
    PLAYER_SPEED_BOOST_SECONDS,
    SCREEN_HEIGHT as HEIGHT,
    SCREEN_WIDTH as WIDTH,
    SHIELD_INVULNERABILITY_SECONDS,
    SPIKE_VISUAL_SIZE,
)
from .game.entities import MovingObstacle, Player, WorldObject
from .game.levels import PhaseId, build_layout
from .hardware.interface import Action, OutputState
from .hardware.factory import create_hardware
from .monitoring.performance import PerformanceMonitor


ROOT = Path(__file__).resolve().parents[1]


class GameState(Enum):
    INTRO = auto()
    MENU = auto()
    PLAYING = auto()
    QUESTION = auto()
    FEEDBACK = auto()
    DYING = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Fuja para o Castelo")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 26)
        self.large_font = pygame.font.Font(None, 56)
        self.sprites = load_brackeys_sprites(ROOT)
        self.platform_strip_cache: dict[tuple[int, int], pygame.Surface] = {}
        self.hardware = KeyboardHardware()
        self.hardware = create_hardware()
        self.question_bank = QuestionBank(ROOT / "data" / "questions.json")
        self.monitor = PerformanceMonitor()
        self.running = True
        self.current_phase = PhaseId.PROTOTYPE
        self.active_layout = build_layout(self.current_phase)
        self.start_phase(self.current_phase)
        self.show_intro()

    def reset_phase(self) -> None:
        self.player = Player(self.active_layout.player_start_x, GROUND_Y)
        self.obstacles = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.obstacles]
        self.moving_obstacles = [
            MovingObstacle(spec.x, spec.y, spec.width, spec.height, spec.min_x, spec.max_x, spec.speed)
            for spec in self.active_layout.moving_obstacles
        ]
        self.portals = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.portals]
        self.platforms = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.platforms]
        self.holes = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.holes]
        self.ground_segments = [
            WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.ground_segments
        ]
        self.triggered_portals: set[int] = set()
        self.active_portal_index: int | None = None
        self.castle = WorldObject(
            self.active_layout.castle.rect.x,
            self.active_layout.castle.rect.y,
            self.active_layout.castle.rect.width,
            self.active_layout.castle.rect.height,
        )
        self.world_width = self.active_layout.world_width
        self.lives = 3
        self.coins = 0
        self.streak = 0
        self.has_shield = False
        self.animation_time = 0.0
        self.invulnerable_until = 0.0
        self.damage_flash_until = 0.0
        self.hit_animation_started: float | None = None
        self.death_animation_started: float | None = None
        self.speed_boost_until = 0.0
        self.state = GameState.PLAYING
        self.current_question: Question | None = None
        self.question_started = 0.0
        self.feedback_text = ""
        self.feedback_until = 0.0
        self.feedback_returns_to_playing = True
        self.last_safe_x = self.player.x
        self.player_facing = 1
        self.player_moving = False

    def show_intro(self) -> None:
        self.state = GameState.INTRO

    def show_main_menu(self) -> None:
        self.state = GameState.MENU
        self.feedback_text = ""
        self.feedback_until = 0.0
        self.feedback_returns_to_playing = True
        self.current_question = None

    def start_phase(self, phase: PhaseId) -> None:
        self.current_phase = phase
        self.active_layout = build_layout(phase)
        self.question_bank.reset_round()
        self.reset_phase()

    def answer_index(self, actions: set[Action]) -> int | None:
        mapping = [Action.ANSWER_1, Action.ANSWER_2, Action.ANSWER_3, Action.ANSWER_4]
        for index, action in enumerate(mapping):
            if action in actions:
                return index
        return None

    def start_question(self) -> None:
        self.current_question = self.question_bank.next_question()
        self.question_started = time.monotonic()
        self.state = GameState.QUESTION

    def update_hardware_outputs(self, feedback: str | None = None) -> None:
        self.hardware.update_outputs(
            OutputState(
                progress=min(1.0, self.player.x / self.castle.rect.x),
                lives=self.lives,
                coins=self.coins,
                feedback=feedback
                or ("shield" if self.has_shield else "neutral"),
            )
        )

    def resolve_answer(self, selected: int) -> None:
        assert self.current_question is not None
        now = time.monotonic()
        elapsed = now - self.question_started
        if selected == self.current_question.correct_index:
            bonus = 5 if elapsed <= 5.0 else 0
            self.coins += 10 + bonus
            self.streak += 1
            if self.streak == 3:
                self.has_shield = True
            if self.streak == 5:
                self.lives += 1
            if bonus:
                # O tempo da tela de feedback não consome o bônus jogável.
                self.speed_boost_until = now + 2.4 + PLAYER_SPEED_BOOST_SECONDS
            extra = f" + velocidade {PLAYER_SPEED_BOOST_MULTIPLIER:.2g}x!" if bonus else ""
            self.feedback_text = f"Correto! +{10 + bonus} moedas{extra}"
        else:
            self.streak = 0
            self.feedback_text = f"Quase! {self.current_question.explanation}"
        if self.active_portal_index is not None:
            self.triggered_portals.add(self.active_portal_index)
            self.active_portal_index = None
        self.feedback_until = time.monotonic() + 2.4
        self.state = GameState.FEEDBACK
        self.update_hardware_outputs("correct" if selected == self.current_question.correct_index else "error")

    def on_hazard(self, cause: str) -> None:
        now = self.animation_time
        if self.state in (GameState.DYING, GameState.GAME_OVER) or now < self.invulnerable_until:
            return

        if self.has_shield:
            self.has_shield = False
            self.invulnerable_until = now + SHIELD_INVULNERABILITY_SECONDS
            if cause == "hole":
                self.player.respawn(self.last_safe_x, GROUND_Y)
            return

        self.lives -= 1
        if self.lives <= 0:
            if cause == "hole":
                self.state = GameState.GAME_OVER
            else:
                self.death_animation_started = now
                self.player_moving = False
                self.state = GameState.DYING
            return

        self.invulnerable_until = now + DAMAGE_INVULNERABILITY_SECONDS
        self.damage_flash_until = now + DAMAGE_INVULNERABILITY_SECONDS
        self.hit_animation_started = now

        # Buracos ainda exigem reposicionamento. Outros danos mantêm o
        # jogador no lugar e dão tempo para que ele se afaste do obstáculo.
        if cause == "hole":
            self.player.respawn(self.last_safe_x, GROUND_Y)
            shield_absorbed_hazard = True
        else:
            self.lives -= 1
            self.feedback_text = "Cuidado! Você perdeu uma vida."
            shield_absorbed_hazard = False
        # ``last_safe_x`` is recorded only while the player is standing on
        # solid ground, so falling into a pit can never create a checkpoint
        # in mid-air above that same pit.
        self.player.x = self.last_safe_x
        self.player.y = float(GROUND_Y - self.player.HEIGHT)
        self.player.vy = 0.0
        self.player.on_ground = True
        if shield_absorbed_hazard:
            self.feedback_text = ""
            self.feedback_until = 0.0
            self.feedback_returns_to_playing = True
            self.state = GameState.PLAYING
        elif self.lives <= 0:
            self.state = GameState.GAME_OVER
        else:
            self.feedback_until = time.monotonic() + 1.5
            self.feedback_returns_to_playing = True
            self.state = GameState.FEEDBACK
        self.update_hardware_outputs("neutral" if shield_absorbed_hazard else "error")

    def update(self, dt: float, actions: set[Action]) -> None:
        if Action.QUIT in actions:
            self.running = False
            return

        self.animation_time += dt

        if self.state == GameState.INTRO:
            if actions - {Action.QUIT}:
                self.show_main_menu()
            return

        if self.state == GameState.MENU:
            if Action.ANSWER_1 in actions:
                self.start_phase(PhaseId.PROTOTYPE)
            elif Action.ANSWER_2 in actions:
                self.start_phase(PhaseId.PHASE_1)
            elif Action.ANSWER_3 in actions:
                self.start_phase(PhaseId.PHASE_2)
            return

        if self.state in (GameState.GAME_OVER, GameState.VICTORY):
            if Action.RESTART in actions:
                self.show_main_menu()
            return

        if self.state == GameState.DYING:
            if (
                self.death_animation_started is not None
                and self.animation_time - self.death_animation_started >= DEATH_ANIMATION_SECONDS
            ):
                self.state = GameState.GAME_OVER
            return

        if self.state == GameState.QUESTION:
            selected = self.answer_index(actions)
            if selected is not None and self.current_question and selected < len(self.current_question.options):
                self.resolve_answer(selected)
            return

        if self.state == GameState.FEEDBACK:
            if time.monotonic() >= self.feedback_until:
                if self.feedback_returns_to_playing:
                    self.state = GameState.PLAYING
            return

        speed_boost_active = time.monotonic() < self.speed_boost_until
        self.player.speed = PLAYER_SPEED * (PLAYER_SPEED_BOOST_MULTIPLIER if speed_boost_active else 1.0)

        direction = int(Action.MOVE_RIGHT in actions) - int(Action.MOVE_LEFT in actions)
        if direction:
            self.player_facing = 1 if direction > 0 else -1
        solids = [obj.rect for obj in self.ground_segments] + [obj.rect for obj in self.platforms]
        self.player.update(
            dt,
            direction,
            Action.JUMP in actions,
            Action.ROLL in actions,
            direction or self.player_facing,
            self.world_width,
            solids,
        )
        self.player_moving = direction != 0 and not self.player.is_rolling
        self.player.update(dt, direction, Action.JUMP in actions, self.world_width, solids)
        for obstacle in self.moving_obstacles:
            obstacle.update(dt)

        fell_in_hole = self.player.y > HEIGHT + 40
        if fell_in_hole:
            self.on_hazard("hole")
            return

        if any(self.player.rect.colliderect(obj.rect) for obj in [*self.obstacles, *self.moving_obstacles]):
            self.on_hazard("spike")
            return

        # Platforms are useful for traversal, but ground-level checkpoints
        # make respawns predictable and guarantee support under the player.
        if self.player.on_ground and any(
            self.player.rect.bottom == segment.rect.top
            and self.player.rect.left >= segment.rect.left
            and self.player.rect.right <= segment.rect.right
            for segment in self.ground_segments
        ):
            self.last_safe_x = self.player.x

        for index, portal in enumerate(self.portals):
            if (
                index not in self.triggered_portals
                and self.player.on_ground
                and self.player.rect.colliderect(portal.rect)
            ):
                self.active_portal_index = index
                self.start_question()
                return

        if self.player.rect.colliderect(self.castle.rect):
            self.state = GameState.VICTORY

        progress = min(1.0, self.player.x / self.castle.rect.x)
        self.hardware.update_outputs(
            OutputState(
                progress=progress,
                lives=self.lives,
                coins=self.coins,
                feedback=(
                    "shield"
                    if self.has_shield
                    or (
                        self.animation_time < self.invulnerable_until
                        and self.animation_time >= self.damage_flash_until
                    )
                    else "neutral"
                ),
            )
        )
        self.update_hardware_outputs()

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        center: bool = False,
        color: tuple[int, int, int] = (240, 240, 240),
    ) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
            self.screen.blit(surface, rect)
        else:
            self.screen.blit(surface, (x, y))

    def draw_wrapped(
        self,
        text: str,
        rect: pygame.Rect,
        font: pygame.font.Font,
        color: tuple[int, int, int] = (240, 240, 240),
    ) -> None:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        y = rect.y
        for line in lines:
            self.screen.blit(font.render(line, True, color), (rect.x, y))
            y += font.get_linesize()

    def draw_background(self, camera_x: float) -> None:
        sky_top = (101, 188, 255)
        sky_bottom = (182, 232, 255)
        for y in range(HEIGHT):
            blend = y / HEIGHT
            r = int(sky_top[0] + (sky_bottom[0] - sky_top[0]) * blend)
            g = int(sky_top[1] + (sky_bottom[1] - sky_top[1]) * blend)
            b = int(sky_top[2] + (sky_bottom[2] - sky_top[2]) * blend)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WIDTH, y))

        pygame.draw.circle(self.screen, (255, 244, 190), (820, 84), 34)
        pygame.draw.circle(self.screen, (255, 252, 230), (810, 76), 30)

        for cloud_x, cloud_y, cloud_w, cloud_h in [(-20, 70, 120, 38), (180, 50, 150, 42), (540, 92, 135, 36), (760, 58, 160, 44)]:
            px = (cloud_x - camera_x * 0.08) % (WIDTH + 220) - 110
            pygame.draw.ellipse(self.screen, (255, 255, 255), (px, cloud_y, cloud_w, cloud_h))
            pygame.draw.ellipse(self.screen, (236, 246, 255), (px + 20, cloud_y + 8, cloud_w - 40, cloud_h - 12))

        # Montanhas em duas camadas criam profundidade com paralaxe.
        for offset in range(-240, WIDTH + 480, 260):
            base_x = (offset - int(camera_x * 0.10)) % (WIDTH + 520) - 260
            pygame.draw.polygon(
                self.screen,
                (125, 169, 181),
                [(base_x, GROUND_Y), (base_x + 150, 245), (base_x + 310, GROUND_Y)],
            )
            pygame.draw.polygon(
                self.screen,
                (233, 242, 240),
                [(base_x + 112, 300), (base_x + 150, 245), (base_x + 190, 300)],
            )

        for offset in range(-180, WIDTH + 400, 230):
            base_x = (offset - int(camera_x * 0.22)) % (WIDTH + 460) - 230
            pygame.draw.polygon(
                self.screen,
                (91, 164, 100),
                [(base_x, GROUND_Y), (base_x + 125, 330), (base_x + 260, GROUND_Y)],
            )

        # Árvores e arbustos acompanham uma camada mais próxima do jogador.
        for world_x in range(180, self.world_width, 360):
            x = world_x - int(camera_x * 0.72)
            if -80 <= x <= WIDTH + 80:
                pygame.draw.rect(self.screen, (104, 72, 52), (x + 28, GROUND_Y - 82, 14, 82))
                pygame.draw.circle(self.screen, (49, 129, 76), (x + 35, GROUND_Y - 105), 38)
                pygame.draw.circle(self.screen, (69, 153, 85), (x + 12, GROUND_Y - 86), 27)
                pygame.draw.circle(self.screen, (79, 166, 91), (x + 58, GROUND_Y - 87), 28)

        for segment in self.ground_segments:
            seg = segment.rect.move(-camera_x, 0)
            if seg.right < 0 or seg.left > WIDTH:
                continue
            strip = self.get_platform_strip(segment.rect.width)
            if strip is not None:
                self.screen.blit(strip, (seg.x, GROUND_Y))
                ground_fill_y = GROUND_Y + strip.get_bounding_rect().bottom
            else:
                pygame.draw.rect(self.screen, (92, 159, 87), seg)
                ground_fill_y = GROUND_Y + 16
            pygame.draw.rect(
                self.screen,
                (84, 124, 73),
                (seg.x, ground_fill_y, seg.width, HEIGHT - ground_fill_y),
            )

        for hole in self.holes:
            pit = hole.rect.move(-camera_x, 0)
            if pit.right < 0 or pit.left > WIDTH:
                continue
            pygame.draw.rect(self.screen, (27, 34, 46), pit)

        for world_x in range(90, self.world_width, 150):
            x = world_x - int(camera_x)
            if -10 <= x <= WIDTH + 10:
                pygame.draw.line(self.screen, (47, 116, 57), (x, GROUND_Y), (x, GROUND_Y - 13), 2)
                pygame.draw.circle(self.screen, (255, 216, 77), (x - 3, GROUND_Y - 14), 3)
                pygame.draw.circle(self.screen, (255, 245, 180), (x + 3, GROUND_Y - 14), 3)

    def get_platform_strip(self, width: int, row: int = 0) -> pygame.Surface | None:
        platform_rows = self.sprites.get("platform_rows")
        if not isinstance(platform_rows, list) or not 0 <= row < len(platform_rows):
            return None

        tiles = platform_rows[row]
        if not isinstance(tiles, tuple) or not tiles:
            return None

        cache_key = (row, width)
        strip = self.platform_strip_cache.get(cache_key)
        if strip is None:
            strip = compose_platform_strip(tiles, width)
            self.platform_strip_cache[cache_key] = strip
        return strip

    def draw_platform(self, rect: pygame.Rect) -> None:
        strip = self.get_platform_strip(rect.width)
        if strip is not None:
            self.screen.blit(strip, rect.topleft)
            return

        pygame.draw.rect(self.screen, (100, 143, 94), rect, border_radius=4)
        pygame.draw.rect(self.screen, (74, 111, 69), (rect.x, rect.y + rect.height - 4, rect.width, 4), border_radius=2)
        pygame.draw.rect(self.screen, (188, 224, 180), (rect.x + 6, rect.y + 2, max(4, rect.width - 12), 3), border_radius=2)

    def draw_obstacle(self, rect: pygame.Rect) -> None:
        visual_rect = pygame.Rect(0, 0, *SPIKE_VISUAL_SIZE)
        visual_rect.midbottom = rect.midbottom
        pygame.draw.rect(self.screen, (74, 78, 88), (visual_rect.x, visual_rect.bottom - 7, visual_rect.width, 7))
        pygame.draw.line(
            self.screen,
            (173, 181, 194),
            (visual_rect.left, visual_rect.bottom - 7),
            (visual_rect.right, visual_rect.bottom - 7),
            2,
        )
        spike_width = visual_rect.width // 3
        for index in range(3):
            left = visual_rect.x + index * spike_width
            points = [(left, visual_rect.bottom - 7), (left + spike_width // 2, visual_rect.top), (left + spike_width, visual_rect.bottom - 7)]
            pygame.draw.polygon(self.screen, (205, 211, 220), points)
            pygame.draw.line(self.screen, (255, 255, 255), points[0], points[1], 2)
            pygame.draw.line(self.screen, (74, 78, 88), points[1], points[2], 2)

    def draw_portal(self, rect: pygame.Rect, triggered: bool) -> None:
        if triggered:
            return
        coin_frames = self.sprites.get("coins")
        if isinstance(coin_frames, list) and coin_frames:
            frame = coin_frames[int(self.animation_time * 12) % len(coin_frames)]
            coin = pygame.transform.scale(frame, (30, 30))
            self.screen.blit(coin, coin.get_rect(center=rect.center))
        elif self.sprites.get("fruit"):
            fruit = self.sprites["fruit"]
            assert isinstance(fruit, pygame.Surface)
            fruit_rect = fruit.get_rect(center=rect.center)
            self.screen.blit(fruit, fruit_rect)
        else:
            pygame.draw.circle(self.screen, (255, 216, 77), rect.center, rect.width // 2)

    def draw_castle(self, rect: pygame.Rect) -> None:
        stone = (116, 120, 132)
        light_stone = (151, 155, 166)
        dark_stone = (70, 73, 84)
        roof = (145, 49, 58)

        center = pygame.Rect(rect.x + 45, rect.y + 54, rect.width - 90, rect.height - 54)
        left_tower = pygame.Rect(rect.x, rect.y + 34, 62, rect.height - 34)
        right_tower = pygame.Rect(rect.right - 62, rect.y + 34, 62, rect.height - 34)
        pygame.draw.rect(self.screen, stone, center)
        pygame.draw.rect(self.screen, light_stone, left_tower)
        pygame.draw.rect(self.screen, light_stone, right_tower)

        for tower in (left_tower, right_tower):
            pygame.draw.polygon(
                self.screen,
                roof,
                [(tower.x - 7, tower.y), (tower.centerx, tower.y - 48), (tower.right + 7, tower.y)],
            )
            pygame.draw.rect(self.screen, dark_stone, tower, width=3)
            window = pygame.Rect(0, 0, 15, 28)
            window.midtop = (tower.centerx, tower.y + 42)
            pygame.draw.rect(self.screen, (38, 48, 67), window, border_radius=7)
            pygame.draw.rect(self.screen, (232, 194, 79), window.inflate(-7, -8), border_radius=3)

        battlement_y = center.y - 12
        pygame.draw.rect(self.screen, stone, (center.x, battlement_y + 12, center.width, 22))
        for x in range(center.x, center.right, 28):
            pygame.draw.rect(self.screen, light_stone, (x, battlement_y, 18, 22))

        for y in range(center.y + 36, center.bottom - 25, 24):
            offset = 0 if (y // 24) % 2 == 0 else 14
            for x in range(center.x + offset, center.right, 28):
                pygame.draw.line(self.screen, dark_stone, (x, y), (min(x + 18, center.right), y), 1)

        door = pygame.Rect(0, 0, 52, 76)
        door.midbottom = (rect.centerx, rect.bottom)
        pygame.draw.rect(self.screen, (72, 44, 35), door, border_radius=22)
        pygame.draw.rect(self.screen, (42, 29, 28), door, width=4, border_radius=22)
        pygame.draw.circle(self.screen, (240, 194, 70), (door.right - 12, door.centery + 12), 3)

        flag_x = rect.centerx
        pygame.draw.line(self.screen, dark_stone, (flag_x, rect.y + 12), (flag_x, rect.y - 42), 4)
        pygame.draw.polygon(
            self.screen,
            (255, 68, 68),
            [(flag_x + 2, rect.y - 40), (flag_x + 52, rect.y - 27), (flag_x + 2, rect.y - 13)],
        )

    def draw_player(self, rect: pygame.Rect, shield: bool) -> None:
        visual_rect = pygame.Rect(0, 0, *PLAYER_SPRITE_SIZE)
        visual_rect.midbottom = (rect.centerx, rect.bottom + 2)
        idle_frames = self.sprites.get("player_idle")
        run_frames = self.sprites.get("player_run")
        jump_frame = self.sprites.get("player_jump")
        roll_frames = self.sprites.get("player_roll")
        hit_frames = self.sprites.get("player_hit")
        death_frames = self.sprites.get("player_death")
        frame: pygame.Surface | None = None
        if (
            self.death_animation_started is not None
            and isinstance(death_frames, list)
            and death_frames
        ):
            elapsed = max(0.0, self.animation_time - self.death_animation_started)
            progress = min(1.0, elapsed / DEATH_ANIMATION_SECONDS)
            frame = death_frames[min(int(progress * len(death_frames)), len(death_frames) - 1)]
        elif (
            self.hit_animation_started is not None
            and self.animation_time - self.hit_animation_started < HIT_ANIMATION_SECONDS
            and isinstance(hit_frames, list)
            and hit_frames
        ):
            progress = (self.animation_time - self.hit_animation_started) / HIT_ANIMATION_SECONDS
            frame = hit_frames[min(int(progress * len(hit_frames)), len(hit_frames) - 1)]
        elif self.player.is_rolling and isinstance(roll_frames, list) and roll_frames:
            elapsed = PLAYER_ROLL_DURATION_SECONDS - self.player.roll_time_left
            frame = roll_frames[min(int(elapsed * 14), len(roll_frames) - 1)]
        elif not self.player.on_ground and isinstance(jump_frame, pygame.Surface):
            frame = jump_frame
        elif self.player_moving and isinstance(run_frames, list) and run_frames:
            frame = run_frames[int(self.animation_time * 10) % len(run_frames)]
        elif isinstance(idle_frames, list) and idle_frames:
            frame = idle_frames[int(self.animation_time * 5) % len(idle_frames)]

        if isinstance(frame, pygame.Surface):
            sprite = pygame.transform.flip(frame, self.player_facing < 0, False)
            if (
                self.hit_animation_started is not None
                and self.animation_time < self.damage_flash_until
                and int((self.animation_time - self.hit_animation_started) / 0.075) % 2 == 0
            ):
                sprite = sprite.copy()
                sprite.fill((255, 70, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(sprite, visual_rect)
        else:
            pygame.draw.rect(self.screen, (240, 240, 240), visual_rect, border_radius=5)
            pygame.draw.rect(self.screen, (255, 68, 68), (visual_rect.x + 10, visual_rect.y + 12, visual_rect.width - 20, 10), border_radius=2)
            pygame.draw.rect(self.screen, (255, 68, 68), (visual_rect.x + 14, visual_rect.y + 28, 10, 21), border_radius=2)
            pygame.draw.rect(self.screen, (255, 68, 68), (visual_rect.x + 36, visual_rect.y + 28, 10, 21), border_radius=2)
            pygame.draw.rect(self.screen, (22, 22, 26), (visual_rect.x + 19, visual_rect.y + 48, 22, 21), border_radius=2)
        if shield:
            pygame.draw.ellipse(self.screen, (92, 180, 255), visual_rect.inflate(22, 14), width=2)

    def draw_hud(self) -> None:
        panel = pygame.Rect(16, 16, 390, 84)
        pygame.draw.rect(self.screen, (18, 18, 22), panel, border_radius=12)
        pygame.draw.rect(self.screen, (255, 68, 68), panel, width=2, border_radius=12)
        self.draw_text("Vidas", 58, 31, self.small_font, color=(255, 170, 170))
        self.draw_text(f"{self.lives}", 58, 50, self.small_font, color=(255, 255, 255))
        coin_frames = self.sprites.get("coins")
        if isinstance(coin_frames, list) and coin_frames:
            frame = coin_frames[int(self.animation_time * 12) % len(coin_frames)]
            coin = pygame.transform.scale(frame, (24, 24))
            self.screen.blit(coin, coin.get_rect(center=(120, 40)))
        self.draw_text(f"{self.coins}", 140, 50, self.small_font, color=(255, 255, 255))
        self.draw_text("Sequência", 215, 31, self.small_font, color=(255, 170, 170))
        self.draw_text(f"{self.streak}", 215, 50, self.small_font, color=(255, 255, 255))
        self.draw_text("Escudo", 318, 31, self.small_font, color=(255, 170, 170))
        shield_status = "sim" if self.has_shield else "não"
        self.draw_text(shield_status, 318, 50, self.small_font, color=(255, 255, 255))

        invulnerable_left = max(0.0, self.invulnerable_until - self.animation_time)
        inv_text = f"Invuln.: {invulnerable_left:.1f}s" if invulnerable_left > 0 else "Invuln.: 0.0s"
        self.draw_text(inv_text, 404, 50, self.small_font, color=(187, 224, 255))
        self.draw_text(self.active_layout.name, 28, 73, self.small_font, color=(255, 190, 190))

    def draw_main_menu(self) -> None:
        self.draw_background(0)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 12, 24, 178))
        self.screen.blit(overlay, (0, 0))

        self.draw_text("SELECIONE SUA JORNADA", WIDTH // 2, 70, self.large_font, center=True, color=(255, 248, 248))
        self.draw_text("Cada caminho leva a um novo desafio", WIDTH // 2, 122, self.small_font, center=True, color=(184, 205, 232))

        cards = (
            (pygame.Rect(65, 170, 250, 225), "1", "PROTÓTIPO", "A aventura original", (94, 170, 255)),
            (pygame.Rect(355, 170, 250, 225), "2", "FASE 1", "Saltos e desníveis", (255, 173, 72)),
            (pygame.Rect(645, 170, 250, 225), "3", "FASE 2", "O desafio completo", (255, 75, 82)),
        )
        for card, key, title, description, accent in cards:
            shadow = card.move(0, 8)
            pygame.draw.rect(self.screen, (5, 8, 16), shadow, border_radius=20)
            pygame.draw.rect(self.screen, (20, 27, 42), card, border_radius=20)
            pygame.draw.rect(self.screen, accent, card, width=2, border_radius=20)
            pygame.draw.rect(self.screen, accent, (card.x, card.y, card.width, 7), border_radius=4)

            badge = pygame.Rect(card.x + 20, card.y + 27, 46, 46)
            pygame.draw.rect(self.screen, accent, badge, border_radius=12)
            self.draw_text(key, badge.centerx, badge.centery, self.font, center=True, color=(12, 16, 25))
            self.draw_text(title, card.x + 20, card.y + 93, self.font, color=(250, 250, 252))
            self.draw_text(description, card.x + 20, card.y + 137, self.small_font, color=(184, 197, 216))

        self.draw_text("PRESSIONE 1, 2 OU 3 PARA COMEÇAR", WIDTH // 2, 464, self.small_font, center=True, color=(218, 226, 239))

    def draw_intro(self) -> None:
        self.draw_background(0)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 12, 24, 184))
        self.screen.blit(overlay, (0, 0))

        emblem = pygame.Rect(0, 0, 112, 112)
        emblem.center = (WIDTH // 2, 155)
        pygame.draw.rect(self.screen, (18, 24, 38), emblem, border_radius=26)
        pygame.draw.rect(self.screen, (255, 75, 82), emblem, width=3, border_radius=26)
        castle_color = (236, 240, 248)
        castle_body = pygame.Rect(emblem.x + 31, emblem.y + 46, 50, 43)
        left_tower = pygame.Rect(emblem.x + 20, emblem.y + 35, 25, 54)
        right_tower = pygame.Rect(emblem.right - 45, emblem.y + 35, 25, 54)
        pygame.draw.rect(self.screen, castle_color, castle_body)
        pygame.draw.rect(self.screen, castle_color, left_tower)
        pygame.draw.rect(self.screen, castle_color, right_tower)
        for tower in (left_tower, right_tower):
            for x in (tower.x, tower.x + 10, tower.right - 5):
                pygame.draw.rect(self.screen, castle_color, (x, tower.y - 8, 6, 12))
        pygame.draw.rect(self.screen, (18, 24, 38), (emblem.centerx - 8, emblem.bottom - 39, 16, 31), border_radius=8)
        pygame.draw.rect(self.screen, (255, 75, 82), (emblem.centerx - 2, emblem.y + 19, 4, 22))
        pygame.draw.polygon(self.screen, (255, 75, 82), [(emblem.centerx + 2, emblem.y + 19), (emblem.centerx + 21, emblem.y + 25), (emblem.centerx + 2, emblem.y + 31)])

        self.draw_text("FUJA PARA O CASTELO", WIDTH // 2, 250, self.large_font, center=True, color=(255, 248, 248))
        self.draw_text("Uma aventura de conhecimento", WIDTH // 2, 304, self.font, center=True, color=(184, 205, 232))

        if int(time.monotonic() * 2) % 2 == 0:
            prompt = pygame.Rect(270, 370, 420, 58)
            pygame.draw.rect(self.screen, (24, 31, 47), prompt, border_radius=14)
            pygame.draw.rect(self.screen, (255, 75, 82), prompt, width=2, border_radius=14)
            self.draw_text("PRESSIONE QUALQUER TECLA PARA JOGAR", WIDTH // 2, 387, self.small_font, center=True, color=(255, 235, 235))

    def draw(self) -> None:
        if self.state == GameState.INTRO:
            self.draw_intro()
            pygame.display.flip()
            return

        if self.state == GameState.MENU:
            self.draw_main_menu()
            pygame.display.flip()
            return

        camera_x = max(0, min(self.player.x - WIDTH * 0.35, self.world_width - WIDTH))
        self.draw_background(camera_x)

        for platform in self.platforms:
            platform_anchor = platform.rect.move(-camera_x, 0)
            self.draw_platform(platform_anchor)

        # Os retângulos abaixo servem apenas para posicionar os sprites. As
        # hitboxes permanecem na lógica de update e nunca são desenhadas.
        for obj in self.obstacles:
            obstacle_anchor = obj.rect.move(-camera_x, 0)
            self.draw_obstacle(obstacle_anchor)

        for obj in self.moving_obstacles:
            obstacle_anchor = obj.rect.move(-camera_x, 0)
            self.draw_obstacle(obstacle_anchor)

        for index, portal in enumerate(self.portals):
            portal_anchor = portal.rect.move(-camera_x, 0)
            self.draw_portal(portal_anchor, index in self.triggered_portals)

        castle_anchor = self.castle.rect.move(-camera_x, 0)
        self.draw_castle(castle_anchor)

        player_anchor = self.player.rect.move(-camera_x, 0)
        shield_visible = self.has_shield or (
            self.animation_time < self.invulnerable_until
            and self.animation_time >= self.damage_flash_until
        )
        self.draw_player(player_anchor, shield_visible)
        self.draw_player(player_anchor, self.has_shield)
        self.draw_hud()

        if self.state == GameState.QUESTION and self.current_question:
            self.draw_question()
        elif self.state == GameState.FEEDBACK:
            panel = pygame.Rect(135, 185, 690, 145)
            pygame.draw.rect(self.screen, (18, 18, 22), panel, border_radius=18)
            pygame.draw.rect(self.screen, (255, 68, 68), panel, width=2, border_radius=18)
            self.draw_wrapped(self.feedback_text, panel.inflate(-40, -40), self.font, color=(255, 246, 246))
        elif self.state == GameState.GAME_OVER:
            self.draw_end_screen("Fim de jogo", "Pressione R para voltar ao menu")
        elif self.state == GameState.VICTORY:
            self.draw_end_screen("Você chegou ao castelo!", f"Moedas conquistadas: {self.coins} - Pressione R")

        pygame.display.flip()

    def draw_question(self) -> None:
        assert self.current_question is not None
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 14, 165))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(80, 62, 800, 420)
        pygame.draw.rect(self.screen, (20, 20, 24), panel, border_radius=22)
        pygame.draw.rect(self.screen, (255, 68, 68), panel, width=3, border_radius=22)
        self.draw_text(self.current_question.category.upper(), WIDTH // 2, 94, self.small_font, center=True, color=(255, 170, 170))
        self.draw_wrapped(self.current_question.text, pygame.Rect(120, 126, 720, 86), self.font, color=(255, 245, 245))
        for i, option in enumerate(self.current_question.options):
            option_rect = pygame.Rect(120, 230 + i * 50, 720, 38)
            pygame.draw.rect(self.screen, (32, 32, 38), option_rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 68, 68), option_rect, width=2, border_radius=10)
            self.draw_text(f"{i + 1}. {option}", option_rect.x + 18, option_rect.y + 7, self.small_font, color=(240, 240, 240))

    def draw_end_screen(self, title: str, subtitle: str) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 14, 175))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(130, 170, 700, 190)
        pygame.draw.rect(self.screen, (20, 20, 24), panel, border_radius=24)
        pygame.draw.rect(self.screen, (255, 68, 68), panel, width=3, border_radius=24)
        self.draw_text(title, WIDTH // 2, 225, self.large_font, center=True, color=(255, 245, 245))
        self.draw_text(subtitle, WIDTH // 2, 305, self.small_font, center=True, color=(255, 190, 190))

    def run(self) -> None:
        try:
            while self.running:
                dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
                actions = self.hardware.poll_actions()
                self.update(dt, actions)
                self.draw()
                self.monitor.sample(self.clock.get_fps())
        finally:
            self.monitor.save(ROOT / "logs" / "performance.csv")
            self.hardware.close()
            pygame.quit()


def main() -> int:
    try:
        Game().run()
        return 0
    except (OSError, ValueError, pygame.error) as error:
        print(f"Erro ao iniciar o jogo: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
