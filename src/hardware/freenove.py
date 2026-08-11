from __future__ import annotations

import os
from dataclasses import dataclass
import threading
import time
from typing import Any, Callable

from .interface import Action, HardwareInterface, OutputState
from .joystick import FreenoveJoystick


@dataclass(frozen=True)
class FreenovePinConfig:
    """Pinagem BCM inicial; deve ser conferida antes da montagem física."""

    # Botões coloridos da placa: vermelho, amarelo, azul e verde.
    answer_1: int = 21
    answer_2: int = 26
    answer_3: int = 20
    answer_4: int = 16
    led_red: int = 17
    led_green: int = 24
    led_blue: int = 12
    buzzer: int = 4
    restart: int = 21

    @classmethod
    def from_env(cls) -> "FreenovePinConfig":
        """Carrega sobreposições ``CASTLE_PIN_*`` usando numeração BCM."""
        defaults = cls()
        values = {
            field_name: int(os.getenv(f"CASTLE_PIN_{field_name.upper()}", getattr(defaults, field_name)))
            for field_name in defaults.__dataclass_fields__
        }
        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        input_fields = {
            "answer_1",
            "answer_2",
            "answer_3",
            "answer_4",
            "restart",
        }
        assignments: dict[int, list[str]] = {}
        for field_name in self.__dataclass_fields__:
            pin = getattr(self, field_name)
            assignments.setdefault(pin, []).append(field_name)
        # Um botão pode assumir mais de uma ação (por exemplo, esquerda no
        # jogo e resposta 1 nas perguntas). Entradas e saídas nunca podem
        # compartilhar um GPIO.
        conflicts = {
            pin: names
            for pin, names in assignments.items()
            if len(names) > 1 and not set(names).issubset(input_fields)
        }
        if conflicts:
            details = ", ".join(f"GPIO {pin}: {', '.join(names)}" for pin, names in conflicts.items())
            raise ValueError(f"GPIO atribuído a mais de uma função: {details}")


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
        joystick: Any | None = None,
        enable_joystick: bool | None = None,
    ) -> None:
        self.pins = pins or FreenovePinConfig.from_env()
        self.pins.validate()
        self.debug = os.getenv("CASTLE_GPIO_DEBUG", "0").strip().lower() in {"1", "true", "yes"}
        using_real_factories = button_factory is None and led_factory is None and buzzer_factory is None
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

        action_pins = {
            Action.ANSWER_1: self.pins.answer_1,
            Action.ANSWER_2: self.pins.answer_2,
            Action.ANSWER_3: self.pins.answer_3,
            Action.ANSWER_4: self.pins.answer_4,
            Action.RESTART: self.pins.restart,
            # Controles redundantes caso o eixo/click analógico não esteja
            # disponível: vermelho rola e azul pula durante a fase.
            Action.ROLL: self.pins.answer_1,
            Action.JUMP: self.pins.answer_3,
        }
        self._button_devices = {
            pin: button_factory(pin, pull_up=True, bounce_time=0.05)
            for pin in set(action_pins.values())
        }
        self._buttons = {
            action: self._button_devices[pin]
            for action, pin in action_pins.items()
        }
        self._continuous_actions = {Action.MOVE_LEFT, Action.MOVE_RIGHT}
        self._previously_pressed: set[Action] = set()
        if enable_joystick is None:
            # Na placa real o joystick é o controle principal. Em testes com
            # fábricas injetadas ele permanece desligado por padrão.
            default_enabled = "1" if using_real_factories else "0"
            enable_joystick = os.getenv("CASTLE_JOYSTICK_ENABLED", default_enabled).strip().lower() in {
                "1",
                "true",
                "yes",
            }
        self.joystick = joystick
        if self.joystick is None and enable_joystick:
            self.joystick = FreenoveJoystick(button_factory=button_factory)
        self._leds = {
            "red": led_factory(self.pins.led_red),
            "green": led_factory(self.pins.led_green),
            "blue": led_factory(self.pins.led_blue),
        }
        self._buzzer = buzzer_factory(self.pins.buzzer)
        self._feedback_generation = 0
        self._feedback_lock = threading.Lock()
        self._last_feedback = "neutral"

    @property
    def audio_buzzer(self):
        return self._buzzer

    def poll_actions(self) -> set[Action]:
        pressed = {action for action, button in self._buttons.items() if button.is_pressed}
        actions = (pressed & self._continuous_actions) | (pressed - self._previously_pressed)
        if self.debug and pressed != self._previously_pressed:
            names = ", ".join(sorted(action.name for action in pressed)) or "nenhum"
            print(f"[GPIO] pressionados: {names}", flush=True)
        self._previously_pressed = pressed
        if self.joystick is not None:
            actions.update(self.joystick.poll_actions())
        return actions

    def pin_summary(self) -> str:
        return "\n".join(
            f"{action.name:>12}: GPIO {button.pin.number}"
            for action, button in self._buttons.items()
        )

    def update_outputs(self, state: OutputState) -> None:
        colors = {
            "correct": (False, True, False),
            "error": (True, False, False),
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
        for device in [*self._button_devices.values(), *self._leds.values(), self._buzzer]:
            device.close()
        if self.joystick is not None:
            self.joystick.close()
