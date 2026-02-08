# Backend

This directory contains backend-side application code.

Scope:

- data access and persistence
- business logic and domain rules
- infrastructure integration
- service orchestration
- API exposure (REST, RPC, CLI)

Layering:

- data_layer: data models and persistence logic
- domain_layer: business and infrastructure logic
- service_layer: micro and macro services
- ui_layer: CLI or other backend-facing interfaces

Rules:

- backend may depend on common
- backend must not depend on frontend
- business logic must not depend on delivery mechanisms
