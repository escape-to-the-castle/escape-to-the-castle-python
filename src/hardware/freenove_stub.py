from __future__ import annotations

from .interface import HardwareInterface, OutputState


class FreenoveHardware(HardwareInterface):
    """Ponto de extensão para a integração real com o kit FNK0054.

    Implemente leitura de GPIO/ADC em poll_actions e controle de LEDs,
    buzzer, servo e display em update_outputs. O protótipo utiliza a
    implementação KeyboardHardware para funcionar sem o kit conectado.
    """

    def poll_actions(self):
        raise NotImplementedError("Integração física ainda não implementada.")

    def update_outputs(self, state: OutputState) -> None:
        _ = state
