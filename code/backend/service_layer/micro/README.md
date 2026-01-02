# code/backend/service_layer/micro

## Purpose
Defines responsibilities and scope of this directory within the ai-platform.

## Allowed Content
- Source files strictly related to this layer or concern
- Configuration or assets owned by this layer

## Forbidden Content
- Logic belonging to other architectural layers
- Direct dependencies violating dependency direction rules

## Dependency Rules
- May import only from explicitly allowed lower-level layers
- Must never import from higher-level layers

## Notes
- This directory is part of an add-only, versioned architecture
- Changes require explicit acceptance
