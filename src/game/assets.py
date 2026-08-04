"""Carregamento dos assets visuais usados pelo jogo."""

from __future__ import annotations

from pathlib import Path

import pygame

from .config import PLAYER_SPRITE_SIZE


def load_sheet_frames(
    path: Path,
    frame_width: int,
    frame_height: int,
    columns: int,
    rows: int,
    scale_to: tuple[int, int] | None = None,
) -> list[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    frames: list[pygame.Surface] = []
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(column * frame_width, row * frame_height, frame_width, frame_height)
            if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
                continue
            frame = sheet.subsurface(rect).copy()
            if scale_to is not None:
                frame = pygame.transform.smoothscale(frame, scale_to)
            frames.append(frame)
    return frames


def load_single_sprite(path: Path, scale_to: tuple[int, int] | None = None) -> pygame.Surface | None:
    if not path.exists():
        return None
    try:
        surface = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None
    if scale_to is not None:
        surface = pygame.transform.smoothscale(surface, scale_to)
    return surface


def load_brackeys_sprites(root: Path) -> dict[str, object]:
    sprites: dict[str, object] = {}
    directory = root / "brackeys_platformer_assets" / "sprites"
    knight = directory / "knight.png"
    sprites["player_idle"] = load_sheet_frames(knight, 32, 32, 4, 1, PLAYER_SPRITE_SIZE)
    sprites["player_run"] = load_sheet_frames(knight, 32, 32, 4, 2, PLAYER_SPRITE_SIZE)[4:8]
    player_jump = load_sheet_frames(knight, 32, 32, 1, 1, PLAYER_SPRITE_SIZE)
    sprites["player_jump"] = player_jump[0] if player_jump else None
    sprites["coins"] = load_sheet_frames(directory / "coin.png", 16, 16, 12, 1, (20, 20))
    sprites["platform_rows"] = load_sheet_frames(directory / "platforms.png", 64, 16, 1, 4)
    sprites["fruit"] = load_single_sprite(directory / "fruit.png", (34, 34))
    return sprites
