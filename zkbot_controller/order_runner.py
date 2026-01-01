from pathlib import Path
from models import Program
from serial_comm import run_program

BASE_DIR = Path(__file__).parent
PROGRAM_DIR = BASE_DIR / "programs"


def run_order(juice_key: str):
    """
    Order flow:
      origin.json
      common/pick_cup.json    (pick cup + ice)
      juices/<juice_key>.json (juice + delivery)
    """
    origin_prog = Program.load(str(PROGRAM_DIR / "orgin.json"))
    common_prog = Program.load(str(PROGRAM_DIR / "common" / "pick_cup.json"))
    juice_prog  = Program.load(str(PROGRAM_DIR / "juices" / f"{juice_key}.json"))

    full_prog = Program(name=f"order_{juice_key}")
    full_prog.steps.extend(origin_prog.steps)
    full_prog.steps.extend(common_prog.steps)
    full_prog.steps.extend(juice_prog.steps)

    run_program(full_prog)
