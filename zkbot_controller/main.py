# main.py

import tkinter as tk
from gui import MainWindow

if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(master=root)
    root.mainloop()
