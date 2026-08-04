"""Layouts declarativos e validação de acessibilidade das fases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .config import GROUND_Y, PLAYER_GRAVITY, PLAYER_JUMP_SPEED, SCREEN_HEIGHT
from .entities import WorldObject


class PhaseId(Enum):
    PROTOTYPE = auto()
    PHASE_1 = auto()


@dataclass(frozen=True)
class PhaseLayout:
    name: str
    world_width: int
    player_start_x: int
    obstacles: list[WorldObject]
    portals: list[WorldObject]
    platforms: list[WorldObject]
    holes: list[WorldObject]
    ground_segments: list[WorldObject]
    castle: WorldObject


@dataclass(frozen=True)
class PlatformSpec:
    """Plataforma posicionada por elevação em relação ao chão."""

    x: int
    width: int
    rise: int
    approach_rise: int = 0
    height: int = 16

    def to_world_object(self) -> WorldObject:
        return WorldObject(self.x, GROUND_Y - self.rise, self.width, self.height)


PHASE_1_PLATFORMS = (
    PlatformSpec(x=760, width=220, rise=96, approach_rise=0),
    PlatformSpec(x=1120, width=180, rise=66, approach_rise=96),
    PlatformSpec(x=1430, width=220, rise=126, approach_rise=66),
    PlatformSpec(x=1780, width=180, rise=96, approach_rise=126),
    # Após o terceiro buraco, a aproximação volta a ser pelo chão.
    PlatformSpec(x=2310, width=220, rise=96, approach_rise=0),
    PlatformSpec(x=2580, width=200, rise=176, approach_rise=96),
)


def maximum_jump_rise() -> float:
    return PLAYER_JUMP_SPEED**2 / (2 * PLAYER_GRAVITY)


def validate_platform_specs(specs: tuple[PlatformSpec, ...]) -> None:
    jump_rise = maximum_jump_rise()
    for spec in specs:
        required_rise = spec.rise - spec.approach_rise
        if required_rise > jump_rise:
            raise ValueError(
                f"Plataforma em x={spec.x} exige subida de {required_rise}px; "
                f"o jogador alcança apenas {jump_rise:.1f}px."
            )


def make_ground_segments(world_width: int, hole_ranges: tuple[tuple[int, int], ...]) -> list[WorldObject]:
    segments: list[WorldObject] = []
    current_x = 0
    for hole_start, hole_end in sorted(hole_ranges):
        hole_start = max(0, min(hole_start, world_width))
        hole_end = max(0, min(hole_end, world_width))
        if hole_start > current_x:
            segments.append(WorldObject(current_x, GROUND_Y, hole_start - current_x, SCREEN_HEIGHT - GROUND_Y))
        current_x = max(current_x, hole_end)
    if current_x < world_width:
        segments.append(WorldObject(current_x, GROUND_Y, world_width - current_x, SCREEN_HEIGHT - GROUND_Y))
    return segments


def build_prototype_layout() -> PhaseLayout:
    world_width = 2600
    return PhaseLayout(
        name="Protótipo",
        world_width=world_width,
        player_start_x=80,
        obstacles=[WorldObject(x, GROUND_Y - 24, 48, 24) for x in (526, 1056, 1711)],
        portals=[WorldObject(x, GROUND_Y - 92, 44, 92) for x in (760, 1380, 2050)],
        platforms=[],
        holes=[],
        ground_segments=make_ground_segments(world_width, ()),
        castle=WorldObject(2380, GROUND_Y - 220, 200, 220),
    )


def build_phase_1_layout() -> PhaseLayout:
    validate_platform_specs(PHASE_1_PLATFORMS)
    world_width = 3100
    hole_ranges = ((520, 700), (1230, 1395), (2010, 2180))
    return PhaseLayout(
        name="Fase 1",
        world_width=world_width,
        player_start_x=70,
        obstacles=[
            WorldObject(420, GROUND_Y - 24, 48, 24),
            WorldObject(930, GROUND_Y - 144, 48, 24),
            WorldObject(1590, GROUND_Y - 24, 48, 24),
            WorldObject(1885, GROUND_Y - 114, 48, 24),
            WorldObject(2460, GROUND_Y - 24, 48, 24),
        ],
        portals=[
            WorldObject(320, GROUND_Y - 92, 44, 92),
            WorldObject(865, GROUND_Y - 182, 44, 92),
            WorldObject(1480, GROUND_Y - 152, 44, 92),
            WorldObject(2140, GROUND_Y - 92, 44, 92),
            WorldObject(2660, GROUND_Y - 212, 44, 92),
        ],
        platforms=[spec.to_world_object() for spec in PHASE_1_PLATFORMS],
        holes=[WorldObject(start, GROUND_Y, end - start, SCREEN_HEIGHT - GROUND_Y) for start, end in hole_ranges],
        ground_segments=make_ground_segments(world_width, hole_ranges),
        castle=WorldObject(2890, GROUND_Y - 220, 200, 220),
    )


def build_layout(phase: PhaseId) -> PhaseLayout:
    return build_phase_1_layout() if phase is PhaseId.PHASE_1 else build_prototype_layout()
