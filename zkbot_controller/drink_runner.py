# drink_runner.py

from pathlib import Path

from models import Program
from serial_comm import run_program


BASE_DIR = Path(__file__).parent
PROGRAM_DIR = BASE_DIR / "programs"


def make_drink(juice_key: str) -> None:
    """
    Sequence:
      1) programs/orgin.json
      2) programs/common/pick_cup.json
      3) programs/juices/<juice_key>.json
    """
    # Load each JSON using Program.load defined in models.py
    origin_prog = Program.load(str(PROGRAM_DIR / "orgin.json"))
    common_prog = Program.load(str(PROGRAM_DIR / "common" / "pick_cup.json"))
    juice_prog  = Program.load(str(PROGRAM_DIR / "juices" / f"{juice_key}.json"))

    # Merge steps in order into one Program
    full_prog = Program(name=f"drink_{juice_key}")
    full_prog.steps.extend(origin_prog.steps)
    full_prog.steps.extend(common_prog.steps)
    full_prog.steps.extend(juice_prog.steps)

    # Run with your existing serial_comm.run_program
    run_program(full_prog)
