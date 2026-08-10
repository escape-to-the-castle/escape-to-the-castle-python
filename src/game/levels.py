"""Layouts declarativos e validação de acessibilidade das fases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .config import GROUND_Y, PLAYER_GRAVITY, PLAYER_JUMP_SPEED, SCREEN_HEIGHT
from .entities import WorldObject


class PhaseId(Enum):
    PROTOTYPE = auto()
    PHASE_1 = auto()
    PHASE_2 = auto()


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
    moving_obstacles: tuple["MovingObstacleSpec", ...] = ()


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


@dataclass(frozen=True)
class MovingObstacleSpec:
    x: int
    y: int
    min_x: int
    max_x: int
    speed: float
    width: int = 48
    height: int = 24


QUESTION_MARKER_SIZE = 24


def make_question_marker(center_x: int, center_y: int) -> WorldObject:
    half_size = QUESTION_MARKER_SIZE // 2
    return WorldObject(center_x - half_size, center_y - half_size, QUESTION_MARKER_SIZE, QUESTION_MARKER_SIZE)


PHASE_1_PLATFORMS = (
    PlatformSpec(x=760, width=220, rise=96, approach_rise=0),
    PlatformSpec(x=1120, width=180, rise=66, approach_rise=96),
    PlatformSpec(x=1430, width=220, rise=126, approach_rise=66),
    PlatformSpec(x=1780, width=180, rise=96, approach_rise=126),
    # Após o terceiro buraco, a aproximação volta a ser pelo chão.
    PlatformSpec(x=2310, width=220, rise=96, approach_rise=0),
    PlatformSpec(x=2580, width=200, rise=176, approach_rise=96),
)


PHASE_2_PLATFORMS = (
    PlatformSpec(x=610, width=190, rise=76, approach_rise=0),
    PlatformSpec(x=870, width=140, rise=166, approach_rise=76),
    PlatformSpec(x=1090, width=210, rise=96, approach_rise=166),
    # A segunda sequência começa novamente a partir do chão.
    PlatformSpec(x=1780, width=200, rise=86, approach_rise=0),
    PlatformSpec(x=2040, width=180, rise=156, approach_rise=86),
    PlatformSpec(x=2300, width=150, rise=146, approach_rise=156),
    # A plataforma baixa prepara o salto para a pergunta seguinte, que não
    # pode ser alcançada diretamente do chão.
    PlatformSpec(x=2740, width=140, rise=70, approach_rise=0),
    PlatformSpec(x=2940, width=130, rise=150, approach_rise=70),
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
        portals=[make_question_marker(x + 22, GROUND_Y - 46) for x in (760, 1380, 2050)],
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
            make_question_marker(342, GROUND_Y - 46),
            make_question_marker(887, GROUND_Y - 136),
            make_question_marker(1502, GROUND_Y - 106),
            make_question_marker(2162, GROUND_Y - 46),
            make_question_marker(2682, GROUND_Y - 166),
        ],
        platforms=[spec.to_world_object() for spec in PHASE_1_PLATFORMS],
        holes=[WorldObject(start, GROUND_Y, end - start, SCREEN_HEIGHT - GROUND_Y) for start, end in hole_ranges],
        ground_segments=make_ground_segments(world_width, hole_ranges),
        castle=WorldObject(2890, GROUND_Y - 220, 200, 220),
    )


def build_phase_2_layout() -> PhaseLayout:
    validate_platform_specs(PHASE_2_PLATFORMS)
    world_width = 3600
    hole_ranges = ((400, 550), (1320, 1480), (2520, 2690), (3100, 3260))
    return PhaseLayout(
        name="Fase 2",
        world_width=world_width,
        player_start_x=70,
        obstacles=[
            WorldObject(300, GROUND_Y - 24, 48, 24),
            WorldObject(1160, GROUND_Y - 120, 48, 24),
            WorldObject(2420, GROUND_Y - 24, 48, 24),
        ],
        portals=[
            make_question_marker(232, GROUND_Y - 46),
            make_question_marker(940, GROUND_Y - 212),
            make_question_marker(1562, GROUND_Y - 46),
            make_question_marker(2375, GROUND_Y - 192),
            make_question_marker(3005, GROUND_Y - 196),
            make_question_marker(3332, GROUND_Y - 46),
        ],
        platforms=[spec.to_world_object() for spec in PHASE_2_PLATFORMS],
        holes=[WorldObject(start, GROUND_Y, end - start, SCREEN_HEIGHT - GROUND_Y) for start, end in hole_ranges],
        ground_segments=make_ground_segments(world_width, hole_ranges),
        castle=WorldObject(3390, GROUND_Y - 220, 200, 220),
        moving_obstacles=(
            # Patrulhas curtas e previsíveis, sempre com espaço para saltar.
            MovingObstacleSpec(690, GROUND_Y - 100, 680, 730, 75.0),
            MovingObstacleSpec(1640, GROUND_Y - 24, 1600, 1690, 90.0),
            MovingObstacleSpec(2120, GROUND_Y - 180, 2110, 2160, 80.0),
        ),
    )


def build_layout(phase: PhaseId) -> PhaseLayout:
    if phase is PhaseId.PHASE_1:
        return build_phase_1_layout()
    if phase is PhaseId.PHASE_2:
        return build_phase_2_layout()
    return build_prototype_layout()
