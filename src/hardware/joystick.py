from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from .interface import Action


@dataclass(frozen=True)
class JoystickConfig:
    address: int = 0x48
    x_channel: int = 5
    y_channel: int = 6
    button_pin: int = 7
    low_threshold: int = 80
    high_threshold: int = 175
    # No módulo Freenove, os valores do eixo X crescem para a esquerda.
    invert_x: bool = True
    invert_y: bool = False

    @classmethod
    def from_env(cls) -> "JoystickConfig":
        defaults = cls()

        def flag(name: str, default: bool) -> bool:
            value = os.getenv(name, "1" if default else "0").strip().lower()
            return value in {"1", "true", "yes"}

        return cls(
            address=int(os.getenv("CASTLE_JOYSTICK_ADDRESS", hex(defaults.address)), 0),
            x_channel=int(os.getenv("CASTLE_JOYSTICK_X_CHANNEL", defaults.x_channel)),
            y_channel=int(os.getenv("CASTLE_JOYSTICK_Y_CHANNEL", defaults.y_channel)),
            button_pin=int(os.getenv("CASTLE_JOYSTICK_BUTTON_PIN", defaults.button_pin)),
            low_threshold=int(os.getenv("CASTLE_JOYSTICK_LOW", defaults.low_threshold)),
            high_threshold=int(os.getenv("CASTLE_JOYSTICK_HIGH", defaults.high_threshold)),
            invert_x=flag("CASTLE_JOYSTICK_INVERT_X", defaults.invert_x),
            invert_y=flag("CASTLE_JOYSTICK_INVERT_Y", defaults.invert_y),
        )


class FreenoveJoystick:
    """Converte o joystick ADS7830 do kit em ações do jogo."""

    def __init__(
        self,
        config: JoystickConfig | None = None,
        adc: Any | None = None,
        button_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config or JoystickConfig.from_env()
        if adc is None:
            adc = self._create_manual_adc()
        if button_factory is None:
            try:
                from gpiozero import Button
            except ImportError as error:
                raise RuntimeError("GPIO Zero é necessário para o botão do joystick.") from error
            button_factory = Button
        self.adc = adc
        self.button = button_factory(self.config.button_pin, pull_up=True, bounce_time=0.05)
        self._button_was_pressed = False
        self._roll_was_active = False

    def _create_manual_adc(self):
        try:
            from ADCDevice import ADCDevice, ADS7830
        except ImportError:
            from .adc import ADS7830

            return ADS7830(self.config.address)

        detector = ADCDevice(self.config.address)
        if not detector.detectI2C(self.config.address):
            detector.close()
            raise RuntimeError(
                f"ADC do joystick não encontrado no endereço {self.config.address:#04x}. "
                "Execute: i2cdetect -y 1"
            )
        detector.close()
        return ADS7830(self.config.address)

    def poll_actions(self) -> set[Action]:
        value_x = int(self.adc.analogRead(self.config.x_channel))
        value_y = int(self.adc.analogRead(self.config.y_channel))
        if self.config.invert_x:
            value_x = 255 - value_x
        if self.config.invert_y:
            value_y = 255 - value_y

        actions: set[Action] = set()
        if value_x < self.config.low_threshold:
            actions.add(Action.MOVE_LEFT)
        elif value_x > self.config.high_threshold:
            actions.add(Action.MOVE_RIGHT)

        # Empurrar o eixo para baixo aciona a rolagem uma vez por movimento.
        roll_active = value_y > self.config.high_threshold
        if roll_active and not self._roll_was_active:
            actions.add(Action.ROLL)
        self._roll_was_active = roll_active

        pressed = bool(self.button.is_pressed)
        if pressed and not self._button_was_pressed:
            actions.add(Action.JUMP)
            actions.add(Action.START)
        self._button_was_pressed = pressed
        return actions

    def close(self) -> None:
        self.adc.close()
        self.button.close()
