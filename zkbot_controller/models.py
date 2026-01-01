# models.py

from dataclasses import dataclass, asdict
from typing import List, Optional
import json
import os
from config import PROGRAMS_DIR, DEFAULT_FEED, DEFAULT_DELAY


@dataclass
class Step:
    cmd: str = "G01"                 # "G00" (point) or "G01" (linear)
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    f: float = DEFAULT_FEED
    delay: float = DEFAULT_DELAY
    do0: Optional[float] = None      # end-effector angle (for G06), degrees

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Step":
        return Step(
            cmd=data.get("cmd", "G01"),
            x=data.get("x"),
            y=data.get("y"),
            z=data.get("z"),
            f=data.get("f", DEFAULT_FEED),
            delay=data.get("delay", DEFAULT_DELAY),
            do0=data.get("do0"),
        )


class Program:
    def __init__(self, name: str = "unnamed"):
        self.name = name
        self.steps: List[Step] = []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }

    @staticmethod
    def from_dict(data: dict) -> "Program":
        prog = Program(name=data.get("name", "unnamed"))
        for s in data.get("steps", []):
            prog.steps.append(Step.from_dict(s))
        return prog

    # ---- file I/O ----

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(path: str) -> "Program":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Program.from_dict(data)
