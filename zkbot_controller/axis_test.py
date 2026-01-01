# workspace_zone_tester.py
#
# Flexible workspace tester with:
# - Predefined zones (delivery, juice, ice, cup pick)
# - Manual user confirmation for each move
# - Detailed logging with timestamps
# - Complete dataset export to CSV

import csv
import time
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import List, Tuple, Optional
from itertools import product

from models import Step, Program
from serial_comm import run_program


# ========== ZONE DEFINITIONS ==========
# Define your workspace zones with their XYZ ranges

ZONES = {
    "delivery_area": {
        "x": {"min": -20.0, "max": 35.0, "step": 10.0},
        "y": {"min": -50.0, "max": -25.0, "step": 15.0},
        "z": {"min": -90.0, "max": -60.0, "step": 25.0},
    },
    "juice_dispense": {
        "x": {"min": -85.0, "max": -55.0, "step": 15.0},
        "y": {"min": -80.0, "max": -50.0, "step": 10.0},
        "z": {"min": -110.0, "max": -100.0, "step": 10.0},
    },
    "ice_dispense": {
        "x": {"min": -103.0, "max": -103.0, "step": 15.0},
        "y": {"min": -60.0, "max": -60.0, "step": 10.0},
        "z": {"min": -110.0, "max": -75.0, "step": 10.0},
    },
    "cup_pick": {
        "x": {"min": -155.0, "max": -125.0, "step": 10.0},
        "y": {"min": -90.0, "max": -50.0, "step": 10.0},
        "z": {"min": -110.0, "max": -65.0, "step": 10.0},
    },
}


# ========== CONFIGURATION ==========

# Which zone to test (change this or test all)
ACTIVE_ZONE = "all"  # or "all" to test all zones

# Confirmation mode: "manual" (you confirm each) or "auto" (relies on serial reply)
CONFIRMATION_MODE = "auto"

# Delay after each move command (seconds)
MOVE_DELAY = 1.0

# Output directory
OUTPUT_DIR = Path("workspace_tests")
OUTPUT_DIR.mkdir(exist_ok=True)


# ========== HELPERS ==========

def generate_range(range_cfg: dict) -> List[float]:
    """Generate list of positions from range config."""
    values = []
    val = range_cfg["min"]
    step = range_cfg["step"]
    
    if step == 0:
        raise ValueError("step cannot be zero")
    
    if range_cfg["min"] <= range_cfg["max"]:
        while val <= range_cfg["max"]:
            values.append(round(val, 3))
            val += abs(step)
    else:
        while val >= range_cfg["max"]:
            values.append(round(val, 3))
            val -= abs(step)
    
    return values


def generate_zone_points(zone_name: str, zone_cfg: dict) -> List[Tuple[float, float, float]]:
    """Generate all XYZ combinations for a zone."""
    xs = generate_range(zone_cfg["x"])
    ys = generate_range(zone_cfg["y"])
    zs = generate_range(zone_cfg["z"])
    
    points = list(product(xs, ys, zs))
    print(f"\nZone '{zone_name}':")
    print(f"  X: {len(xs)} points ({zone_cfg['x']['min']} to {zone_cfg['x']['max']})")
    print(f"  Y: {len(ys)} points ({zone_cfg['y']['min']} to {zone_cfg['y']['max']})")
    print(f"  Z: {len(zs)} points ({zone_cfg['z']['min']} to {zone_cfg['z']['max']})")
    print(f"  Total combinations: {len(points)}")
    
    return points


def test_move(x: float, y: float, z: float) -> Tuple[str, str, float]:
    """
    Execute move and return (status, note, duration).
    status: "OK" or "ERROR"
    """
    start_time = time.time()
    try:
        prog = Program(name="zone_test")
        prog.steps.append(Step(cmd="G00", x=x, y=y, z=z, delay=MOVE_DELAY))
        run_program(prog)
        duration = time.time() - start_time
        return ("OK", "Move completed", duration)
    except Exception as e:
        duration = time.time() - start_time
        return ("ERROR", str(e), duration)


