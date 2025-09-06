import argparse
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import cmp_to_key

import yaml


def load_services_config(config_path: Path) -> List[Dict[str, Any]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Services config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    services = data.get("services", [])
    if not isinstance(services, list) or not services:
        raise ValueError("Config 'services' must be a non-empty list")
    return services


SEMVER_RE = re.compile(
    r"^\s*v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\s*$"
)


class SemVer:
    def __init__(self, major: int, minor: int, patch: int, prerelease: Tuple[str, ...], original: str) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.original = original

    @staticmethod
    def parse(version: str) -> Optional["SemVer"]:
        m = SEMVER_RE.match(version)
        if not m:
            return None
        g = m.groupdict()
        prerelease_raw = g.get("prerelease") or ""
        return SemVer(int(g["major"]), int(g["minor"]), int(g["patch"]), tuple(prerelease_raw.split(".")) if prerelease_raw else tuple(), version)


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
    # Use the SemVer objects for proper ordering
    parsed.sort(key=cmp_to_key(lambda a, b: compare_semver(a[0], b[0])), reverse=True)
    return [v for _, v in parsed]


class AppTrustClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, query: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            q = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
            url = f"{url}?{q}"
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

    def list_application_versions(self, app_key: str, limit: int = 200) -> Dict[str, Any]:
        path = f"/applications/{urllib.parse.quote(app_key)}/versions"
        return self._request("GET", path, query={"limit": limit, "order_by": "created", "order_asc": "false"})

    def get_version_content(self, app_key: str, version: str) -> Dict[str, Any]:
        path = f"/applications/{urllib.parse.quote(app_key)}/versions/{urllib.parse.quote(version)}/content"
        return self._request("GET", path)

    def create_platform_version(self, platform_app_key: str, version: str, sources_versions: List[Dict[str, str]]) -> Dict[str, Any]:
        path = f"/applications/{urllib.parse.quote(platform_app_key)}/versions"
        body = {
            "version": version,
            "sources": {
                "versions": sources_versions,
            },
        }
        return self._request("POST", path, body=body)


RELEASED = "RELEASED"
TRUSTED = "TRUSTED_RELEASE"


def compute_next_semver_for_application(client: AppTrustClient, app_key: str) -> str:
    """Return next SemVer for the given application by incrementing PATCH.

    Logic mirrors the CI flows used by individual services:
    - Fetch latest created version
    - If present and SemVer-compatible, increment the patch component
    - Otherwise default to 1.0.0
    """
    try:
        resp = client.list_application_versions(app_key, limit=1)
        versions = resp.get("versions", []) if isinstance(resp, dict) else []
        latest = str(versions[0].get("version", "")) if versions else ""
    except Exception:
        latest = ""

    if latest:
        parsed = SemVer.parse(latest)
        if parsed is not None:
            return f"{parsed.major}.{parsed.minor}.{parsed.patch + 1}"

    return "1.0.0"


def pick_latest_prod_version(client: AppTrustClient, app_key: str) -> Optional[str]:
    resp = client.list_application_versions(app_key)
    versions = resp.get("versions", [])
    prod = [str(v.get("version", "")) for v in versions if str(v.get("release_status", "")).upper() in (RELEASED, TRUSTED)]
    prod = [v for v in prod if v]
    if not prod:
        return None
    ordered = sort_versions_by_semver_desc(prod)
    return ordered[0] if ordered else None


def resolve_promoted_versions(services_cfg: List[Dict[str, Any]], client: AppTrustClient) -> List[Dict[str, Any]]:
    """Resolve latest promoted (PROD) version per configured application.

    Returns list entries with: name, apptrust_application, resolved_version.
    """
    resolved: List[Dict[str, Any]] = []
    for s in services_cfg:
        name = s.get("name")
        app_key = s.get("apptrust_application")
        if not name or not app_key:
            raise ValueError(f"Service config missing required fields: {s}")
        latest = pick_latest_prod_version(client, app_key)
        if not latest:
            raise RuntimeError(f"No PROD version found for application {app_key}")
        resolved.append(
            {
                "name": name,
                "apptrust_application": app_key,
                "resolved_version": latest,
            }
        )
    return resolved


def build_manifest(applications: List[Dict[str, Any]], client: AppTrustClient, source_stage: str) -> Dict[str, Any]:
    if source_stage != "PROD":
        raise ValueError("Platform aggregation demo only supports source_stage=PROD")

    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    manifest_version = now.strftime("%Y.%m.%d.%H%M%S")

    apps_block: List[Dict[str, Any]] = []
    for entry in applications:
        app_key = entry.get("apptrust_application")
        version = entry.get("resolved_version") or entry.get("simulated_version", "0.0.0-sim")
        if not app_key or not version:
            raise ValueError(f"Application entry missing required fields: {entry}")

        content = client.get_version_content(app_key, str(version)) or {}
        sources = content.get("sources", {}) if isinstance(content, dict) else {}
        releasables = content.get("releasables", {}) if isinstance(content, dict) else {}

        apps_block.append(
            {
                "application_key": app_key,
                "version": version,
                "sources": sources,
                "releasables": releasables,
            }
        )

    manifest: Dict[str, Any] = {
        "version": manifest_version,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "source_stage": source_stage,
        "applications": apps_block,
        "provenance": {
            # SBOM evidence is handled automatically by AppTrust; not generated here
            "evidence_minimums": {"signatures_present": True},
        },
        "notes": "Auto-generated by platform-aggregator (applications & versions)",
    }
    return manifest


def write_manifest(output_dir: Path, manifest: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"platform-{manifest['version']}.yaml"
    target = output_dir / filename
    with target.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)
    return target


def format_summary(manifest: Dict[str, Any]) -> str:
    apps = manifest.get("applications", [])
    rows = []
    for comp in apps:
        rows.append(
            {
                "application_key": comp.get("application_key"),
                "version": comp.get("version"),
            }
        )
    return json.dumps(
        {
            "platform_manifest_version": manifest["version"],
            "platform_app_version": manifest.get("platform_app_version", ""),
            "applications": rows,
        },
        indent=2,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BookVerse Platform Aggregator (demo). Generates a platform manifest by selecting latest PROD microservice versions.",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "services.yaml"),
        help="Path to services.yaml (static configuration).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent.parent / "manifests"),
        help="Directory to write manifests into.",
    )
    parser.add_argument(
        "--source-stage",
        default="PROD",
        help="Source stage (fixed to PROD for the demo).",
    )
    parser.add_argument(
        "--platform-app",
        default=os.environ.get("PLATFORM_APP_KEY", "bookverse-platform"),
        help="Platform application key in AppTrust.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: resolve live versions and print summary only (no AppTrust or file writes).",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="SERVICE=VERSION",
        help="Override a service version (can be provided multiple times), e.g., inventory=1.8.2",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    source_stage = args.source_stage
    do_write = not bool(args.preview)

    services_cfg = load_services_config(config_path)

    base_url = os.environ.get("APPTRUST_BASE_URL")
    token = os.environ.get("APPTRUST_ACCESS_TOKEN")
    if not base_url or not token:
        print("Missing APPTRUST_BASE_URL or APPTRUST_ACCESS_TOKEN (live mode only)", flush=True)
        return 2
    client = AppTrustClient(base_url=base_url, token=token)
    services = resolve_promoted_versions(services_cfg, client)
    # Apply overrides if provided
    overrides: Dict[str, str] = {}
    for ov in getattr(args, "override", []) or []:
        if "=" not in ov:
            print(f"Ignoring malformed override: {ov}")
            continue
        svc, ver = ov.split("=", 1)
        svc = svc.strip()
        ver = ver.strip()
        if not svc or not ver:
            print(f"Ignoring malformed override: {ov}")
            continue
        overrides[svc] = ver
    if overrides:
        for s in services:
            name = s.get("name")
            if name in overrides:
                s["resolved_version"] = overrides[name]

    manifest = build_manifest(services, client, source_stage)

    # Determine next platform application SemVer (patch bump) following service CI logic
    platform_app_key = str(getattr(args, "platform_app"))
    platform_app_version = compute_next_semver_for_application(client, platform_app_key)

    # Include platform app SemVer in manifest for visibility (manifest version remains CalVer)
    manifest["platform_app_version"] = platform_app_version

    print(format_summary(manifest))

    if do_write:
        target = write_manifest(output_dir, manifest)
        print(f"Wrote manifest: {target}")
        # Create platform application version in AppTrust
        sources_versions = [
            {"application_key": s["apptrust_application"], "version": s["resolved_version"]}
            for s in services
        ]
        resp = client.create_platform_version(platform_app_key, platform_app_version, sources_versions)
        print(json.dumps({"platform_version_created": resp}, indent=2))
    else:
        print("Preview: resolved live versions; no files written and no AppTrust changes. Omit --preview to create the platform version and write the manifest.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


