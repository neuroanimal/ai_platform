# Architecture

## Purpose

This document defines the high-level architecture of the AI Platform.
Its goal is to provide a stable, explicit, and enforceable structural model
that supports long-term evolution, extensibility, and multi-technology integration.

The architecture is designed to:
- enforce strong separation of concerns,
- enable add-only evolution,
- support plugin-based extensibility,
- remain technology-agnostic,
- scale across teams, domains, and languages.

---

## Architectural Style

The platform follows a **Layered + Hexagonal + Plugin-Oriented Architecture**:

- **Layered**: clear vertical separation (common, backend, frontend, test)
- **Hexagonal (Ports & Adapters)**: domain logic isolated from infrastructure
- **Plugin-oriented**: dynamic registration and discovery of capabilities

No layer is allowed to “reach across” boundaries.

---

## High-Level Structure

ai-platform/
+-- code/
¦ +-- common/
¦ +-- backend/
¦ +-- frontend/
+-- test/
+-- config/
+-- doc/
+-- (root configuration files)

Each top-level area has a **single responsibility**.

---

## code/common

### Role

`common` contains **pure, reusable, technology-agnostic building blocks**
shared across backend, frontend, and tooling.

It must never depend on:
- backend-specific logic,
- frontend frameworks,
- deployment or runtime environments.

### Internal Responsibilities

- core abstractions and contracts
- type system and semantic models
- registries and plugin mechanisms
- engine-level orchestration and data flow
- utilities with no domain coupling

### Allowed Dependencies

- Standard language libraries
- Pure third-party utilities (no frameworks)
- Other `common` modules (respecting sub-layer rules)

---

## code/backend

### Role

`backend` implements **domain logic, services, and system integrations**.

It is responsible for:
- business rules
- domain models
- persistence and infrastructure adapters
- service composition
- APIs and CLIs

### Layering Inside Backend

backend/
+-- data_layer/
+-- domain_layer/
+-- service_layer/
+-- ui_layer/


Each layer may depend **only inward**, never outward.

---

## code/frontend

### Role

`frontend` provides **human-facing interaction layers**.

It contains:
- presentation logic
- UI orchestration
- client-side adapters

Frontend must:
- depend on `common`
- communicate with backend only via defined interfaces or APIs
- contain no business logic duplication

---

## test

### Role

`test` mirrors the entire codebase structure but contains **only test artifacts**.

It supports:
- structural testing
- functional testing
- non-functional testing
- white-box and black-box strategies

Tests may depend on production code,
but production code must never depend on tests.

---

## config

### Role

`config` contains **operational and environment-related configuration**.

This includes:
- ops configuration
- virtual/runtime definitions
- deployment descriptors

No executable business logic is allowed here.

---

## doc

### Role

`doc` is the **single source of architectural, technical, and analytical truth**.

It contains:
- architecture definitions
- diagrams
- reports
- design decisions

Documentation may reference code, but code must not depend on documentation.

---

## Plugin and Registry Architecture

The platform relies on **explicit registries** rather than implicit imports.

Key principles:
- registration instead of discovery by scanning
- explicit lifecycle control
- late binding of implementations
- interface-first design

Registries live in:

code/common/core/registry/

Plugins:
- implement interfaces from `core/interface`
- register themselves via registry APIs
- are resolved at runtime by orchestration layers

---

## Evolution Rules

- New layers may be added, existing ones are not removed.
- New modules extend existing boundaries, never weaken them.
- Refactoring is allowed only with explicit approval.
- Backward compatibility is preferred over breaking changes.

This architecture is intentionally strict to protect long-term scalability.

# AI Platform Architecture

This document describes the architectural design of ai-platform, including
layering, core principles, module responsibilities, and plugin/registry usage.

---

## 1. Architectural Principles

- **Add-only evolution** – no deletions or breaking changes; new functionality is added incrementally.
- **Strong layer boundaries** – layers may only depend on permitted lower layers.
- **Plugin-based extensibility** – all cross-cutting functionality is exposed via registry.
- **Multi-language support** – Python, R, Julia, JavaScript/TypeScript, Rust, etc.
- **Technology agnosticism** – core abstractions are independent of backend or frontend.

