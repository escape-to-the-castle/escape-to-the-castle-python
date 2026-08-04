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

    def update(self, dt: float, direction: int, jump: bool, world_width: int) -> None:
        self.x += direction * self.SPEED * dt
        self.x = max(0, min(self.x, world_width - self.WIDTH))

        if jump and self.on_ground:
            self.vy = self.JUMP_SPEED
            self.on_ground = False

        self.vy += self.GRAVITY * dt
        self.y += self.vy * dt
        floor = self.ground_y - self.HEIGHT
        if self.y >= floor:
            self.y = float(floor)
            self.vy = 0.0
            self.on_ground = True


class WorldObject:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.rect = pygame.Rect(x, y, width, height)
