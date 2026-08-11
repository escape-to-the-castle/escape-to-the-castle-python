from __future__ import annotations

import os

from .interface import HardwareInterface
from .keyboard import KeyboardHardware
from .freenove import FreenoveHardware


def create_hardware(mode: str | None = None) -> HardwareInterface:
    """Cria o controle solicitado sem importar GPIO no modo teclado."""
    '''selected_mode = (mode or os.getenv("CASTLE_HARDWARE", "keyboard")).strip().lower()'''
    '''if selected_mode == "keyboard":
        return KeyboardHardware()
    if selected_mode == "freenove":
        '''

    return FreenoveHardware()
    '''raise ValueError(f"Modo de hardware desconhecido: {selected_mode}")'''
