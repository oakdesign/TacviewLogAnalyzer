# Tacview Log Analyzer (skeleton)

A Python project to parse Tacview XML logs and generate statistics. This is the base scaffolding with CLI, packaging, tests, and Windows build hooks. Business logic will be added later.

## Features (now)
- src/ layout Python package: `tacview_log_analyzer`
- CLI entry: `tacview-analyze`
- Tests via pytest
- VS Code tasks and debug configs
- PyInstaller task to build a standalone `.exe`

## Quick start (Windows PowerShell)

```powershell
# 1) Create & activate virtualenv
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 2) Install dev dependencies and project in editable mode
pip install -U pip
pip install -e .[dev]

# 3) Run tests
pytest -q

# 4) Use CLI (skeleton)
python -m tacview_log_analyzer --help
python -m tacview_log_analyzer 2025-09-06_18-48-30.xml

# 5) Build one-file exe (outputs to dist/)
pyinstaller --noconfirm --onefile --name TacviewLogAnalyzer --console --paths src src/tacview_log_analyzer/cli.py
```

## Project layout
- `src/tacview_log_analyzer/cli.py` – CLI entry point (no business logic yet)
- `src/tacview_log_analyzer/__init__.py` – package metadata
- `tests/` – minimal smoke tests
- `.vscode/` – tasks and debug configs
- `pyproject.toml` – packaging config

## Next steps
- Define XML schema/data points and write parsing services
- Add domain models and statistics calculators
- Wire CLI options to run parsing and output reports
- Optional: add GUI (e.g., `PySide6`/`Tkinter`) atop service layer
