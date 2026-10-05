"""User-configurable timing. Jitter is added only before currency application."""
from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class TimingSettings:
    speed: float = 3.0
    random_enabled: bool = True
    random_min_ms: float = 50.0
    random_max_ms: float = 150.0

    def __post_init__(self):
        if not math.isfinite(self.speed) or not 0.5 <= self.speed <= 5.0:
            raise ValueError('速度倍率须为0.5至5，越大越快')
        bounds = self.random_min_ms, self.random_max_ms
        if any(not math.isfinite(v) or v < 0 or v > 10000 for v in bounds):
            raise ValueError('随机延迟须为0至10000毫秒的有限数')
        if self.random_max_ms < self.random_min_ms:
            raise ValueError('随机延迟上限不能小于下限')

    def seconds(self, phase: str) -> float:
        # Base delays are the v0.1.3 timings. Floors leave time for the client
        # to receive input; speed never changes clipboard freshness checks.
        base, floor = {
            'move': (0.15, 0.015), 'select': (0.20, 0.05),
            'shift': (0.05, 0.02), 'click': (0.06, 0.02),
            'hover': (0.40, 0.08), 'key': (0.04, 0.015),
            'settle': (0.65, 0.10),
        }[phase]
        return max(floor, base / self.speed)

    def random_seconds(self) -> float:
        if not self.random_enabled:
            return 0.0
        return random.uniform(self.random_min_ms, self.random_max_ms) / 1000.0
