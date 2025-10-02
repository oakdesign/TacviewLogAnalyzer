from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .webapp import app as _app


app = FastAPI(title="Tacview Log Analyzer - Entrypoint")


@app.get("/")
def root():
    xml = os.environ.get("TLA_XML")
    if xml:
        return RedirectResponse(url=f"/ui?xml={xml}")
    return RedirectResponse(url="/ui")


# Mount the actual UI at /ui
app.mount("/ui", _app)
