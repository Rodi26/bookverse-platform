import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field


class ReleaseCompletedPayload(BaseModel):
    applicationVersion: str = Field(..., description="Platform application version")
    applicationKey: str = Field(..., description="Should be 'bookverse-platform' for this demo")
    stage: Optional[str] = Field(None, description="Release stage (release events imply prod)")


app = FastAPI(title="BookVerse Platform Webhook Adapter")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/info")
def info() -> Dict[str, Any]:
    return {
        "service": "platform-webhook-adapter",
        "version": "0.1.0",
        "repo_dispatch_owner": os.environ.get("GITHUB_OWNER", ""),
        "repo_dispatch_repo": os.environ.get("GITHUB_REPO", ""),
        "repo_dispatch_event": os.environ.get("REPO_DISPATCH_EVENT", "platform_release"),
    }


_seen_events: Dict[str, float] = {}
_SEEN_TTL_SECONDS = 3600.0


def _prune_seen(now: float) -> None:
    stale = [k for k, t in _seen_events.items() if (now - t) > _SEEN_TTL_SECONDS]
    for k in stale:
        _seen_events.pop(k, None)


def _verify_signature(raw_body: bytes, signature_header: Optional[str]) -> None:
    require_sig = os.environ.get("APPTRUST_REQUIRE_SIGNATURE", "false").lower() in ("1", "true", "yes")
    secret = os.environ.get("APPTRUST_WEBHOOK_SECRET", "")
    if not require_sig:
        # Signature validation is optional for the demo; enable by setting APPTRUST_REQUIRE_SIGNATURE=true
        return
    if not secret:
        raise HTTPException(status_code=401, detail="Signature required but secret is not configured")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Expect format: sha256=<hexdigest>
    sig = signature_header.strip()
    if sig.startswith("sha256="):
        sig = sig.split("=", 1)[1]
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # Constant time compare
    if not hmac.compare_digest(digest, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")


async def _dispatch_repository_event(payload: ReleaseCompletedPayload, trace_id: str) -> None:
    owner = os.environ.get("GITHUB_OWNER") or "yonatanp-jfrog"
    repo = os.environ.get("GITHUB_REPO") or "bookverse-helm"
    token = os.environ.get("GITHUB_TOKEN") or ""
    event_type = os.environ.get("REPO_DISPATCH_EVENT") or "platform_release"
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not configured")

    url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    body = {
        "event_type": event_type,
        "client_payload": {
            # Preserve original fields
            "applicationVersion": payload.applicationVersion,
            "applicationKey": payload.applicationKey,
            "stage": payload.stage or "prod",
            "trace_id": trace_id,
            # Compatibility fields consumed by existing workflows
            "platform_version": payload.applicationVersion,
            "tag": payload.applicationVersion,
        },
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, content=json.dumps(body))
        if resp.status_code != 204:
            raise HTTPException(status_code=502, detail=f"GitHub dispatch failed: HTTP {resp.status_code}")


@app.post("/webhooks/apptrust")
async def apptrust_webhook(
    request: Request,
    x_apptrust_signature_256: Optional[str] = Header(default=None, convert_underscores=False),
    x_event_id: Optional[str] = Header(default=None, convert_underscores=False),
    traceparent: Optional[str] = Header(default=None, convert_underscores=False),
):
    raw = await request.body()
    _verify_signature(raw, x_apptrust_signature_256)

    try:
        payload = ReleaseCompletedPayload.parse_obj(json.loads(raw.decode("utf-8")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Filter only platform application
    if payload.applicationKey != "bookverse-platform":
        # Accept but no-op to be robust; alternatively, return 202 without dispatch
        return {"accepted": True, "dispatched": False, "reason": "ignored applicationKey"}

    # Idempotency (best-effort, in-memory)
    now = time.time()
    _prune_seen(now)
    event_id = x_event_id or f"{payload.applicationKey}:{payload.applicationVersion}"
    if event_id in _seen_events:
        return {"accepted": True, "dispatched": False, "reason": "duplicate"}

    trace_id = traceparent or event_id
    await _dispatch_repository_event(payload, trace_id)
    _seen_events[event_id] = now
    return {"accepted": True, "dispatched": True}


