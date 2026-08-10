from src.hardware.factory import create_hardware
from src.hardware.freenove import FreenoveHardware
from src.hardware.interface import Action, OutputState
from src.hardware.keyboard import KeyboardHardware


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
