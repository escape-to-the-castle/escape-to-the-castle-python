from __future__ import annotations

import pygame

from .config import (
    PLAYER_GRAVITY,
    PLAYER_HEIGHT,
    PLAYER_JUMP_SPEED,
    PLAYER_ROLL_DURATION_SECONDS,
    PLAYER_ROLL_HEIGHT,
    PLAYER_ROLL_SPEED,
    PLAYER_SPEED,
    PLAYER_WIDTH,
)


class Player:
    # A colisão é deliberadamente menor que o sprite para deixar os
    # movimentos e saltos mais tolerantes nas bordas dos obstáculos.
    WIDTH = PLAYER_WIDTH
    HEIGHT = PLAYER_HEIGHT
    SPEED = PLAYER_SPEED
    JUMP_SPEED = PLAYER_JUMP_SPEED
    GRAVITY = PLAYER_GRAVITY
    ROLL_HEIGHT = PLAYER_ROLL_HEIGHT
    ROLL_SPEED = PLAYER_ROLL_SPEED
    ROLL_DURATION = PLAYER_ROLL_DURATION_SECONDS

    def __init__(self, x: float, ground_y: int) -> None:
        self.x = x
        self.y = float(ground_y - self.HEIGHT)
        self.vy = 0.0
        self.ground_y = ground_y
        self.on_ground = True
        self.speed = self.SPEED
        self.is_rolling = False
        self.roll_time_left = 0.0
        self.roll_direction = 1

    @property
    def height(self) -> int:
        return self.ROLL_HEIGHT if self.is_rolling else self.HEIGHT

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.height)

    def start_roll(self, direction: int) -> None:
        if self.is_rolling or not self.on_ground:
            return
        bottom = self.y + self.HEIGHT
        self.is_rolling = True
        self.roll_time_left = self.ROLL_DURATION
        self.roll_direction = 1 if direction >= 0 else -1
        self.y = bottom - self.ROLL_HEIGHT

    def try_finish_roll(self, solids: list[pygame.Rect]) -> bool:
        if not self.is_rolling:
            return True
        standing_y = self.y + self.ROLL_HEIGHT - self.HEIGHT
        standing_rect = pygame.Rect(round(self.x), round(standing_y), self.WIDTH, self.HEIGHT)
        if any(standing_rect.colliderect(solid) for solid in solids):
            return False
        self.y = standing_y
        self.is_rolling = False
        self.roll_time_left = 0.0
        return True

    def respawn(self, x: float, ground_y: int) -> None:
        self.x = x
        self.y = float(ground_y - self.HEIGHT)
        self.vy = 0.0
        self.on_ground = True
        self.is_rolling = False
        self.roll_time_left = 0.0

    def update(
        self,
        dt: float,
        direction: int,
        jump: bool,
        roll: bool,
        roll_direction: int,
        world_width: int,
        solids: list[pygame.Rect],
    ) -> None:
        if roll:
            self.start_roll(roll_direction)

        movement_direction = self.roll_direction if self.is_rolling else direction
        movement_speed = self.ROLL_SPEED if self.is_rolling else self.speed
        desired_x = max(
            0,
            min(self.x + movement_direction * movement_speed * dt, world_width - self.WIDTH),
        )
        horizontal_candidate = pygame.Rect(
            round(desired_x), round(self.y), self.WIDTH, self.height
        )
        blocked_by_solid = self.on_ground and any(
            horizontal_candidate.colliderect(solid) for solid in solids
        )
        if not blocked_by_solid:
            self.x = desired_x

        if jump and self.on_ground and not self.is_rolling:
            self.vy = self.JUMP_SPEED
            self.on_ground = False

        previous_bottom = self.y + self.height
        self.vy += self.GRAVITY * dt
        self.y += self.vy * dt
        self.on_ground = False

        if self.vy >= 0.0:
            player_rect = self.rect
            landing_y: float | None = None
            for solid in solids:
                if player_rect.right <= solid.left or player_rect.left >= solid.right:
                    continue
                if previous_bottom > solid.top + 8:
                    continue
                if player_rect.bottom < solid.top:
                    continue
                candidate = float(solid.top - self.height)
                if landing_y is None or candidate < landing_y:
                    landing_y = candidate

            if landing_y is not None:
                self.y = landing_y
                self.vy = 0.0
                self.on_ground = True

        if self.is_rolling:
            self.roll_time_left = max(0.0, self.roll_time_left - dt)
            if self.roll_time_left == 0.0:
                self.try_finish_roll(solids)


class WorldObject:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.rect = pygame.Rect(x, y, width, height)


class MovingObstacle(WorldObject):
    """Obstáculo que patrulha horizontalmente entre dois limites."""

    def __init__(self, x: int, y: int, width: int, height: int, min_x: int, max_x: int, speed: float) -> None:
        super().__init__(x, y, width, height)
        self.x = float(x)
        self.min_x = min_x
        self.max_x = max_x
        self.speed = speed
        self.direction = 1

    def update(self, dt: float) -> None:
        self.x += self.direction * self.speed * dt
        if self.x >= self.max_x:
            self.x = float(self.max_x)
            self.direction = -1
        elif self.x <= self.min_x:
            self.x = float(self.min_x)
            self.direction = 1
        self.rect.x = round(self.x)
