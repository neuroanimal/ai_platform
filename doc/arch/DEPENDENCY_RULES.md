# Dependency Rules

## Purpose

This document defines **mandatory dependency and import rules**
for the AI Platform.

Its role is to:
- prevent architectural erosion,
- make dependencies auditable,
- enable automated boundary checks,
- support multi-language implementations.

These rules are normative.

---

## Global Dependency Principles

1. Dependencies must always point **inward**.
2. Higher-level layers may depend on lower-level layers, never the opposite.
3. Circular dependencies are forbidden.
4. Cross-layer shortcuts are forbidden.
5. Technology-specific code must not leak upward.

---

## Top-Level Dependency Graph

frontend -+
+--> common
backend -+


Rules:
- `frontend` ? `common` ?
- `backend` ? `common` ?
- `frontend` ? `backend` ? (except via APIs)
- `common` ? anything ?

---

## code/common Rules

### Allowed Imports

- `common ? common`
- standard libraries
- pure third-party utilities

### Forbidden Imports

- `common ? backend`
- `common ? frontend`
- `common ? test`
- `common ? config`

`common` must remain pure and reusable.

---

## code/backend Rules

### Layer Dependency Direction

ui_layer -> service_layer -> domain_layer -> data_layer


Allowed:
- downward dependencies
- interface-based callbacks upward

Forbidden:
- upward concrete imports
- skipping layers

---

## code/frontend Rules

Allowed:
- `frontend ? common`
- UI framework dependencies
- API client abstractions

Forbidden:
- `frontend ? backend` (direct imports)
- business logic implementation
- persistence logic

---

## test Rules

Allowed:
- `test ? code`
- test framework dependencies
- mocks and stubs

Forbidden:
- `code ? test`

---

## config Rules

Allowed:
- configuration files
- environment descriptors

Forbidden:
- business logic
- imports from `code`

---

## Plugin Dependency Rules

Plugins:
- depend on interfaces, not implementations
- register via registry APIs
- must not self-discover via filesystem scanning

Registries:
- must be deterministic
- must not import concrete plugins eagerly

---

## Enforcement

These rules are intended to be enforced via:
- static analysis
- import boundary checkers
- linting rules
- CI pipelines

Concrete tooling is defined separately.

Violations are considered architectural defects.



# Dependency Rules for ai-platform

This document defines allowed and forbidden dependencies between layers,
packages, and modules in the AI Platform architecture.

All rules are additive: adding a dependency is allowed only if explicitly permitted.

---

## 1. Layer Overview

| Layer / Directory                  | Allowed to depend on                  |
|-----------------------------------|--------------------------------------|
| common/core                        | None (self-contained)                |
| common/engine                      | common/core                           |
| common/util                        | common/core, common/engine            |
| common/example                      | common/core, common/engine, common/util |
| backend/data_layer                 | common                                |
| backend/domain_layer               | backend/data_layer, common           |
| backend/service_layer/micro        | backend/domain_layer, common         |
| backend/service_layer/macro        | backend/domain_layer, common         |
| backend/ui_layer/cli               | backend/service_layer, common        |
| frontend/channel/*                 | common                                |
| frontend/shared                    | common                                |
| test/basic-structural              | common, backend, frontend             |
| test/functional                    | common, backend, frontend             |
| test/non-functional                | common, backend, frontend             |
| config/ops                         | None (declarative only)              |
| config/virtual                     | None (declarative only)              |
| doc/arch                           | None (documentation only)            |
| doc/board, doc/diagram, doc/report | None (documentation only)            |

---

## 2. Forbidden dependencies

- **No backward dependencies**: common may not depend on backend or frontend  
- **No cross-layer violations**:
  - data_layer → service_layer ❌
  - domain_layer → ui_layer ❌
  - frontend → backend ❌
- **No examples depending on business logic**:
  - common/example → backend ❌
  - common/example → frontend ❌
- **No runtime code in config or doc**:
  - config/ → code/ ❌
  - doc/ → code/ ❌

---

## 3. Import Rules

- **Use absolute imports** in Python:  
  ```python
  from code.common.core.registry.plugin_registry import PluginRegistry
  ```

- No relative imports that skip layer boundaries

- All dynamic resolution via registry for engines, ML/DL backends, DataFrame adapters, LLMs

## 4. Plugin / Registry Rules

- All plugins must implement a PluginContract (common/core/interface)

- Registration must happen explicitly in PluginRegistry

- Examples demonstrating plugin usage must remain isolated in common/example

- Plugin discovery must not use reflection, auto-discovery, or implicit imports

- Layer dependencies are respected even via registry: a plugin cannot pull backend-only code into common

## 5. Layering Enforcement Tips

- Backend may import Common only

- Frontend may import Common only

- Common must not import Backend or Frontend

- Tests may import layers under test + common

- CI/CD may run static analysis tools (e.g., pylint, mypy, ruff) to enforce rules

## 6. Notes

- Adding a new package or module must always consider these rules

- Violation may break add-only evolution or layer isolation

- Use example and engine/df abstractions to experiment with new adapters without breaking layer rules

---

### Co daje ten plik

- Pełną mapę **dozwolonych zależności** między katalogami.  
- Jasne instrukcje dla Pylance / mypy / ruff / CI.  
- Wspiera **add-only, plugin-based evolution**.  
- Można go wykorzystać do **automatycznej walidacji architektury**, np. w pytest + custom checker.  

---

