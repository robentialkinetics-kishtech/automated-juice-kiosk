# Contributing

Thanks for your interest in contributing! A few quick guidelines:

- Create an issue first for non-trivial changes so we can discuss design.
- Fork the repo and create feature branches from `master` (or `main`).
- Keep changes small and focused; add tests where possible.

Local setup

1. Create and activate a virtualenv:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install runtime deps:

```powershell
pip install -r requirements.txt
```

3. Run syntax check locally:

```powershell
python -m py_compile zkbot_controller\*.py
```

Pull requests

- Target the `master` branch.
- Describe the change and any setup required to test it.
