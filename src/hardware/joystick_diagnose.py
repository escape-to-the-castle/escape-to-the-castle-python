from __future__ import annotations

import time

from .joystick import FreenoveJoystick


def main() -> int:
    joystick = FreenoveJoystick()
    config = joystick.config
    print("Diagnóstico do joystick (Ctrl+C encerra)")
    print(
        f"I2C={config.address:#04x} X=canal {config.x_channel} "
        f"Y=canal {config.y_channel} Z=GPIO {config.button_pin}"
    )
    try:
        while True:
            x = joystick.adc.analogRead(config.x_channel)
            y = joystick.adc.analogRead(config.y_channel)
            z = int(joystick.button.is_pressed)
            print(f"X={x:3d}  Y={y:3d}  Z={z}", end="\r", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        joystick.close()


if __name__ == "__main__":
    raise SystemExit(main())
