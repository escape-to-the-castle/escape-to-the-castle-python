from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
import audioop
import threading
import time
import wave
from typing import Any


@dataclass(frozen=True)
class ToneEvent:
    frequency: float | None
    duration: float


@dataclass(frozen=True)
class RomStep:
    tone: int
    duration_ticks: int


ROM_MIN_FREQUENCY = 55.0
ROM_MAX_FREQUENCY = 1760.0
ROM_DURATION_MS = 20


def _merge_tone_events(events: list[ToneEvent]) -> tuple[ToneEvent, ...]:
    merged: list[ToneEvent] = []
    for event in events:
        if not merged:
            merged.append(event)
            continue

        previous = merged[-1]
        if previous.frequency is None and event.frequency is None:
            merged[-1] = ToneEvent(None, previous.duration + event.duration)
            continue

        if (
            previous.frequency is not None
            and event.frequency is not None
            and abs(previous.frequency - event.frequency) <= max(8.0, previous.frequency * 0.04)
        ):
            average_frequency = (previous.frequency + event.frequency) / 2.0
            merged[-1] = ToneEvent(average_frequency, previous.duration + event.duration)
            continue

        merged.append(event)
    return tuple(merged)


def frequency_to_rom_tone(frequency: float | None) -> int:
    if frequency is None or frequency <= 0:
        return 0

    clamped_frequency = min(max(frequency, ROM_MIN_FREQUENCY), ROM_MAX_FREQUENCY)
    span = math.log2(ROM_MAX_FREQUENCY) - math.log2(ROM_MIN_FREQUENCY)
    normalized = (math.log2(clamped_frequency) - math.log2(ROM_MIN_FREQUENCY)) / span
    return 1 + round(normalized * 254)


def rom_tone_to_frequency(tone: int) -> float | None:
    if tone <= 0:
        return None

    normalized = (tone - 1) / 254.0
    span = math.log2(ROM_MAX_FREQUENCY) - math.log2(ROM_MIN_FREQUENCY)
    return ROM_MIN_FREQUENCY * (2 ** (normalized * span))


def tone_events_to_rom_steps(events: tuple[ToneEvent, ...], duration_ms: int = ROM_DURATION_MS) -> tuple[RomStep, ...]:
    if duration_ms <= 0:
        raise ValueError("A duração do passo da ROM precisa ser positiva")

    steps: list[RomStep] = []
    for event in events:
        tone = frequency_to_rom_tone(event.frequency)
        ticks = max(1, round((event.duration * 1000.0) / duration_ms))
        if steps and steps[-1].tone == tone:
            steps[-1] = RomStep(tone, steps[-1].duration_ticks + ticks)
        else:
            steps.append(RomStep(tone, ticks))
    return tuple(steps)


def rom_steps_to_tone_events(steps: tuple[RomStep, ...], duration_ms: int = ROM_DURATION_MS) -> tuple[ToneEvent, ...]:
    events: list[ToneEvent] = []
    for step in steps:
        duration = step.duration_ticks * duration_ms / 1000.0
        events.append(ToneEvent(rom_tone_to_frequency(step.tone), duration))
    return tuple(events)


