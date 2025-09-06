#!/usr/bin/env python3
from __future__ import annotations

"""
Local copy of AppTrust rollback utility (sourced from inventory service).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

SEMVER_RE = re.compile(
    r"^\s*v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\s*$"
)


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Tuple[str, ...]
    original: str

    @staticmethod
    def parse(version: str) -> Optional["SemVer"]:
        m = SEMVER_RE.match(version)
        if not m:
            return None
        g = m.groupdict()
        prerelease_raw = g.get("prerelease") or ""
        return SemVer(
            int(g["major"]), int(g["minor"]), int(g["patch"]), tuple(prerelease_raw.split(".")) if prerelease_raw else tuple(), version
        )


def compare_semver(a: SemVer, b: SemVer) -> int:
    if a.major != b.major:
        return -1 if a.major < b.major else 1
    if a.minor != b.minor:
        return -1 if a.minor < b.minor else 1
    if a.patch != b.patch:
        return -1 if a.patch < b.patch else 1
    if not a.prerelease and b.prerelease:
        return 1
    if a.prerelease and not b.prerelease:
        return -1
    for at, bt in zip(a.prerelease, b.prerelease):
        if at == bt:
            continue
        a_num, b_num = at.isdigit(), bt.isdigit()
        if a_num and b_num:
            ai, bi = int(at), int(bt)
            if ai != bi:
                return -1 if ai < bi else 1
        elif a_num and not b_num:
            return -1
        elif not a_num and b_num:
            return 1
        else:
            if at < bt:
                return -1
            return 1
    if len(a.prerelease) != len(b.prerelease):
        return -1 if len(a.prerelease) < len(b.prerelease) else 1
    return 0


def sort_versions_by_semver_desc(version_strings: List[str]) -> List[str]:
    parsed: List[Tuple[SemVer, str]] = []
    for v in version_strings:
        sv = SemVer.parse(v)
        if sv is not None:
            parsed.append((sv, v))
    parsed.sort(key=lambda t: t[0], reverse=True)  # type: ignore[arg-type]
    return [v for _, v in parsed]


class AppTrustClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read()
            if not raw:
                return {}
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return {"raw": raw.decode("utf-8", errors="replace")}

    def get_version_content(self, app_key: str, version: str) -> Dict[str, Any]:
        path = f"/applications/{urllib.parse.quote(app_key)}/versions/{urllib.parse.quote(version)}/content"
        return self._request("GET", path)

    def rollback_application_version(self, app_key: str, version: str, from_stage: str) -> Dict[str, Any]:
        path = f"/applications/{urllib.parse.quote(app_key)}/versions/{urllib.parse.quote(version)}/rollback"
        return self._request("POST", path, body={"from_stage": from_stage})


def rollback_in_prod(client: AppTrustClient, app_key: str, target_version: str) -> None:
    content = client.get_version_content(app_key, target_version)
    from_stage = str(content.get("current_stage") or "").strip()
    if not from_stage or from_stage.upper() == "UNASSIGNED":
        raise RuntimeError("Cannot rollback a version in UNASSIGNED or unknown stage")
    print(
        "Calling AppTrust endpoint: POST /applications/"
        f"{app_key}/versions/{target_version}/rollback with body {{from_stage: {from_stage}}}"
    )
    client.rollback_application_version(app_key, target_version, from_stage)
    print(f"Invoked AppTrust rollback for {app_key}@{target_version} from {from_stage}")


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name)
    return None if v is None or v.strip() == "" else v.strip()


def main() -> int:
    p = argparse.ArgumentParser(description="AppTrust PROD rollback utility (platform)")
    p.add_argument("--app", default="bookverse-platform", help="Application key")
    p.add_argument("--version", required=True, help="Target version to rollback (SemVer)")
    p.add_argument("--base-url", default=_env("APPTRUST_BASE_URL"), help="Base API URL (env: APPTRUST_BASE_URL)")
    p.add_argument("--token", default=_env("APPTRUST_ACCESS_TOKEN"), help="Access token (env: APPTRUST_ACCESS_TOKEN)")
    args = p.parse_args()

    if not args.base_url:
        print("Missing --base-url or APPTRUST_BASE_URL", file=sys.stderr)
        return 2
    if not args.token:
        print("Missing --token or APPTRUST_ACCESS_TOKEN", file=sys.stderr)
        return 2

    client = AppTrustClient(args.base_url, args.token)
    try:
        start = time.time()
        rollback_in_prod(client, args.app, args.version)
        print(f"Done in {time.time()-start:.2f}s")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


