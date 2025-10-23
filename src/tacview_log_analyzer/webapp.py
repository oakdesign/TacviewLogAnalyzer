from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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


@app.get("/api/browse")
def browse_files(path: Optional[str] = Query(default=None, description="Directory path to browse")):
    """API endpoint to browse files and directories for file picker functionality."""
    try:
        if path is None:
            # Start from executable directory if frozen, otherwise current directory
            if getattr(sys, 'frozen', False):
                # When frozen (PyInstaller), use the directory containing the executable
                browse_path = Path(sys.executable).parent
            else:
                browse_path = Path.cwd()
        else:
            browse_path = Path(path)
            
        # Security: ensure we don't browse outside reasonable bounds
        try:
            browse_path = browse_path.resolve()
        except (OSError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")
            
        if not browse_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {browse_path}")
            
        if not browse_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {browse_path}")
        
        files = []
        directories = []
        
        try:
            # List directory contents
            for item in browse_path.iterdir():
                try:
                    if item.is_dir():
                        directories.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "directory"
                        })
                    elif item.is_file() and item.suffix.lower() == '.xml':
                        # Only show XML files
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "file",
                            "size": item.stat().st_size if item.exists() else 0
                        })
                except (PermissionError, OSError) as e:
                    # Skip files/dirs we can't access but log the issue
                    print(f"Warning: Cannot access {item}: {e}")
                    continue
                    
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
            
        # Sort: directories first, then files, both alphabetically
        directories.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        
        # Add parent directory option (if not at root)
        parent_path = None
        if browse_path.parent != browse_path:  # Not at filesystem root
            parent_path = str(browse_path.parent)
            
        return JSONResponse({
            "success": True,
            "current_path": str(browse_path),
            "parent_path": parent_path,
            "directories": directories,
            "files": files,
            "total_items": len(directories) + len(files)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Unexpected error in browse_files: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/recent-files")
def get_recent_files():
    """Get recently accessed XML files from common locations."""
    recent_files = []
    
    # Check executable directory for XML files (most common for standalone users)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        try:
            for xml_file in exe_dir.glob("*.xml"):
                if xml_file.is_file():
                    recent_files.append({
                        "name": xml_file.name,
                        "path": str(xml_file),
                        "location": "executable directory"
                    })
        except (PermissionError, OSError):
            pass
    
    # Check current working directory
    try:
        for xml_file in Path.cwd().glob("*.xml"):
            if xml_file.is_file():
                recent_files.append({
                    "name": xml_file.name,
                    "path": str(xml_file),
                    "location": "current directory"
                })
    except (PermissionError, OSError):
        pass
    
    # Remove duplicates and limit results
    seen_paths = set()
    unique_files = []
    for file in recent_files:
        if file["path"] not in seen_paths:
            seen_paths.add(file["path"])
            unique_files.append(file)
            
    return JSONResponse({
        "files": unique_files[:10]  # Limit to 10 most recent
    })
