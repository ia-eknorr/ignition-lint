---
title: Introduction
sidebar_position: 1
slug: /
description: Static analysis for Ignition Perspective view.json files
---

# Ignition Lint

Static analysis for Ignition Perspective `view.json` files. Catches naming inconsistencies, performance issues, dead custom properties, broken component references, and Python errors in scripts — before the gateway runs them.

## What it does

Ignition Lint parses Perspective view definitions, builds an object model of components, bindings, and scripts, and runs a configurable set of rules over that model. Rules are visitor-pattern classes you can extend; the framework ships with seven built-in rules covering the most common pitfalls in Perspective views.

## When to use it

- **In a pre-commit hook** — block bad views before they hit the repo. See [Pre-commit integration](./usage/pre-commit.md).
- **In CI** — fail the build on regressions. See [GitHub Actions](./usage/github-actions.md).
- **From the CLI** — audit existing views or analyze new ones. See [Command line](./usage/cli.md).

## Built-in rules

| Rule | Category | What it catches |
| --- | --- | --- |
| [NamePatternRule](./rules/naming/name-pattern.md) | Naming | Component, property, and script names that don't match a configured convention |
| [BadComponentReferenceRule](./rules/structure/bad-component-reference.md) | Structure | Brittle traversal patterns (`.getSibling()`, `.getParent()`, relative paths) |
| [ComponentReferenceValidationRule](./rules/structure/component-reference-validation.md) | Structure | Relative references that don't resolve to a real component |
| [PollingIntervalRule](./rules/performance/polling-interval.md) | Performance | `now()` polling intervals below a configurable minimum |
| [UnusedCustomPropertiesRule](./rules/properties/unused-custom-properties.md) | Properties | Custom properties and view parameters defined but never referenced |
| [ExcessiveContextDataRule](./rules/properties/excessive-context-data.md) | Properties | Large datasets stored in custom properties (arrays, breadth, depth, total volume) |
| [PylintScriptRule](./rules/scripts/pylint-script.md) | Scripts | Pylint findings across every script in the view |

## Where to start

- **Just trying it out?** → [Installation](./getting-started/installation.md) → [Quick start](./getting-started/quick-start.md)
- **Setting up a project?** → [Configuration](./getting-started/configuration.md) → [Pre-commit integration](./usage/pre-commit.md)
- **Writing a custom rule?** → [Architecture](./developing/architecture.md) → [Creating rules](./developing/creating-rules.md)
- **Debugging a rule or a view?** → [Debug output](./usage/debug-output.md) → [Troubleshooting](./developing/troubleshooting.md)

## Project links

- **Source**: [github.com/design-group/ignition-lint](https://github.com/design-group/ignition-lint)
- **Package**: [pypi.org/project/ignition-lint](https://pypi.org/project/ignition-lint/)
- **Issues**: [GitHub Issues](https://github.com/design-group/ignition-lint/issues)