class ManualConfirmDialog:
    """GUI dialog for manual confirmation."""
    
    def __init__(self):
        self.result = None
        self.root = None
    
    def ask(self, point_num: int, total: int, x: float, y: float, z: float) -> str:
        """Show dialog and return 'OK' or 'ERROR'."""
        self.result = None
        
        self.root = tk.Tk()
        self.root.title("Confirm Move")
        self.root.geometry("400x200")
        
        # Center window
        self.root.eval('tk::PlaceWindow . center')
        
        # Info
        tk.Label(
            self.root,
            text=f"Point {point_num}/{total}",
            font=("Arial", 14, "bold")
        ).pack(pady=10)
        
        tk.Label(
            self.root,
            text=f"X={x:.2f}, Y={y:.2f}, Z={z:.2f}",
            font=("Arial", 12)
        ).pack(pady=5)
        
        tk.Label(
            self.root,
            text="Did the arm move successfully?",
            font=("Arial", 11)
        ).pack(pady=15)
        
        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="✓ OK (Arm Moved)",
            command=lambda: self._set_result("OK"),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame,
            text="✗ ERROR (Alarm/No Move)",
            command=lambda: self._set_result("ERROR"),
            bg="#f44336",
            fg="white",
            font=("Arial", 11, "bold"),
            width=18,
            height=2
        ).pack(side="left", padx=10)
        
        self.root.protocol("WM_DELETE_WINDOW", lambda: self._set_result("ERROR"))
        self.root.mainloop()
        
        return self.result or "ERROR"
    
    def _set_result(self, value: str):
        self.result = value
        self.root.destroy()


def run_zone_test(zone_name: str, zone_cfg: dict):
    """Test all points in a zone and save results."""
    
    points = generate_zone_points(zone_name, zone_cfg)
    
    if not points:
        print("No points generated. Check zone config.")
        return
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"test_{zone_name}_{timestamp}.csv"
    
    print(f"\n{'='*70}")
    print(f"Starting test for zone: {zone_name}")
    print(f"Total points: {len(points)}")
    print(f"Confirmation mode: {CONFIRMATION_MODE}")
    print(f"{'='*70}\n")
    
    dialog = ManualConfirmDialog() if CONFIRMATION_MODE == "manual" else None
    
    results = []
    ok_count = 0
    error_count = 0
    
    for i, (x, y, z) in enumerate(points, start=1):
        test_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"[{i}/{len(points)}] Testing X={x:7.2f}, Y={y:7.2f}, Z={z:7.2f} ... ", end="", flush=True)
        
        # Execute move
        auto_status, auto_note, duration = test_move(x, y, z)
        
        # Get final status
        if CONFIRMATION_MODE == "manual":
            print(f"({auto_status}) ", end="", flush=True)
            user_status = dialog.ask(i, len(points), x, y, z)
            final_status = user_status
            final_note = f"Auto: {auto_status}, User: {user_status} | {auto_note}"
        else:
            final_status = auto_status
            final_note = auto_note
        
        # Display result
        if final_status == "OK":
            ok_count += 1
            print("✓ OK")
        else:
            error_count += 1
            print(f"✗ ERROR")
        
        results.append({
            "test_num": i,
            "timestamp": test_timestamp,
            "zone": zone_name,
            "x": x,
            "y": y,
            "z": z,
            "status": final_status,
            "duration_sec": round(duration, 3),
            "note": final_note
        })
        
        time.sleep(0.3)
    
    # Save results
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "test_num", "timestamp", "zone", "x", "y", "z", 
            "status", "duration_sec", "note"
        ])
        writer.writeheader()
        writer.writerows(results)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Zone '{zone_name}' test complete!")
    print(f"Total points: {len(points)}")
    print(f"OK: {ok_count} ({100*ok_count/len(points):.1f}%)")
    print(f"ERROR: {error_count} ({100*error_count/len(points):.1f}%)")
    print(f"Results saved to: {csv_path}")
    print(f"{'='*70}\n")


# ========== MAIN ==========

def main():
    if ACTIVE_ZONE == "all":
        for zone_name, zone_cfg in ZONES.items():
            run_zone_test(zone_name, zone_cfg)
            input("\nPress Enter to continue to next zone...")
    elif ACTIVE_ZONE in ZONES:
        run_zone_test(ACTIVE_ZONE, ZONES[ACTIVE_ZONE])
    else:
        print(f"ERROR: Unknown zone '{ACTIVE_ZONE}'")
        print(f"Available zones: {', '.join(ZONES.keys())}")


if __name__ == "__main__":
    main()
