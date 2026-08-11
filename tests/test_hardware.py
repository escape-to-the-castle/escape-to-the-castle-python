import math
import wave
from pathlib import Path

from src.hardware.factory import create_hardware
from src.hardware.freenove import FreenoveHardware
from src.hardware.interface import Action, OutputState
from src.hardware.joystick import FreenoveJoystick, JoystickConfig
from src.hardware.keyboard import KeyboardHardware
from src.hardware.passive_audio import PassiveBuzzerTrack, ToneEvent, wav_to_tone_events


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


class FakeADC:
    def __init__(self, x: int = 128, y: int = 128) -> None:
        self.values = {5: x, 6: y}
        self.closed = False

    def analogRead(self, channel: int) -> int:
        return self.values[channel]

    def close(self) -> None:
        self.closed = True


def test_joystick_maps_x_axis_roll_and_click_to_game_actions():
    adc = FakeADC(x=40, y=220)
    button = FakeDevice(7)
    joystick = FreenoveJoystick(
        config=JoystickConfig(),
        adc=adc,
        button_factory=lambda _pin, **_kwargs: button,
    )

    assert joystick.poll_actions() == {Action.MOVE_LEFT, Action.ROLL}
    # Rolagem e clique são eventos de borda; movimento é contínuo.
    assert joystick.poll_actions() == {Action.MOVE_LEFT}

    adc.values[5] = 220
    adc.values[6] = 128
    button.is_pressed = True
    assert joystick.poll_actions() == {Action.MOVE_RIGHT, Action.JUMP, Action.START}
    assert joystick.poll_actions() == {Action.MOVE_RIGHT}

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

    # Executa sincronamente para tornar a garantia de limpeza determinística.
    track._run(track._generation)

    assert buzzer.stopped is True
