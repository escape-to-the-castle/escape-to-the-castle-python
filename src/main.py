from __future__ import annotations

import sys
import time
from enum import Enum, auto
from pathlib import Path

import pygame

from .education.question_bank import Question, QuestionBank
from .game.assets import load_brackeys_sprites
from .game.config import (
    FPS,
    GROUND_TILE_WIDTH,
    GROUND_Y,
    PLAYER_SPRITE_SIZE,
    SCREEN_HEIGHT as HEIGHT,
    SCREEN_WIDTH as WIDTH,
    SHIELD_INVULNERABILITY_SECONDS,
    SPIKE_VISUAL_SIZE,
)
from .game.entities import Player, WorldObject
from .game.levels import PhaseId, build_layout
from .hardware.interface import Action, OutputState
from .hardware.keyboard import KeyboardHardware
from .monitoring.performance import PerformanceMonitor


ROOT = Path(__file__).resolve().parents[1]


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    QUESTION = auto()
    FEEDBACK = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Fuja para o Castelo - Protótipo")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 26)
        self.large_font = pygame.font.Font(None, 56)
        self.sprites = load_brackeys_sprites(ROOT)
        self.hardware = KeyboardHardware()
        self.question_bank = QuestionBank(ROOT / "data" / "questions.json")
        self.monitor = PerformanceMonitor()
        self.running = True
        self.current_phase = PhaseId.PROTOTYPE
        self.active_layout = build_layout(self.current_phase)
        self.start_phase(self.current_phase)
        self.show_main_menu()

    def reset_phase(self) -> None:
        self.player = Player(self.active_layout.player_start_x, GROUND_Y)
        self.obstacles = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.obstacles]
        self.portals = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.portals]
        self.platforms = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.platforms]
        self.holes = [WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.holes]
        self.ground_segments = [
            WorldObject(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height) for obj in self.active_layout.ground_segments
        ]
        self.triggered_portals: set[int] = set()
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
        self.invulnerable_until = 0.0
        self.state = GameState.PLAYING
        self.current_question: Question | None = None
        self.question_started = 0.0
        self.feedback_text = ""
        self.feedback_until = 0.0
        self.feedback_returns_to_playing = True
        self.last_safe_x = self.player.x
        self.animation_time = 0.0
        self.player_facing = 1

    def show_main_menu(self) -> None:
        self.state = GameState.MENU
        self.feedback_text = ""
        self.feedback_until = 0.0
        self.feedback_returns_to_playing = True
        self.current_question = None

    def start_phase(self, phase: PhaseId) -> None:
        self.current_phase = phase
        self.active_layout = build_layout(phase)
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

    def resolve_answer(self, selected: int) -> None:
        assert self.current_question is not None
        elapsed = time.monotonic() - self.question_started
        if selected == self.current_question.correct_index:
            bonus = 5 if elapsed <= 5.0 else 0
            self.coins += 10 + bonus
            self.streak += 1
            if self.streak == 3:
                self.has_shield = True
            if self.streak == 5:
                self.lives += 1
            extra = " + bônus de rapidez!" if bonus else ""
            self.feedback_text = f"Correto! +{10 + bonus} moedas{extra}"
        else:
            self.streak = 0
            self.feedback_text = f"Quase! {self.current_question.explanation}"
        self.feedback_until = time.monotonic() + 2.4
        self.state = GameState.FEEDBACK

    def on_hazard(self, _cause: str) -> None:
        now = time.monotonic()
        if now < self.invulnerable_until:
            return

        if self.has_shield:
            self.has_shield = False
            self.invulnerable_until = now + SHIELD_INVULNERABILITY_SECONDS
            self.feedback_text = "Escudo ativado! Sem dano por 3s."
        else:
            self.lives -= 1
            self.feedback_text = "Cuidado! Você perdeu uma vida."
        self.feedback_until = time.monotonic() + 1.5
        self.feedback_returns_to_playing = self.lives > 0
        # ``last_safe_x`` is recorded only while the player is standing on
        # solid ground, so falling into a pit can never create a checkpoint
        # in mid-air above that same pit.
        self.player.x = self.last_safe_x
        self.player.y = float(GROUND_Y - self.player.HEIGHT)
        self.player.vy = 0.0
        self.player.on_ground = True
        if self.lives <= 0:
            self.state = GameState.GAME_OVER
        else:
            self.state = GameState.FEEDBACK

    def update(self, dt: float, actions: set[Action]) -> None:
        if Action.QUIT in actions:
            self.running = False
            return

        self.animation_time += dt

        if self.state == GameState.MENU:
            if Action.ANSWER_1 in actions:
                self.start_phase(PhaseId.PROTOTYPE)
            elif Action.ANSWER_2 in actions:
                self.start_phase(PhaseId.PHASE_1)
            return

        if self.state in (GameState.GAME_OVER, GameState.VICTORY):
            if Action.RESTART in actions:
                self.show_main_menu()
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

        direction = int(Action.MOVE_RIGHT in actions) - int(Action.MOVE_LEFT in actions)
        if direction:
            self.player_facing = 1 if direction > 0 else -1
        solids = [obj.rect for obj in self.ground_segments] + [obj.rect for obj in self.platforms]
        self.player.update(dt, direction, Action.JUMP in actions, self.world_width, solids)

        fell_in_hole = self.player.y > HEIGHT + 40
        if fell_in_hole:
            self.on_hazard("hole")
            return

        if any(self.player.rect.colliderect(obj.rect) for obj in self.obstacles):
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
            if index not in self.triggered_portals and self.player.rect.colliderect(portal.rect):
                self.triggered_portals.add(index)
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
                feedback="shield" if self.has_shield or time.monotonic() < self.invulnerable_until else "neutral",
            )
        )

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

        ground_strip = self.sprites.get("platform_rows")
        for segment in self.ground_segments:
            seg = segment.rect.move(-camera_x, 0)
            if seg.right < -GROUND_TILE_WIDTH or seg.left > WIDTH + GROUND_TILE_WIDTH:
                continue
            if isinstance(ground_strip, list) and ground_strip:
                tile = pygame.transform.scale(ground_strip[0], (GROUND_TILE_WIDTH, 16))
                # Anchor tiles in world coordinates. Only the camera offset is
                # subtracted, preventing the texture from sliding over the
                # ground geometry as the camera follows the player.
                first_world_tile = (segment.rect.left // GROUND_TILE_WIDTH) * GROUND_TILE_WIDTH
                previous_clip = self.screen.get_clip()
                self.screen.set_clip(seg.clip(self.screen.get_rect()))
                for world_x in range(first_world_tile, segment.rect.right, GROUND_TILE_WIDTH):
                    self.screen.blit(tile, (world_x - int(camera_x), GROUND_Y))
                self.screen.set_clip(previous_clip)
            else:
                pygame.draw.rect(self.screen, (92, 159, 87), seg)
            pygame.draw.rect(self.screen, (84, 124, 73), (seg.x, GROUND_Y + 16, seg.width, HEIGHT - GROUND_Y - 16))

        for hole in self.holes:
            pit = hole.rect.move(-camera_x, 0)
            if pit.right < 0 or pit.left > WIDTH:
                continue
            pygame.draw.rect(self.screen, (27, 34, 46), pit)
            pygame.draw.ellipse(self.screen, (10, 16, 22), pit.inflate(0, -36), width=4)

        for world_x in range(90, self.world_width, 150):
            x = world_x - int(camera_x)
            if -10 <= x <= WIDTH + 10:
                pygame.draw.line(self.screen, (47, 116, 57), (x, GROUND_Y), (x, GROUND_Y - 13), 2)
                pygame.draw.circle(self.screen, (255, 216, 77), (x - 3, GROUND_Y - 14), 3)
                pygame.draw.circle(self.screen, (255, 245, 180), (x + 3, GROUND_Y - 14), 3)

    def draw_platform(self, rect: pygame.Rect) -> None:
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
        color = (130, 130, 130) if triggered else (82, 47, 190)
        pygame.draw.ellipse(self.screen, color, rect, width=4)
        pygame.draw.ellipse(self.screen, (255, 255, 255), rect.inflate(-10, -10), width=2)
        coin_frames = self.sprites.get("coins")
        if isinstance(coin_frames, list) and coin_frames:
            frame = coin_frames[int(self.animation_time * 12) % len(coin_frames)]
            coin_rect = frame.get_rect(center=rect.center)
            self.screen.blit(frame, coin_rect)
        elif self.sprites.get("fruit"):
            fruit = self.sprites["fruit"]
            assert isinstance(fruit, pygame.Surface)
            fruit_rect = fruit.get_rect(center=rect.center)
            self.screen.blit(fruit, fruit_rect)
        else:
            pygame.draw.circle(self.screen, (255, 68, 68) if not triggered else (180, 180, 180), rect.center, 6)

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
        frame: pygame.Surface | None = None
        if not self.player.on_ground and isinstance(jump_frame, pygame.Surface):
            frame = jump_frame
        elif abs(self.player.vy) < 20 and isinstance(idle_frames, list) and idle_frames:
            frame = idle_frames[int(self.animation_time * 5) % len(idle_frames)]
        elif isinstance(run_frames, list) and run_frames:
            frame = run_frames[int(self.animation_time * 10) % len(run_frames)]

        if isinstance(frame, pygame.Surface):
            sprite = pygame.transform.flip(frame, self.player_facing < 0, False)
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
        panel = pygame.Rect(16, 16, 520, 84)
        pygame.draw.rect(self.screen, (18, 18, 22), panel, border_radius=12)
        pygame.draw.rect(self.screen, (255, 68, 68), panel, width=2, border_radius=12)
        self.draw_text("Vidas", 58, 31, self.small_font, color=(255, 170, 170))
        self.draw_text(f"{self.lives}", 58, 50, self.small_font, color=(255, 255, 255))
        coin_frames = self.sprites.get("coins")
        if isinstance(coin_frames, list) and coin_frames:
            frame = coin_frames[int(self.animation_time * 12) % len(coin_frames)]
            self.screen.blit(frame, frame.get_rect(center=(120, 40)))
        self.draw_text(f"{self.coins}", 140, 50, self.small_font, color=(255, 255, 255))
        self.draw_text("Sequência", 215, 31, self.small_font, color=(255, 170, 170))
        self.draw_text(f"{self.streak}", 215, 50, self.small_font, color=(255, 255, 255))
        self.draw_text("Escudo", 318, 31, self.small_font, color=(255, 170, 170))
        shield_status = "sim" if self.has_shield else "não"
        self.draw_text(shield_status, 318, 50, self.small_font, color=(255, 255, 255))

        invulnerable_left = max(0.0, self.invulnerable_until - time.monotonic())
        inv_text = f"Invuln.: {invulnerable_left:.1f}s" if invulnerable_left > 0 else "Invuln.: 0.0s"
        self.draw_text(inv_text, 404, 50, self.small_font, color=(187, 224, 255))
        self.draw_text(self.active_layout.name, 28, 73, self.small_font, color=(255, 190, 190))

        progress = min(1.0, self.player.x / self.castle.rect.x)
        bar_bg = pygame.Rect(560, 24, 250, 18)
        pygame.draw.rect(self.screen, (18, 18, 22), bar_bg, border_radius=8)
        pygame.draw.rect(self.screen, (255, 68, 68), (563, 27, int(244 * progress), 12), border_radius=6)
        self.draw_text("Progresso", 685, 48, self.small_font, center=True, color=(255, 240, 240))

    def draw_main_menu(self) -> None:
        self.draw_background(0)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 8, 14, 165))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(130, 96, 700, 350)
        pygame.draw.rect(self.screen, (20, 20, 24), panel, border_radius=24)
        pygame.draw.rect(self.screen, (255, 68, 68), panel, width=3, border_radius=24)
        self.draw_text("Fuja para o Castelo", WIDTH // 2, 148, self.large_font, center=True, color=(255, 245, 245))
        self.draw_text("Escolha uma fase", WIDTH // 2, 188, self.font, center=True, color=(255, 190, 190))

        option_1 = pygame.Rect(184, 230, 592, 62)
        option_2 = pygame.Rect(184, 307, 592, 92)
        pygame.draw.rect(self.screen, (32, 32, 38), option_1, border_radius=12)
        pygame.draw.rect(self.screen, (255, 68, 68), option_1, width=2, border_radius=12)
        pygame.draw.rect(self.screen, (32, 32, 38), option_2, border_radius=12)
        pygame.draw.rect(self.screen, (255, 68, 68), option_2, width=2, border_radius=12)
        self.draw_text("1. Protótipo (fase original)", option_1.x + 22, option_1.y + 18, self.small_font, color=(240, 240, 240))
        self.draw_text("2. Fase 1 (buracos, desníveis e 5 perguntas)", option_2.x + 22, option_2.y + 19, self.small_font, color=(240, 240, 240))
        self.draw_text("Use 1 ou 2 para iniciar", option_2.x + 22, option_2.y + 52, self.small_font, color=(255, 190, 190))

    def draw(self) -> None:
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

        for index, portal in enumerate(self.portals):
            portal_anchor = portal.rect.move(-camera_x, 0)
            self.draw_portal(portal_anchor, index in self.triggered_portals)

        castle_anchor = self.castle.rect.move(-camera_x, 0)
        self.draw_castle(castle_anchor)

        player_anchor = self.player.rect.move(-camera_x, 0)
        shield_visible = self.has_shield or (time.monotonic() < self.invulnerable_until)
        self.draw_player(player_anchor, shield_visible)
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
