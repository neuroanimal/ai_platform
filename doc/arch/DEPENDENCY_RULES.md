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

