from __future__ import annotations

import os

from .interface import HardwareInterface, OutputState
from .keyboard import KeyboardHardware
from .freenove import FreenoveHardware



class CompositeHardware(HardwareInterface):
    def __init__(self, *devices: HardwareInterface) -> None:
        self.devices = devices

    def poll_actions(self):
        actions = set()
        for device in self.devices:
            actions.update(device.poll_actions())
        return actions

    def update_outputs(self, state: OutputState) -> None:
        for device in self.devices:
            device.update_outputs(state)

    def close(self) -> None:
        for device in self.devices:
            device.close()

    @property
    def audio_buzzer(self):
        for device in self.devices:
            buzzer = getattr(device, "audio_buzzer", None)
            if buzzer is not None:
                return buzzer
        return None


def create_hardware(mode: str | None = None) -> HardwareInterface:
    """Seleciona teclado, placa Freenove ou ambos."""
    '''selected_mode = (mode or os.getenv("CASTLE_HARDWARE", "keyboard")).strip().lower()
    if selected_mode == "keyboard":
        return KeyboardHardware()
    if selected_mode == "freenove":
        from .freenove import FreenoveHardware

        return FreenoveHardware()
    if selected_mode == "hybrid":
        from .freenove import FreenoveHardware'''

    return FreenoveHardware()
    
    '''raise ValueError(f"Modo de hardware desconhecido: {selected_mode}")'''
