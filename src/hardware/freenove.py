from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable

from .interface import Action, HardwareInterface, OutputState


@dataclass(frozen=True)
class FreenovePinConfig:
    """Pinagem BCM inicial; deve ser conferida antes da montagem física."""

    move_left: int = 17
    move_right: int = 27
    jump: int = 22
    answer_1: int = 5
    answer_2: int = 6
    answer_3: int = 13
    answer_4: int = 19
    led_red: int = 16
    led_green: int = 20
    led_blue: int = 21
    buzzer: int = 26


class FreenoveHardware(HardwareInterface):
    """Adaptador GPIO Zero para botões, LED RGB e buzzer do kit Freenove.

    GPIO Zero só é importado quando este adaptador é explicitamente ativado.
    As fábricas injetáveis permitem testar a integração sem um Raspberry Pi.
    """

    def __init__(
        self,
        pins: FreenovePinConfig | None = None,
        button_factory: Callable[..., Any] | None = None,
        led_factory: Callable[..., Any] | None = None,
        buzzer_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.pins = pins or FreenovePinConfig()
        if button_factory is None or led_factory is None or buzzer_factory is None:
            try:
                from gpiozero import Button, LED, TonalBuzzer
            except ImportError as error:
                raise RuntimeError(
                    "GPIO Zero não está instalado. Use CASTLE_HARDWARE=keyboard "
                    "ou instale python3-gpiozero no Raspberry Pi."
                ) from error
            button_factory = button_factory or Button
            led_factory = led_factory or LED
            buzzer_factory = buzzer_factory or TonalBuzzer

        self._buttons = {
            Action.MOVE_LEFT: button_factory(self.pins.move_left, pull_up=True, bounce_time=0.05),
            Action.MOVE_RIGHT: button_factory(self.pins.move_right, pull_up=True, bounce_time=0.05),
            Action.JUMP: button_factory(self.pins.jump, pull_up=True, bounce_time=0.05),
            Action.ANSWER_1: button_factory(self.pins.answer_1, pull_up=True, bounce_time=0.05),
            Action.ANSWER_2: button_factory(self.pins.answer_2, pull_up=True, bounce_time=0.05),
            Action.ANSWER_3: button_factory(self.pins.answer_3, pull_up=True, bounce_time=0.05),
            Action.ANSWER_4: button_factory(self.pins.answer_4, pull_up=True, bounce_time=0.05),
        }
        self._continuous_actions = {Action.MOVE_LEFT, Action.MOVE_RIGHT}
        self._previously_pressed: set[Action] = set()
        self._leds = {
            "red": led_factory(self.pins.led_red),
            "green": led_factory(self.pins.led_green),
            "blue": led_factory(self.pins.led_blue),
        }
        self._buzzer = buzzer_factory(self.pins.buzzer)
        self._feedback_generation = 0
        self._feedback_lock = threading.Lock()
        self._last_feedback = "neutral"

    def poll_actions(self) -> set[Action]:
        pressed = {action for action, button in self._buttons.items() if button.is_pressed}
        actions = (pressed & self._continuous_actions) | (pressed - self._previously_pressed)
        self._previously_pressed = pressed
        return actions

    def update_outputs(self, state: OutputState) -> None:
        colors = {
            "correct": (False, True, False),
            "error": (True, False, False),
            "shield": (False, False, True),
            "neutral": (False, False, False),
        }
        red, green, blue = colors.get(state.feedback, colors["neutral"])
        for led, enabled in zip(self._leds.values(), (red, green, blue)):
            led.on() if enabled else led.off()

        if state.feedback in {"correct", "error"} and state.feedback != self._last_feedback:
            frequency = 880.0 if state.feedback == "correct" else 220.0
            self._play_feedback_tone(frequency, 0.08)
        self._last_feedback = state.feedback

    def _play_feedback_tone(self, frequency: float, duration: float) -> None:
        if hasattr(self._buzzer, "play"):
            with self._feedback_lock:
                self._feedback_generation += 1
                generation = self._feedback_generation
            self._buzzer.play(frequency)

            def stop_after_delay() -> None:
                time.sleep(duration)
                with self._feedback_lock:
                    if generation != self._feedback_generation:
                        return
                if hasattr(self._buzzer, "stop"):
                    self._buzzer.stop()

            threading.Thread(target=stop_after_delay, daemon=True).start()
            return

        self._buzzer.beep(on_time=duration, off_time=0.05, n=1, background=True)

    def close(self) -> None:
        for device in [*self._buttons.values(), *self._leds.values(), self._buzzer]:
            device.close()
