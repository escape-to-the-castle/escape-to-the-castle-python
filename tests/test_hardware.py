import json
import math
import wave
from pathlib import Path

from src.game.assets import load_brackeys_sounds
from src.hardware.factory import create_hardware
from src.hardware.freenove import FreenoveHardware
from src.hardware.interface import Action, OutputState
from src.hardware.joystick import FreenoveJoystick, JoystickConfig
from src.hardware.keyboard import KeyboardHardware
from src.hardware.passive_audio import PassiveBuzzerTrack, ToneEvent, rom_steps_to_tone_events, wav_to_rom_steps


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


class FakeADC:
    def __init__(self, x: int = 128, y: int = 128) -> None:
        self.values = {5: x, 6: y}
        self.closed = False

    def analogRead(self, channel: int) -> int:
        return self.values[channel]

    def close(self) -> None:
        self.closed = True


def test_keyboard_remains_the_default_hardware():
    assert isinstance(create_hardware(mode="keyboard"), KeyboardHardware)


def test_freenove_adapter_reads_colored_buttons_on_press_edge():
    devices: dict[int, FakeDevice] = {}

    def factory(pin: int, **kwargs) -> FakeDevice:
        device = FakeDevice(pin, **kwargs)
        devices[pin] = device
        return device

    hardware = FreenoveHardware(button_factory=factory, led_factory=factory, buzzer_factory=factory)
    devices[hardware.pins.answer_2].is_pressed = True

    assert hardware.poll_actions() == {Action.ANSWER_2}
    assert hardware.poll_actions() == set()


def test_red_rolls_and_blue_jumps_without_duplicate_gpio_devices():
    devices: dict[int, FakeDevice] = {}
    created_pins: list[int] = []

    def factory(pin: int, **kwargs) -> FakeDevice:
        device = FakeDevice(pin, **kwargs)
        devices[pin] = device
        created_pins.append(pin)
        return device

    hardware = FreenoveHardware(button_factory=factory, led_factory=factory, buzzer_factory=factory)

    devices[hardware.pins.answer_1].is_pressed = True
    assert hardware.poll_actions() == {Action.ANSWER_1, Action.RESTART, Action.ROLL}

    devices[hardware.pins.answer_1].is_pressed = False
    hardware.poll_actions()
    devices[hardware.pins.answer_3].is_pressed = True
    assert hardware.poll_actions() == {Action.ANSWER_3, Action.JUMP}

    assert created_pins.count(hardware.pins.answer_1) == 1
    assert created_pins.count(hardware.pins.answer_3) == 1


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


def test_joystick_maps_x_axis_roll_and_click_to_game_actions():
    adc = FakeADC(x=40, y=220)
    button = FakeDevice(7)
    joystick = FreenoveJoystick(
        config=JoystickConfig(),
        adc=adc,
        button_factory=lambda _pin, **_kwargs: button,
    )

    assert joystick.poll_actions() == {Action.MOVE_RIGHT, Action.ROLL}
    assert joystick.poll_actions() == {Action.MOVE_RIGHT}

    adc.values[5] = 220
    adc.values[6] = 128
    button.is_pressed = True
    assert joystick.poll_actions() == {Action.MOVE_LEFT, Action.JUMP, Action.START}
    assert joystick.poll_actions() == {Action.MOVE_LEFT}

    joystick.close()
    assert adc.closed and button.closed


def test_freenove_adapter_combines_joystick_and_colored_button():
    devices: dict[int, FakeDevice] = {}

    def factory(pin: int, **kwargs) -> FakeDevice:
        device = FakeDevice(pin, **kwargs)
        devices[pin] = device
        return device

    class FakeJoystick:
        def poll_actions(self):
            return {Action.MOVE_RIGHT}

        def close(self):
            pass

    hardware = FreenoveHardware(
        button_factory=factory,
        led_factory=factory,
        buzzer_factory=factory,
        joystick=FakeJoystick(),
    )
    devices[hardware.pins.answer_4].is_pressed = True

    assert hardware.poll_actions() == {Action.MOVE_RIGHT, Action.ANSWER_4}


def test_wav_analysis_generates_rom_steps(tmp_path: Path):
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

    steps = wav_to_rom_steps(wav_path, window_seconds=0.05)
    events = rom_steps_to_tone_events(steps)

    assert steps
    assert any(event.frequency is not None and abs(event.frequency - frequency) < 80 for event in events)


def test_buzzer_rom_manifest_can_roundtrip(tmp_path: Path):
    manifest_path = tmp_path / "buzzer_roms.json"
    payload = {
        "format": "escape-to-the-castle-buzzer-rom-v1",
        "duration_ms": 20,
        "sounds": {
            "jump": [{"tone": 153, "duration_ticks": 2}, {"tone": 191, "duration_ticks": 2}],
        },
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["sounds"]["jump"][0]["tone"] == 153


def test_sound_loader_reuses_existing_hardware_buzzer(tmp_path: Path):
    manifest_path = tmp_path / "data" / "buzzer_roms.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps({"sounds": {"jump": [{"tone": 153, "duration_ticks": 2}]}}),
        encoding="utf-8",
    )
    buzzer = FakeDevice(4)

    sounds = load_brackeys_sounds(tmp_path, backend="freenove", buzzer=buzzer)

    assert sounds["jump"]._buzzer is buzzer


def test_passive_track_stops_buzzer_even_when_play_fails():
    class FailingBuzzer:
        def __init__(self) -> None:
            self.stopped = False

        def play(self, _frequency) -> None:
            raise ValueError("frequência inválida")

        def stop(self) -> None:
            self.stopped = True

    buzzer = FailingBuzzer()
    track = PassiveBuzzerTrack(buzzer, (ToneEvent(440.0, 0.01),))

    track._run(track._generation)

    assert buzzer.stopped is True