def wav_to_tone_events(path: Path, window_seconds: float = 0.05) -> tuple[ToneEvent, ...]:
    """Converte um WAV PCM em uma sequência curta de tons e pausas."""

    if window_seconds <= 0:
        raise ValueError("A janela de análise precisa ser positiva")

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        if sample_rate <= 0 or frame_count <= 0:
            return ()
        if sample_width not in (1, 2, 4):
            raise ValueError(f"{path.name} usa largura de amostra não suportada: {sample_width}")

        raw_audio = wav_file.readframes(frame_count)
        if channels == 2:
            raw_audio = audioop.tomono(raw_audio, sample_width, 0.5, 0.5)
        elif channels != 1:
            raise ValueError(f"{path.name} precisa ser mono ou estéreo")

    full_scale = float((1 << (8 * sample_width - 1)) - 1)
    silence_threshold = max(4.0, full_scale * 0.01)
    chunk_size = max(sample_width, int(sample_rate * window_seconds) * sample_width)

    events: list[ToneEvent] = []
    for offset in range(0, len(raw_audio), chunk_size):
        chunk = raw_audio[offset : offset + chunk_size]
        if len(chunk) < sample_width:
            break

        duration = len(chunk) / (sample_width * sample_rate)
        if duration <= 0:
            continue

        if audioop.rms(chunk, sample_width) < silence_threshold:
            events.append(ToneEvent(None, duration))
            continue

        crossings = audioop.cross(chunk, sample_width)
        estimated_frequency = crossings / (2.0 * duration)
        if estimated_frequency < 60.0:
            events.append(ToneEvent(None, duration))
            continue

        events.append(ToneEvent(estimated_frequency, duration))

    return _merge_tone_events(events)


def wav_to_rom_steps(path: Path, window_seconds: float = 0.05) -> tuple[RomStep, ...]:
    return tone_events_to_rom_steps(wav_to_tone_events(path, window_seconds))


def serialize_rom_steps(steps: tuple[RomStep, ...]) -> str:
    return json.dumps(
        [{"tone": step.tone, "duration_ticks": step.duration_ticks} for step in steps],
        ensure_ascii=True,
        indent=2,
    )


def deserialize_rom_steps(payload: str) -> tuple[RomStep, ...]:
    data = json.loads(payload)
    return tuple(RomStep(int(item["tone"]), int(item["duration_ticks"])) for item in data)


class PassiveBuzzerTrack:
    def __init__(self, buzzer: Any, events: tuple[ToneEvent, ...]) -> None:
        self._buzzer = buzzer
        self._events = events
        self._generation = 0
        self._lock = threading.Lock()

    def play(self) -> None:
        with self._lock:
            self._generation += 1
            generation = self._generation
        thread = threading.Thread(target=self._run, args=(generation,), daemon=True)
        thread.start()

    def _run(self, generation: int) -> None:
        for event in self._events:
            if generation != self._generation:
                break

            if event.frequency is None:
                self._stop()
            else:
                self._play_frequency(event.frequency)

            time.sleep(event.duration)

        if generation == self._generation:
            self._stop()

    def _play_frequency(self, frequency: float) -> None:
        if hasattr(self._buzzer, "play"):
            self._buzzer.play(frequency)
            return
        raise RuntimeError("O buzzer passivo não oferece uma interface de tom")

    def _stop(self) -> None:
        if hasattr(self._buzzer, "stop"):
            self._buzzer.stop()
        elif hasattr(self._buzzer, "off"):
            self._buzzer.off()


class PassiveBuzzerRomTrack(PassiveBuzzerTrack):
    def __init__(self, buzzer: Any, steps: tuple[RomStep, ...]) -> None:
        super().__init__(buzzer, rom_steps_to_tone_events(steps))


class PassiveBuzzerLibrary:
    def __init__(self, buzzer_factory: Any, pin: int) -> None:
        self._buzzer = buzzer_factory(pin)

    def load_track(self, path: Path) -> PassiveBuzzerTrack:
        return PassiveBuzzerRomTrack(self._buzzer, wav_to_rom_steps(path))

    def load_rom_payload(self, payload: str) -> dict[str, PassiveBuzzerRomTrack]:
        manifest = json.loads(payload)
        sounds = manifest.get("sounds", {})
        return {
            name: PassiveBuzzerRomTrack(
                self._buzzer,
                tuple(RomStep(int(item["tone"]), int(item["duration_ticks"])) for item in steps),
            )
            for name, steps in sounds.items()
        }

    def load_rom_manifest(self, path: Path) -> dict[str, PassiveBuzzerRomTrack]:
        return self.load_rom_payload(path.read_text(encoding="utf-8"))

    def close(self) -> None:
        if hasattr(self._buzzer, "close"):
            self._buzzer.close()
