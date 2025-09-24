# BookVerse Platform Aggregator

Demo aggregator for the BookVerse platform, showcasing JFrog AppTrust capabilities with shared library and aggregated release patterns.

## 🎯 Demo Purpose & Patterns

This service demonstrates the **Shared Library & Aggregator Pattern** - showcasing how platform components, shared libraries, and aggregated releases can be managed in AppTrust.

### 📚 **Shared Library & Aggregator Pattern**
- **What it demonstrates**: Application versions built from shared libraries, common utilities, and platform aggregation
- **AppTrust benefit**: Shared components promoted together ensuring platform consistency across all services (DEV → QA → STAGING → PROD)
- **Real-world applicability**: Platform teams, shared library management, and enterprise-wide component distribution

This service is **platform-focused** - it demonstrates how shared components can be reliably versioned and promoted across enterprise ecosystems.

## 🏗️ Platform Aggregator Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  BookVerse Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                ┌─────────────────────────┐                  │
│                │  Platform Aggregator    │                  │
│                │                         │                  │
│                │  Shared Libraries &     │                  │
│                │  Common Components      │                  │
│                │ ┌─────────────────────┐ │                  │
│                │ │   BookVerse Core    │ │                  │
│                │ │     Library         │ │                  │
│                │ └─────────────────────┘ │                  │
│                │ ┌─────────────────────┐ │                  │
│                │ │  Platform Scripts   │ │                  │
│                │ │   & Utilities       │ │                  │
│                │ └─────────────────────┘ │                  │
│                │ ┌─────────────────────┐ │                  │
│                │ │ Version & Config    │ │                  │
│                │ │   Management        │ │                  │
│                │ └─────────────────────┘ │                  │
│                └─────────────────────────┘                  │
│                          │                                  │
│     ┌────────────────────┼────────────────────┐             │
│     │                    │                    │             │
│ ┌───────────┐    ┌───────────┐    ┌───────────┐             │
│ │Inventory  │    │ Checkout  │    │Recommend- │             │
│ │ Service   │    │ Service   │    │ations     │             │
│ └───────────┘    └───────────┘    └───────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

AppTrust Promotion Pipeline:
DEV → QA → STAGING → PROD
 │     │       │        │
 └─────┴───────┴────────┘
   Shared Libraries & Config
   Move Together as Platform
```

## 🔧 JFrog AppTrust Integration

This service creates multiple artifacts per application version:

1. **Python Packages** - Shared library packages for all services
2. **Configuration Files** - Platform-wide configuration templates
3. **Docker Images** - Platform utility containers
4. **SBOMs** - Software Bill of Materials for shared dependencies
5. **Test Reports** - Integration testing across platform components
6. **Build Evidence** - Comprehensive platform build attestations

Each artifact moves together through the promotion pipeline: DEV → QA → STAGING → PROD.

For the non-JFrog evidence plan and gates, see: `../bookverse-demo-init/docs/EVIDENCE_PLAN.md`.

## 🔄 Workflows

- [`ci.yml`](.github/workflows/ci.yml) — CI: library tests, package builds, Docker builds, publish artifacts/build-info, AppTrust version and evidence
- [`promote.yml`](.github/workflows/promote.yml) — Promote the platform app version through stages with evidence
- [`promotion-rollback.yml`](.github/workflows/promotion-rollback.yml) — Roll back a promoted platform application version (demo utility)
