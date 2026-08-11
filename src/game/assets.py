"""Carregamento dos assets visuais e sonoros usados pelo jogo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import pygame

from .config import PLAYER_SPRITE_SIZE
from ..hardware.passive_audio import PassiveBuzzerLibrary


PLATFORM_TILE_SIZE = 16
PLATFORM_TILES_PER_ROW = 3
PlatformTiles = tuple[pygame.Surface, ...]


def load_sheet_frames(
    path: Path,
    frame_width: int,
    frame_height: int,
    columns: int,
    rows: int,
    scale_to: tuple[int, int] | None = None,
    start_column: int = 0,
    start_row: int = 0,
) -> list[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    frames: list[pygame.Surface] = []
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(
                (start_column + column) * frame_width,
                (start_row + row) * frame_height,
                frame_width,
                frame_height,
            )
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


def load_sound(path: Path) -> pygame.mixer.Sound | None:
    if not path.exists() or pygame.mixer.get_init() is None:
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        return None


def load_platform_rows(path: Path, tile_size: int = PLATFORM_TILE_SIZE) -> list[PlatformTiles]:
    """Carrega os três tiles detalhados de cada faixa de ``platforms.png``."""

    sheet = pygame.image.load(path).convert_alpha()
    required_width = tile_size * PLATFORM_TILES_PER_ROW
    if sheet.get_width() < required_width:
        raise ValueError(f"{path.name} não contém {PLATFORM_TILES_PER_ROW} tiles por faixa")

    rows: list[PlatformTiles] = []
    for y in range(0, sheet.get_height() - tile_size + 1, tile_size):
        tiles = tuple(
            sheet.subsurface(pygame.Rect(column * tile_size, y, tile_size, tile_size)).copy()
            for column in range(PLATFORM_TILES_PER_ROW)
        )
        rows.append(tiles)
    return rows


def compose_platform_strip(tiles: PlatformTiles, width: int) -> pygame.Surface:
    """Justapõe tiles inteiros, sem alongamento, até preencher a largura."""

    if not tiles or width <= 0:
        raise ValueError("A plataforma precisa de tiles e largura positiva")
    height = tiles[0].get_height()
    if any(tile.get_width() <= 0 or tile.get_height() != height for tile in tiles):
        raise ValueError("Todos os tiles da plataforma precisam ter a mesma altura")

    strip = pygame.Surface((width, height), pygame.SRCALPHA)
    x = 0
    tile_index = 0
    while x < width:
        tile = tiles[tile_index % len(tiles)]
        visible_width = min(tile.get_width(), width - x)
        strip.blit(tile, (x, 0), pygame.Rect(0, 0, visible_width, height))
        x += visible_width
        tile_index += 1
    return strip


def load_brackeys_sprites(root: Path) -> dict[str, object]:
    sprites: dict[str, object] = {}
    directory = root / "brackeys_platformer_assets" / "sprites"
    knight = directory / "knight.png"
    sprites["player_idle"] = load_sheet_frames(knight, 32, 32, 4, 1, PLAYER_SPRITE_SIZE)
    sprites["player_run"] = load_sheet_frames(
        knight, 32, 32, 8, 2, PLAYER_SPRITE_SIZE, start_row=2
    )
    player_jump = load_sheet_frames(knight, 32, 32, 1, 1, PLAYER_SPRITE_SIZE)
    sprites["player_jump"] = player_jump[0] if player_jump else None
    sprites["player_roll"] = load_sheet_frames(
        knight, 32, 32, 8, 1, PLAYER_SPRITE_SIZE, start_row=5
    )
    sprites["player_hit"] = load_sheet_frames(
        knight, 32, 32, 4, 1, PLAYER_SPRITE_SIZE, start_row=6
    )
    sprites["player_death"] = load_sheet_frames(
        knight, 32, 32, 4, 1, PLAYER_SPRITE_SIZE, start_row=7
    )
    sprites["coins"] = load_sheet_frames(directory / "coin.png", 16, 16, 12, 1, (20, 20))
    sprites["platform_rows"] = load_platform_rows(directory / "platforms.png")
    sprites["fruit"] = load_single_sprite(directory / "fruit.png", (34, 34))
    return sprites


def load_brackeys_sounds(
    root: Path,
    backend: str = "keyboard",
    buzzer_factory: Callable[..., object] | None = None,
    buzzer: object | None = None,
) -> dict[str, object | None]:
    directory = root / "brackeys_platformer_assets" / "sounds"
    rom_manifest = root / "data" / "buzzer_roms.json"
    sound_files = {
        "coin": "coin.wav",
        "jump": "jump.wav",
        "hurt": "hurt.wav",
        "power_up": "power_up.wav",
    }

    if backend.strip().lower() in {"freenove", "hybrid"}:
        if buzzer is not None:
            library = PassiveBuzzerLibrary(buzzer=buzzer)
            return {name: library.load_track(directory / filename) for name, filename in sound_files.items()}
        factory = buzzer_factory
        if factory is None:
            try:
                from gpiozero import TonalBuzzer
            except ImportError as error:
                raise RuntimeError(
                    "GPIO Zero não está instalado. Use CASTLE_HARDWARE=keyboard ou instale python3-gpiozero."
                ) from error
            factory = TonalBuzzer

        library = PassiveBuzzerLibrary(factory, 26)
        if rom_manifest.exists():
            return library.load_rom_manifest(rom_manifest)
        return {name: library.load_track(directory / filename) for name, filename in sound_files.items()}

    return {name: load_sound(directory / filename) for name, filename in sound_files.items()}
