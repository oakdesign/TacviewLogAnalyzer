from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import (Environment, FileSystemLoader, PackageLoader,
                    select_autoescape)

from .parser import parse_file
from .viewmodel import build_pilot_view_model


def _build_env() -> Environment:
    """Build Jinja2 environment with support for user-provided custom templates.
    
    Priority order:
    1. Custom template in same directory as executable (for standalone .exe)
    2. Custom template in current working directory (for development)
    3. Built-in package template (default)
    """
    
    # Check for custom template alongside executable (for standalone .exe users)
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        exe_dir = Path(sys.executable).parent
        custom_template = exe_dir / "index.html"
        if custom_template.exists():
            loader = FileSystemLoader(str(exe_dir))
            return Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))
    
    # Check for custom template in current working directory (for development/testing)
    cwd_template = Path.cwd() / "index.html"
    if cwd_template.exists():
        loader = FileSystemLoader(str(Path.cwd()))
        return Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))
    
    # Fall back to built-in template
    try:
        # When installed as a package, templates are inside the package
        loader = PackageLoader("tacview_log_analyzer", "webui")
    except Exception:
        # Fallback for editable/source runs
        tpl_dir = Path(__file__).with_name("webui")
        loader = FileSystemLoader(str(tpl_dir))
    return Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))

env = _build_env()

app = FastAPI(title="Tacview Log Analyzer - Web UI")


@app.get("/", response_class=HTMLResponse)
def index(xml: Optional[str] = Query(default=None, description="Path to Tacview XML file")):
    if not xml:
        template = env.get_template("index.html")
        return template.render(error=None, hasData=False)
    p = Path(xml)
    if not p.exists():
        template = env.get_template("index.html")
        return template.render(error=f"File not found: {xml}", hasData=False)
    deb = parse_file(p)
    vm = build_pilot_view_model(deb.events, deb.mission)
    template = env.get_template("index.html")
    return template.render(error=None, hasData=True, vm=vm, xml=str(p))
