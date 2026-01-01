# Automated Juice Kiosk (ZKBot Controller)

Simple controller UI and program runner for the ZKBot automated juice kiosk.

## Quick start

1. Create and activate a Python virtual environment (recommended):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure serial port in `zkbot_controller/config.py` (set `PORT` to your COM port).

4. Run the GUI:

```powershell
python -m zkbot_controller.main
```

## Project layout

- `zkbot_controller/` — application code
- `programs/` — JSON programs run by the robot
- `workspace_tests/` — generated test CSVs

## Notes

- The repository `.gitignore` excludes virtual environments and caches.
- If you push large files by accident (e.g., contents of `venv/`), let me know and I can help remove them from history.
