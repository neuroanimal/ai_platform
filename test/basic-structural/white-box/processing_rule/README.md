# Architecture Rule Test

This directory contains architecture-level white-box tests.

Purpose:
- validate dependency direction
- detect forbidden imports
- verify layer isolation

No runtime logic is allowed here.
All tests must be deterministic and static.
