# serial_comm.py

import time
from typing import Optional
import serial

from config import PORT, BAUD, BYTESIZE, PARITY, STOPBITS, TIMEOUT
from models import Step, Program


def open_port() -> serial.Serial:
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        bytesize=BYTESIZE,
        parity=PARITY,
        stopbits=STOPBITS,
        timeout=TIMEOUT,
    )
    print(f"Port opened: {ser.is_open} on {PORT}")
    return ser


def send_command(ser: serial.Serial, cmd_str: str) -> bytes:
    if not ser.is_open:
        raise RuntimeError("Serial port not open")

    data = cmd_str.encode("utf-8")
    written = ser.write(data)
    print("Sent:", cmd_str, "| bytes:", written)

    time.sleep(0.5)  # controller processing time; can tune later
    reply = ser.read(100)
    print("Reply:", reply)
    return reply


def build_move(step: Step) -> Optional[str]:
    """
    Build a G00 / G01 XYZ move frame, or None if no XYZ is set.
    Format from the vendor examples:
    0x550xAA G01 X.. Y.. Z.. F.. 0xAA0x55
    """
    if step.x is None and step.y is None and step.z is None:
        return None

    # choose command
    cmd = step.cmd if step.cmd in ("G00", "G01") else "G01"

    # start building G-code part
    parts = [cmd]
    if step.x is not None:
        parts.append(f"X{step.x}")
    if step.y is not None:
        parts.append(f"Y{step.y}")
    if step.z is not None:
        parts.append(f"Z{step.z}")

    parts.append(f"F{step.f}")

    gcode = " ".join(parts)
    frame = f"0x550xAA {gcode} 0xAA0x55"
    print("FRAME:", frame)

    return frame


def build_do0(step: Step) -> Optional[str]:
    """
    Build a G06 command for DO-0 (4th axis) if step.do0 is set.
    Vendor says 4th axis steering gear uses parameter A, e.g. A90.
    """
    if step.do0 is None:
        return None

    angle = step.do0          # degrees, e.g. 0–180
    gcode = f"G06 D7 S1 A{angle}"
    frame = f"0x550xAA {gcode} 0xAA0x55"
    return frame



def run_program(prog: Program) -> None:
    """
    Run all steps in a Program once, blocking.
    GUI can wrap this in a thread later.
    """
    ser = open_port()
    try:
        for i, step in enumerate(prog.steps, start=1):
            print(f"--- Step {i} ---")

            # DO0 first (optional)
            do_cmd = build_do0(step)
            if do_cmd:
                send_command(ser, do_cmd)

            # XYZ move
            move_cmd = build_move(step)
            if move_cmd:
                send_command(ser, move_cmd)

            # delay before next step
            time.sleep(step.delay)
    finally:
        ser.close()
        print("Serial port closed.")
