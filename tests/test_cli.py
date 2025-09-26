from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess:
    # Run the package as a module via the CLI script entry
    cmd = [sys.executable, "-m", "tacview_log_analyzer.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_no_args_shows_help():
    proc = run_cli()
    assert proc.returncode == 0
    assert "Tacview Log Analyzer" in proc.stdout


def test_version_flag():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert proc.stdout.strip().startswith("tacview-analyze ")


def test_with_xml_path_prints_placeholder(tmp_path: Path):
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text("<root />", encoding="utf-8")
    proc = run_cli(str(xml_file))
    assert proc.returncode == 0
    assert f"Would analyze: {xml_file}" in proc.stdout
