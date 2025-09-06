# BookVerse Platform

This repository is part of the JFrog AppTrust BookVerse demo. The demo highlights secure delivery across microservices using JFrog Platform capabilities: AppTrust lifecycle and promotion, SBOMs and signatures, Xray policies, and GitHub Actions OIDC for passwordless pipelines.

## What this repository represents

The Platform repo provides shared components, utilities, and templates that other BookVerse services can reuse. In the demo, it follows the same Python + Docker packaging and promotion model.

## How this repo fits the demo

- CI builds Python and Docker artifacts
- SBOM generation and signing (placeholders in scaffold)
- Publishes to Artifactory internal repos (DEV/QA/STAGING)
- Promotion workflow moves artifacts through AppTrust stages to PROD
- Uses GitHub OIDC for authentication to JFrog

## Platform Aggregator

- Plan of action: see `PLAN_OF_ACTION.md` for architecture, algorithms, workflow, and rollout strategy.
- Aggregator CLI entrypoint: `python -m app.main`
- Static services config: `config/services.yaml` (PROD-only sourcing; SBOM handled by AppTrust automatically)
- Manifests output directory: `manifests/`

### Run locally (preview)

```bash
cd bookverse-platform
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --config config/services.yaml --output-dir manifests --source-stage PROD --preview
```

### Create platform version and write manifest

```bash
python -m app.main --config config/services.yaml --output-dir manifests --source-stage PROD
```

### Overrides

You can force specific service versions:

```bash
python -m app.main --source-stage PROD --override inventory=1.8.2 --override checkout=0.7.1
```

### Workflows

- [`aggregate.yml`](.github/workflows/aggregate.yml) — Manual (default) aggregator. Resolves latest PROD microservice versions and:
  - Preview mode (default): prints a summary only
  - Write mode (`write=true`): writes manifest under `manifests/` and creates a platform version in AppTrust
  - Real environments may enable a schedule (every second Monday 09:00 UTC) — commented out by default
- [`promote-platform.yml`](.github/workflows/promote-platform.yml) — Promote a platform version to QA/STAGING/PROD via AppTrust; when targeting PROD, dispatches a helm pin to `bookverse-helm`
- [`rollback-platform.yml`](.github/workflows/rollback-platform.yml) — Roll back a platform version in PROD; supports optional auto-resolution of the latest promoted version and a `dry_run` mode

## CI Expectations

GitHub variables required:

- `PROJECT_KEY` = `bookverse`
- `JFROG_URL` = your JFrog instance URL
- `DOCKER_REGISTRY` = Docker registry hostname in Artifactory

Internal repositories:

- Docker: `bookverse-platform-docker-internal-local`
- Python: `bookverse-platform-python-internal-local`

Release repositories:

- Docker: `bookverse-platform-docker-release-local`
- Python: `bookverse-platform-python-release-local`

## Promotion

Use `.github/workflows/promote.yml` selecting QA, STAGING, or PROD. Evidence placeholders can be wired to real gates in a full setup.

## Related demo resources

- BookVerse scenario overview in the AppTrust demo materials
- Other repos: `bookverse-inventory`, `bookverse-recommendations`, `bookverse-checkout`, `bookverse-demo-assets`

---
This repository is intentionally minimal to showcase platform capabilities. Expand with shared platform code as needed for demos.
