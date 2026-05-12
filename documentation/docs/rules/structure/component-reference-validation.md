---
title: ComponentReferenceValidationRule
sidebar_label: ComponentReferenceValidationRule
description: Validates that component references in bindings and scripts resolve to real components in the view hierarchy.
---

# ComponentReferenceValidationRule

Walks your component tree and verifies that every relative reference — `{../Component.props.value}` expressions, dotted property binding paths, and `self.getSibling()` / `self.getChild()` script chains — actually points at a component that exists. Where [BadComponentReferenceRule](./bad-component-reference.md) flags the *pattern* as bad practice, this rule flags references that are also *broken*.

**Severity:** `error` by default — a reference that doesn't resolve will fail at runtime, often silently (a binding produces `null`, a script raises a `NoneType` attribute error). Promote to `warning` if your team is still cleaning up legacy references and you don't want CI to fail.

**Auto-fix:** No. Fixing a broken reference requires knowing what the developer *intended* — `{../NonExistentButton.props.text}` could mean any of several existing siblings, or a component that needs to be re-added.

## Basic config

The simplest setup — validate every reference type at error severity:

```json
{
  "ComponentReferenceValidationRule": {
    "enabled": true
  }
}
```

That's it. Run the linter and any broken expression binding, property binding, or script chain is reported with the full reference text and the missing component name.

## Common configurations

### Disable script validation

If your team frequently writes scripts that build component names dynamically (e.g. `self.getSibling(self.props.targetName)`), the static analyzer can't follow those calls and `validate_scripts` will produce noise. Turn it off and rely on expression/property-binding validation:

```json
{
  "ComponentReferenceValidationRule": {
    "enabled": true,
    "kwargs": {
      "validate_scripts": false
    }
  }
}
```

### Downgrade to warning during migration

When introducing the rule to an existing codebase with known broken references, run it as `warning` first so CI keeps passing while you triage. Promote back to `error` once the backlog is clear:

```json
{
  "ComponentReferenceValidationRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning"
    }
  }
}
```

### Validate only expressions

Tackle one reference type at a time — start with expressions (usually the easiest to fix), leave property bindings and scripts for later:

```json
{
  "ComponentReferenceValidationRule": {
    "enabled": true,
    "kwargs": {
      "validate_expressions": true,
      "validate_property_bindings": false,
      "validate_scripts": false
    }
  }
}
```

## Examples

### Correct code

`Button2` references its sibling `Button1` via a one-level-up expression. The reference resolves — passes:

```json
{
  "children": [
    { "meta": { "name": "Button1" }, "type": "ia.input.button", "props": { "text": "Button 1" } },
    {
      "meta": { "name": "Button2" },
      "type": "ia.input.button",
      "propConfig": {
        "props.enabled": {
          "binding": {
            "config": { "expression": "{../Button1.props.text}" },
            "type": "expr"
          }
        }
      }
    }
  ],
  "meta": { "name": "root" },
  "type": "ia.container.coord"
}
```

### Problematic code

`Button2`'s binding references `NonExistentButton`, which isn't a sibling of `Button2`:

```json
{
  "config": { "expression": "{../NonExistentButton.props.text}" },
  "type": "expr"
}
```

Output:

```
ComponentReferenceValidationRule (error):
  • <binding path>: Expression references non-existent component 'NonExistentButton' in: {../NonExistentButton.props.text}
```

A script-side break looks similar:

```python
nested = self.getSibling('Container1').getChild('MissingButton')
```

```
ComponentReferenceValidationRule (error):
  • <script path>: Component 'MissingButton' not found as child in: self.getSibling('Container1').getChild('MissingButton')
```

## Path semantics

Relative reference syntax follows Ignition's binding rules — and they're not obvious. **Each dot beyond the first means one level up the tree**:

| Reference | Levels up | Meaning |
| --- | --- | --- |
| `..` | 1 | Go to my parent |
| `...` | 2 | Go to my grandparent |
| `....` | 3 | Go up 3 levels |

After climbing, **forward slashes drill back down**. So `.../Parent/Child.props.value` means: go up 2 levels, find a child named `Parent`, then find `Child` inside `Parent`, then access `props.value`.

The rule resolves these paths the same way Ignition does at runtime — by walking the parent/child map built from your view tree. If the climb runs out of parents (e.g. a top-level child uses `...`), the rule emits a "navigates above root" violation rather than silently failing.

For the resolution algorithm and component-path extraction details, see [the reference page](../../reference/structure/component-reference-validation.md#how-references-are-resolved).

## Relationship to BadComponentReferenceRule

The two rules are complementary — most teams should run both:

| Rule | Fires when... | Default severity |
| --- | --- | --- |
| [`BadComponentReferenceRule`](./bad-component-reference.md) | The traversal pattern appears at all (style enforcement) | `warning` |
| `ComponentReferenceValidationRule` | The traversal exists AND the target doesn't resolve (correctness enforcement) | `error` |

`BadComponentReferenceRule` discourages relative-traversal references entirely in favor of property bindings and parameters. `ComponentReferenceValidationRule` catches broken references that slipped past style review or that the team has consciously decided to keep using. If you only run one, run this one — incorrect references are a real bug, while the style preference is a judgment call.

## See also

- [Full ComponentReferenceValidationRule reference](../../reference/structure/component-reference-validation.md) — every option, every violation message, every edge case
- [BadComponentReferenceRule](./bad-component-reference.md) — the complementary style rule
- [Configuration overview](../../getting-started/configuration.md) — the `rule_config.json` schema
