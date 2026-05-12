---
title: BadComponentReferenceRule
sidebar_label: BadComponentReferenceRule
description: Flags brittle component traversal patterns (.getSibling, .getParent, relative paths) in scripts and bindings.
---

# BadComponentReferenceRule

Flags object-traversal patterns like `.getSibling()`, `.getParent()`, `self.parent.`, and relative paths (`../`, `./`) in scripts and expression bindings. These patterns reach across the component tree by name or position, so any rename or reparent silently breaks them at runtime.

**Severity:** `error` by default — every traversal pattern is a known source of runtime breakage when view structure changes. Configurable via `severity`.

**Auto-fix:** No. Replacing a traversal call requires understanding the semantic intent — which custom property to bind to, which message to send, what state to lift — and the rule cannot infer that from string matching. Migrations are manual.

## Basic config

The simplest setup — enable the rule with all defaults:

```json
{
  "BadComponentReferenceRule": {
    "enabled": true
  }
}
```

That's it. The rule scans every script and expression binding in the view, flags any of the 16 default traversal patterns, and fails the lint run on the first match.

## Common configurations

### Warning-only during onboarding

When introducing the rule on a codebase that already has traversal calls, downgrade to a warning so CI doesn't immediately go red:

```json
{
  "BadComponentReferenceRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning"
    }
  }
}
```

Pair with the [whitelist](../../usage/whitelist.md) for legacy views you'll fix later, then promote to `error` once the backlog is gone.

### Customize the pattern list

To add team-specific helpers (or drop patterns that don't apply to your style), provide your own `forbidden_patterns`. Note: this **replaces** the defaults — copy the ones you want to keep:

```json
{
  "BadComponentReferenceRule": {
    "enabled": true,
    "kwargs": {
      "forbidden_patterns": [
        ".getSibling(",
        ".getParent(",
        ".getChild(",
        ".getChildren(",
        ".getParents(",
        "self.parent.",
        "self.children."
      ]
    }
  }
}
```

The example above adds a custom `.getParents(` helper and drops `./` and `../` (useful when relative-path expressions are an intentional part of your binding style).

### Catch non-canonical capitalization

For legacy code with inconsistent casing, enable case-insensitive matching so `Self.GetSibling(...)` is still caught:

```json
{
  "BadComponentReferenceRule": {
    "enabled": true,
    "kwargs": {
      "case_sensitive": false
    }
  }
}
```

This rarely matters for Python scripts (Python is case-sensitive anyway), but is occasionally useful when third-party tools or generated code rewrite method names.

## Examples

### Problematic code

From `tests/cases/BadComponentReferences/view.json`, the `BadButton.onActionPerformed` event handler:

```python
# Bad pattern 1: getSibling
sibling = self.getSibling('StatusLabel')
sibling.props.text = 'Button clicked!'

# Bad pattern 2: getParent
parent = self.getParent()
parent.props.style.backgroundColor = 'red'
```

Output:

```
BadComponentReferenceRule (error):
  • root.BadButton.events.onActionPerformed: Script contains '.getSibling(' and 1 other object traversal pattern(s) which creates brittle view structure dependencies. Consider using view.custom properties or message handling for component communication instead.
```

The rule emits one violation per script or expression — when more than one pattern matches the same content, it names the first and mentions the count of additional matches.

The same fixture also includes an expression binding that fails:

```
{../StatusLabel.position.display} || {../ContainerWithBadScript.position.display}
```

The `../` substring matches and the rule emits an `Expression contains '../'` violation.

## Recommended alternatives

- **`view.custom.*` properties** — store shared data on the view and bind multiple components to it. Renames stay in one place (the binding path), not buried inside script logic.
- **Message handlers** — call `system.perspective.sendMessage(...)` from the publisher and register a message handler on the subscriber. The two components are decoupled by message type instead of tree position.
- **Session and page properties** — for state that spans views, use `session.custom.*` or page-scope properties.
- **Direct property bindings** — where two components really do need to mirror each other, use a property binding from the source's path rather than a script that reads via `getSibling`.

## See also

- [Full BadComponentReferenceRule reference](../../reference/structure/bad-component-reference.md) — every option, the full default pattern list, edge cases, and violation message format
- [ComponentReferenceValidationRule](./component-reference-validation.md) — the companion rule that fires only when a referenced component does not exist
- [Configuration overview](../../getting-started/configuration.md)
