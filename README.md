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

## Repository layout
- `.github/workflows/ci.yml`: CI pipeline (test → build → SBOM/sign → publish)
- `.github/workflows/promote.yml`: Manual promotion workflow with evidence placeholders
- Application/library code and packaging files will be added as the demo evolves

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