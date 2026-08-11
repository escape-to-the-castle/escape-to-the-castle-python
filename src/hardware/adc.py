from __future__ import annotations


class ADS7830:
    """Leitor mínimo do ADS7830 via SMBus, compatível com a API Freenove."""

    def __init__(self, address: int = 0x48, bus_number: int = 1) -> None:
        try:
            import smbus
        except ImportError as error:
            raise RuntimeError(
                "SMBus não está instalado. Execute: sudo apt install python3-smbus"
            ) from error
        self.address = address
        self.bus = smbus.SMBus(bus_number)
        try:
            self.analogRead(0)
        except OSError as error:
            self.close()
            raise RuntimeError(
                f"ADS7830 não encontrado em {address:#04x}. Execute: i2cdetect -y 1"
            ) from error

    def analogRead(self, channel: int) -> int:
        if not 0 <= channel <= 7:
            raise ValueError("O canal do ADS7830 deve estar entre 0 e 7")
        command = 0x84 | ((((channel << 2) | (channel >> 1)) & 0x07) << 4)
        return int(self.bus.read_byte_data(self.address, command))

    def close(self) -> None:
        self.bus.close()