---

## 2. Layering Overview

### 2.1 Common (code/common)
- **Purpose:** cross-cutting, language-agnostic, reusable code
- **Subdirectories:**
  - `core/` – architectural contracts, interfaces, type definitions
  - `engine/` – engines for IO, DataFrame abstraction, orchestration, visualization
  - `util/` – utility functions and helpers
  - `example/` – living examples demonstrating registry and plugin usage
  - `other/` – ops, virtualization, container management
- **Dependencies:** independent; may not import backend or frontend

### 2.2 Backend (code/backend)
- **Purpose:** server-side logic, domain rules, data persistence
- **Subdirectories:**
  - `data_layer/` – data models, database connectors, repository patterns
  - `domain_layer/` – business logic and infra logic
  - `service_layer/` – micro and macro services
  - `ui_layer/` – CLI or other backend-facing interfaces
- **Dependencies:** may import `common`; must not import `frontend`

### 2.3 Frontend (code/frontend)
- **Purpose:** client-side presentation and channel interfaces
- **Subdirectories:**
  - `channel/web/`
  - `channel/mobile/`
  - `channel/desktop/`
  - `shared/` – reusable frontend components
- **Dependencies:** may import `common`; must not import `backend`

### 2.4 Documentation (doc/)
- **Purpose:** architectural diagrams, reports, board notes, statistical analysis
- **Subdirectories:**
  - `arch/` – architecture and dependency documentation
  - `board/` – kanban or decision boards
  - `diagram/` – UML, TikZ/Forest, or other visualizations
  - `report/` – structured reports and analytics

### 2.5 Tests (test/)
- Structured according to ISTQB:
  - `basic-structural/` – unit, coverage, static analysis
  - `functional/` – functional, integration, regression, UAT, system
  - `non-functional/` – performance, security, usability, reliability, compatibility
- Tests depend only on `common` or code under test

---

## 3. Plugin / Registry Mechanism

- **All cross-cutting functionality** is exposed via the registry in `common/core/registry`
- **PluginContract** defines the interface for all plugins
- **PluginRegistry** manages registration and resolution
- **Examples** are in `common/example/registry/`
- Registry enables:
  - LLM/Agent switching
  - ML/DL backend selection
  - DataFrame adapter injection

---

## 4. Import / Dependency Rules

- **General rules**
  - Absolute imports preferred
  - No cyclic dependencies
  - No cross-layer imports except allowed
- **Layer rules**
  - Backend ? may import Common
  - Frontend ? may import Common
  - Common ? may not import Backend or Frontend
  - Examples ? may import Common only
- **Configuration and docs**
  - Do not import runtime code
  - Use declarative config only

---

## 5. DataFrame Abstraction (engine/df)

- **Purpose:** unified interface for multiple DataFrame types
- **Supported types:**
  - Pandas, Dask, Spark (Python)
  - R `data.frame`, `caret`, `statsmodels`
  - Julia `DataFrames.jl`
- **Pattern:** adapter + registry
- **Contracts:** defined in `common/core/interface/dataframe_contract.py`

---

## 6. Engines (engine/)

- **IO Engine:** unified read/write for multiple formats (csv, parquet, json, DB)
- **Orchestration Engine:** pipeline management, scheduler interface
- **Visualization Engine:** abstracted plots (Plotly, Seaborn, TikZ, D3.js)
- **Registry Integration:** engines are registered as plugins and resolved at runtime

---

## 7. Virtualization / Containerization

- Located under `common/other/virtual/`
- Supports:
  - Docker images
  - Kubernetes pods
  - CI/CD integration
  - Versioned environment reproducibility

---

## 8. Key Principles in Practice

- **Examples** show exactly how to register and resolve plugins
- **Import rules** prevent accidental cross-layer coupling
- **Add-only** evolution ensures backward compatibility
- **Layer isolation** allows parallel development across backend, frontend, and common
- **Registry** supports dynamic switching of ML/DL backends, LLMs, and DataFrame types

---

## 9. References

- See `DEPENDENCY_RULES.md` for more detailed allowed/forbidden import matrix
- See `README.md` for high-level overview
- See `common/example/` for executable reference implementations


