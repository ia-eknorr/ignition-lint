---
title: PollingIntervalRule
sidebar_label: PollingIntervalRule
description: Flags now() calls that poll faster than your configured minimum interval.
---

# PollingIntervalRule

Catches `now()` calls inside expression-based bindings that poll faster than the configured minimum. By default it rejects anything below **10000 ms** (10 seconds), including the most common offender: a bare `now()` (which polls every 1 second).

**Severity:** `error` by default — aggressive polling causes measurable gateway slowdowns, so the rule fails the build out of the box. Downgrade to `"warning"` while you retrofit a legacy project.

**Auto-fix:** No. Fixing a polling violation requires intent — bump the interval, switch to a tag/event-driven update, or explicitly disable polling with `now(0)`. The rule reports the offending expression and leaves the decision to you.

## Basic config

Just turn it on. The defaults catch the vast majority of problems:

```json
{
  "PollingIntervalRule": {
    "enabled": true
  }
}
```

That's it. Any expression-style binding (expression, expression-struct, query parameters, expression-mode tag bindings, indirect-mode tag references, expression transforms) that calls `now()` with no argument or with an interval below 10000 ms is flagged.

## Common configurations

### Relax the threshold during onboarding

When dropping the rule into an existing project, 10 seconds may be too aggressive to fix everything at once. Loosen to 5 seconds while you migrate:

```json
{
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 5000
    }
  }
}
```

### Tighten for production

Production gateways with many sessions benefit from a stricter floor. Push to 30 seconds:

```json
{
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 30000
    }
  }
}
```

### Downgrade to a warning

If you want the linter to surface polling smells without blocking the build (useful for legacy projects or pre-commit hooks):

```json
{
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 10000,
      "severity": "warning"
    }
  }
}
```

## Examples

### Problematic code

`tests/cases/ExpressionBindings/view.json` contains several real violations. A bare `now()` on a component prop binding:

```json
{
  "meta": { "name": "BadPollingDateTimeInput" },
  "propConfig": {
    "props.value": {
      "binding": {
        "config": { "expression": "now()" },
        "type": "expr"
      }
    }
  }
}
```

And an expression transform sitting on a property binding (the `now(5000)` is below the default minimum, and the `now()` is the 1-second default):

```json
{
  "binding": {
    "config": { "path": "view.params.inputProp" },
    "transforms": [
      { "expression": "now()",     "type": "expression" },
      { "expression": "now(5000)", "type": "expression" },
      { "expression": "now(11000)","type": "expression" }
    ],
    "type": "property"
  }
}
```

Output (against the default `minimum_interval: 10000`):

```
PollingIntervalRule (error):
  • view.custom.expressionPolling: 'now()'
  • view.custom.expressionStructurePolling.badPolling: 'now()'
  • view.custom.transformPolling: 'now()'
  • view.custom.transformPolling: 'now(5000)'
  • root.BadPollingDateTimeInput.props.value: 'now()'
```

The `now(11000)` transform is silently accepted — it sits at or above the 10000 ms floor.

## Where it looks

The rule walks every binding the model produces and scans the expression text for `now`. It covers:

- **Expression bindings** — the `expression` field.
- **Expression-struct bindings** — every value in the `struct` map (the offending key is appended to the path in the violation).
- **Query bindings** — every parameter expression in `parameters`.
- **Tag bindings in expression mode** — the `tagPath` is treated as an expression.
- **Tag bindings in indirect mode** — every value in `references`.
- **Expression transforms on property bindings** — modeled as expression bindings by the builder, so they go through the same check.

Tag bindings in **direct** mode are skipped (no expression text to evaluate).

## See also

- [Full PollingIntervalRule reference](../../reference/performance/polling-interval.md) — every option, every edge case, the exact regex used, and how `now(0)` is treated
- [Configuration overview](../../getting-started/configuration.md) — the `rule_config.json` schema
