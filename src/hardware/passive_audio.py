from __future__ import annotations

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
    silence_threshold = max(700.0, full_scale * 0.03)
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


class PassiveBuzzerLibrary:
    def __init__(self, buzzer_factory: Any, pin: int) -> None:
        self._buzzer = buzzer_factory(pin)

    def load_track(self, path: Path) -> PassiveBuzzerTrack:
        return PassiveBuzzerTrack(self._buzzer, wav_to_tone_events(path))

    def close(self) -> None:
        if hasattr(self._buzzer, "close"):
            self._buzzer.close()
