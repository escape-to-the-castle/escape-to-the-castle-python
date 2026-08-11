import math
import wave
from pathlib import Path

from src.hardware.factory import create_hardware
from src.hardware.freenove import FreenoveHardware
from src.hardware.interface import Action, OutputState
from src.hardware.keyboard import KeyboardHardware
from src.hardware.passive_audio import wav_to_tone_events


class FakeDevice:
    def __init__(self, pin: int, **_kwargs) -> None:
        self.pin = pin
        self.is_pressed = False
        self.active = False
        self.closed = False
        self.beeps = 0

    def on(self) -> None:
        self.active = True

    def off(self) -> None:
        self.active = False

    def beep(self, **_kwargs) -> None:
        self.beeps += 1

    def close(self) -> None:
        self.closed = True


def test_keyboard_remains_the_default_hardware():
    assert isinstance(create_hardware(mode="keyboard"), KeyboardHardware)


def test_freenove_adapter_reads_continuous_and_edge_triggered_inputs():
    devices: dict[int, FakeDevice] = {}

    def factory(pin: int, **kwargs) -> FakeDevice:
        device = FakeDevice(pin, **kwargs)
        devices[pin] = device
        return device

    hardware = FreenoveHardware(button_factory=factory, led_factory=factory, buzzer_factory=factory)
    devices[hardware.pins.move_right].is_pressed = True
    devices[hardware.pins.jump].is_pressed = True

    assert hardware.poll_actions() == {Action.MOVE_RIGHT, Action.JUMP}
    assert hardware.poll_actions() == {Action.MOVE_RIGHT}


def test_freenove_adapter_updates_outputs_and_closes_devices():
    created: list[FakeDevice] = []

    def factory(pin: int, **kwargs) -> FakeDevice:
        device = FakeDevice(pin, **kwargs)
        created.append(device)
        return device

    hardware = FreenoveHardware(button_factory=factory, led_factory=factory, buzzer_factory=factory)
    hardware.update_outputs(OutputState(feedback="correct"))

    assert hardware._leds["green"].active is True
    assert hardware._leds["red"].active is False
    assert hardware._buzzer.beeps == 1

    hardware.close()
    assert all(device.closed for device in created)


def test_wav_analysis_generates_tone_events(tmp_path: Path):
    wav_path = tmp_path / "tone.wav"
    sample_rate = 8000
    duration = 0.2
    frequency = 440.0
    amplitude = 12000

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for index in range(int(sample_rate * duration)):
            value = int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(frames))

    events = wav_to_tone_events(wav_path, window_seconds=0.05)

    assert events
    assert any(event.frequency is not None and abs(event.frequency - frequency) < 80 for event in events)
