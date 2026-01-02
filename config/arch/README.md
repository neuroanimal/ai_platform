# Architecture Configuration

This directory contains architecture-level configuration files.

Purpose:
- define layer boundaries
- describe allowed and forbidden dependencies
- provide input for static architecture checks
- remain language-agnostic

Rules:
- no runtime logic
- no environment-specific configuration
- configuration must be declarative
- files must not import application code

Typical usage:
- static analysis tools
- CI boundary validation
- documentation of architectural decisions
