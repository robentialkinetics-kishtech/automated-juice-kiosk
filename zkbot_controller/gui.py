# gui.py

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from models import Step, Program
from serial_comm import run_program
from config import PROGRAMS_DIR


class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("ZKBot Controller")
        self.pack(fill="both", expand=True)

        self.program = Program("unnamed")
        self.current_path = None
        self._build_widgets()

    # ---------- UI building ----------

    def _build_widgets(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)

        # --- steps table ---
        columns = ("cmd", "x", "y", "z", "f", "delay", "do0")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        headings = {
            "cmd": "Cmd",
            "x": "X",
            "y": "Y",
            "z": "Z",
            "f": "F",
            "delay": "Delay",
            "do0": "DO0",
        }
        for col, text in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=70, anchor="center")

        self.tree.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_step)

        # --- step editor ---
        editor = ttk.LabelFrame(self, text="Step editor")
        editor.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # cmd
        ttk.Label(editor, text="Cmd (G00/G01):").grid(row=0, column=0, sticky="e")
        self.cmd_var = tk.StringVar(value="G01")
        self.cmd_entry = ttk.Combobox(
            editor, textvariable=self.cmd_var, values=("G00", "G01"), width=6
        )
        self.cmd_entry.grid(row=0, column=1, sticky="w", pady=2)

        # X/Y/Z/F/Delay/DO0
        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.z_var = tk.StringVar()
        self.f_var = tk.StringVar()
        self.delay_var = tk.StringVar()
        self.do0_var = tk.StringVar()

        row = 1
        for label, var in (
            ("X:", self.x_var),
            ("Y:", self.y_var),
            ("Z:", self.z_var),
            ("F:", self.f_var),
            ("Delay (s):", self.delay_var),
            ("DO0 angle:", self.do0_var),
        ):
            ttk.Label(editor, text=label).grid(row=row, column=0, sticky="e")
            ttk.Entry(editor, textvariable=var, width=10).grid(
                row=row, column=1, sticky="w", pady=2
            )
            row += 1

        # step buttons
        btn_frame = ttk.Frame(editor)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=5, sticky="ew")
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)

        ttk.Button(btn_frame, text="Add", command=self.on_add_step).grid(
            row=0, column=0, padx=2
        )
        ttk.Button(btn_frame, text="Insert", command=self.on_insert_step).grid(
            row=0, column=1, padx=2
        )
        ttk.Button(btn_frame, text="Update", command=self.on_update_step).grid(
            row=0, column=2, padx=2
        )
        ttk.Button(btn_frame, text="Delete", command=self.on_delete_step).grid(
            row=0, column=3, padx=2
        )

        # --- program buttons ---
        prog_frame = ttk.LabelFrame(self, text="Program")
        prog_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        for i in range(3):
            prog_frame.columnconfigure(i, weight=1)

        ttk.Button(prog_frame, text="New", command=self.on_new_program).grid(
            row=0, column=0, padx=2, pady=2
        )
        ttk.Button(prog_frame, text="Open", command=self.on_open_program).grid(
            row=0, column=1, padx=2, pady=2
        )
        ttk.Button(prog_frame, text="Save", command=self.on_save_program).grid(
            row=0, column=2, padx=2, pady=2
        )

        # --- run buttons + status ---
        run_frame = ttk.LabelFrame(self, text="Run")
        run_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        run_frame.columnconfigure(0, weight=1)

        ttk.Button(run_frame, text="Run program", command=self.on_run_program).grid(
            row=0, column=0, padx=2, pady=2, sticky="ew"
        )

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(run_frame, textvariable=self.status_var).grid(
            row=1, column=0, sticky="w", padx=2, pady=2
        )

    # ---------- helpers ----------

    def _read_step_from_fields(self) -> Optional[Step]:
        try:
            cmd = self.cmd_var.get().strip() or "G01"
            if cmd not in ("G00", "G01"):
                raise ValueError("Cmd must be G00 or G01")

            def parse_float(s):
                s = s.strip()
                return float(s) if s else None

            x = parse_float(self.x_var.get())
            y = parse_float(self.y_var.get())
            z = parse_float(self.z_var.get())
            f = float(self.f_var.get()) if self.f_var.get().strip() else None
            delay = (
                float(self.delay_var.get()) if self.delay_var.get().strip() else None
            )
            do0 = parse_float(self.do0_var.get())

            step = Step(
                cmd=cmd,
                x=x,
                y=y,
                z=z,
                f=f if f is not None else Step().f,
                delay=delay if delay is not None else Step().delay,
                do0=do0,
            )
            return step
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return None

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, s in enumerate(self.program.steps):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(s.cmd, s.x, s.y, s.z, s.f, s.delay, s.do0),
            )

    # ---------- callbacks ----------

    def on_add_step(self):
        step = self._read_step_from_fields()
        if not step:
            return
        self.program.steps.append(step)
        self._refresh_tree()

    def on_insert_step(self):
        step = self._read_step_from_fields()
        if not step:
            return
        sel = self.tree.selection()
        index = int(sel[0]) if sel else len(self.program.steps)
        self.program.steps.insert(index, step)
        self._refresh_tree()

    def on_update_step(self):
        step = self._read_step_from_fields()
        if not step:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Update step", "Select a step first.")
            return
        index = int(sel[0])
        self.program.steps[index] = step
        self._refresh_tree()

    def on_delete_step(self):
        sel = self.tree.selection()
        if not sel:
            return
        index = int(sel[0])
        del self.program.steps[index]
        self._refresh_tree()

    def on_select_step(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        index = int(sel[0])
        s = self.program.steps[index]
        self.cmd_var.set(s.cmd)
        self.x_var.set("" if s.x is None else str(s.x))
        self.y_var.set("" if s.y is None else str(s.y))
        self.z_var.set("" if s.z is None else str(s.z))
        self.f_var.set(str(s.f))
        self.delay_var.set(str(s.delay))
        self.do0_var.set("" if s.do0 is None else str(s.do0))

    def on_new_program(self):
        self.program = Program("unnamed")
        self.current_path = None
        self._refresh_tree()
        self.status_var.set("New program.")

    def on_open_program(self):
        os.makedirs(PROGRAMS_DIR, exist_ok=True)
        path = filedialog.askopenfilename(
            initialdir=PROGRAMS_DIR,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.program = Program.load(path)
            self.current_path = path
            self._refresh_tree()
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def on_save_program(self):
        if not self.current_path:
            os.makedirs(PROGRAMS_DIR, exist_ok=True)
            path = filedialog.asksaveasfilename(
                initialdir=PROGRAMS_DIR,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return
            self.current_path = path
        try:
            self.program.save(self.current_path)
            self.status_var.set(f"Saved: {os.path.basename(self.current_path)}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def on_run_program(self):
        if not self.program.steps:
            messagebox.showinfo("Run", "Program is empty.")
            return
        try:
            self.status_var.set("Running program...")
            self.master.update_idletasks()
            run_program(self.program)
            self.status_var.set("Finished program.")
        except Exception as e:
                messagebox.showerror("Run failed", str(e))
                self.status_var.set("Error – see message.")
    
    
    def main(root=None):
        if root is None:
            root = tk.Tk()
        app = MainWindow(root)   # whatever your existing main class is
        root.mainloop()
