# Common Code

This directory contains cross-cutting, technology-agnostic code
shared across backend, frontend, and tooling.

Scope:
- core architectural abstractions
- contracts and interfaces
- registries and plugin mechanisms
- engines (IO, DataFrame, orchestration, visualization)
- utilities without business semantics

Rules:
- no business logic
- no application-specific behavior
- no dependency on backend or frontend
- stable APIs preferred over frequent changes

Common code defines the architectural foundation of ai-platform.

