from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hardware.passive_audio import wav_to_rom_steps


ROOT = Path(__file__).resolve().parents[1]
SOUND_DIR = ROOT / "brackeys_platformer_assets" / "sounds"
OUTPUT_PATH = ROOT / "data" / "buzzer_roms.json"
SOUND_FILES = {
    "coin": "coin.wav",
    "jump": "jump.wav",
    "hurt": "hurt.wav",
    "power_up": "power_up.wav",
}


def main() -> int:
    manifest = {
        "format": "escape-to-the-castle-buzzer-rom-v1",
        "duration_ms": 20,
        "sounds": {
            name: [
                {"tone": step.tone, "duration_ticks": step.duration_ticks}
                for step in wav_to_rom_steps(SOUND_DIR / filename)
            ]
            for name, filename in SOUND_FILES.items()
        },
    }
    OUTPUT_PATH.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
