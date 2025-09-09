"""Deprecated webhook adapter for platform repository_dispatch bridging.

This module is retained as a no‑op placeholder after migrating to direct
AppTrust → GitHub repository_dispatch (no in‑cluster adapter required).
"""

from typing import Dict

from fastapi import FastAPI


app = FastAPI(title="BookVerse Platform Webhook Adapter (deprecated)")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


