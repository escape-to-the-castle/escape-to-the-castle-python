from __future__ import annotations

import pygame


class Player:
    # A colisão é deliberadamente menor que o sprite para deixar os
    # movimentos e saltos mais tolerantes nas bordas dos obstáculos.
    WIDTH = 30
    HEIGHT = 46
    SPEED = 270.0
    JUMP_SPEED = -560.0
    GRAVITY = 1450.0

    def __init__(self, x: float, ground_y: int) -> None:
        self.x = x
        self.y = float(ground_y - self.HEIGHT)
        self.vy = 0.0
        self.ground_y = ground_y
        self.on_ground = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    def update(self, dt: float, direction: int, jump: bool, world_width: int, solids: list[pygame.Rect]) -> None:
        self.x += direction * self.SPEED * dt
        self.x = max(0, min(self.x, world_width - self.WIDTH))

        if jump and self.on_ground:
            self.vy = self.JUMP_SPEED
            self.on_ground = False

        previous_bottom = self.y + self.HEIGHT
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
                candidate = float(solid.top - self.HEIGHT)
                if landing_y is None or candidate < landing_y:
                    landing_y = candidate

            if landing_y is not None:
                self.y = landing_y
                self.vy = 0.0
                self.on_ground = True


class WorldObject:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.rect = pygame.Rect(x, y, width, height)
