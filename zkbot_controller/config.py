# config.py

# ---- serial port settings ----
PORT = "COM3"          # change if Device Manager shows a different COM
BAUD = 9600
BYTESIZE = 8
PARITY = "N"
STOPBITS = 1
TIMEOUT = 1.0          # seconds

# ---- motion defaults ----
DEFAULT_FEED = 20.0    # default F if user leaves it blank
DEFAULT_DELAY = 0.5    # seconds between steps

# optional safety limits (world coordinates, mm)
X_MIN, X_MAX = -200.0, 200.0
Y_MIN, Y_MAX = -200.0, 200.0
Z_MIN, Z_MAX = -50.0, 250.0

# programs folder
PROGRAMS_DIR = "programs"
