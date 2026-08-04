from __future__ import annotations

import csv
import time
from pathlib import Path

import psutil


class PerformanceMonitor:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.samples: list[tuple[float, float, float, float]] = []

    def sample(self, fps: float) -> None:
        self.samples.append(
            (
                time.time(),
                fps,
                self.process.cpu_percent(interval=None),
                self.process.memory_info().rss / (1024 * 1024),
            )
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "fps", "cpu_percent", "memory_mb"])
            writer.writerows(self.samples)
