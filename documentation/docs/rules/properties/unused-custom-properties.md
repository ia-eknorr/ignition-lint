---
title: UnusedCustomPropertiesRule
sidebar_label: UnusedCustomPropertiesRule
description: Flags custom properties and view parameters that are defined but never referenced.
---

# UnusedCustomPropertiesRule

Flags custom properties and view parameters that are defined in a view but never read, bound, or written to. These dangling definitions accumulate as views evolve — bindings get rewritten, parameters get renamed, components get removed — and they leave behind dead configuration that adds noise to the designer, bloats serialized views, and confuses future maintainers.

**Severity:** `error` by default — unused properties are technical debt that the rule asks you to clean up. Downgrade to `"warning"` while bringing a legacy view into compliance.

**Auto-fix:** No. Removing a property might break an external contract (e.g. a parent view writes to an output param), so the rule defers to a human. Resolve violations by either deleting the definition or wiring up a real reference.

## Basic config

Enable the rule with defaults — unused props become errors:

```json
{
  "UnusedCustomPropertiesRule": {
    "enabled": true
  }
}
```

That's it. Every `custom.*`, `params.*`, and `<component>.custom.*` definition in the view is checked, and anything that isn't bound or referenced gets flagged.

## Common configurations

### Downgrade to warning while cleaning up legacy views

Useful when you're adopting the rule on a codebase that already has lots of orphaned definitions — surface them in CI logs without breaking the build:

```json
{
  "UnusedCustomPropertiesRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning"
    }
  }
}
```

### Strict mode on a freshly-cleaned codebase

Once a view is clean, lock it down so new unused props never sneak in:

```json
{
  "UnusedCustomPropertiesRule": {
    "enabled": true,
    "kwargs": {
      "severity": "error"
    }
  }
}
```

## Examples

### Correct code

A view-level custom property that is referenced from an expression binding passes. `usedProp` is read inside the binding text, so the rule marks it as used:

```json
{
  "custom": {
    "usedProp": "value"
  },
  "root": {
    "children": [
      {
        "meta": { "name": "TestLabel" },
        "type": "ia.display.label",
        "custom": {
          "usedComponentProp": "value"
        },
        "props": {
          "text": {
            "binding": {
              "type": "expression",
              "config": {
                "expression": "{view.custom.usedProp} + {this.custom.usedComponentProp}"
              }
            }
          }
        }
      }
    ]
  }
}
```

A property that has its own binding is also considered used — even if nothing else references it. From `tests/cases/PreferredStyle/view.json`:

```json
{
  "custom": {
    "customViewParam": "value"
  },
  "params": {
    "viewParam": "value"
  },
  "propConfig": {
    "custom.customViewParam": { "persistent": true },
    "params.viewParam": { "paramDirection": "input", "persistent": true }
  }
}
```

### Problematic code

A view with `custom` and `params` entries that are never bound and never referenced:

```json
{
  "custom": {
    "unusedViewProp": "value"
  },
  "params": {
    "unusedViewParam": "default value"
  },
  "root": {
    "children": [],
    "meta": { "name": "root" }
  }
}
```

Output:

```
UnusedCustomPropertiesRule (error):
  • custom.unusedViewProp: custom property 'unusedViewProp' is defined but never referenced
  • params.unusedViewParam: view parameter 'unusedViewParam' is defined but never referenced
```

## What counts as "used"

A property is treated as used when **any** of the following hold:

- The property has a binding of any type (expression, property, tag, query) — a property being populated by a binding is "used" by definition.
- It appears in an expression binding, e.g. `{view.custom.X}`, `{view.params.X}`, `{this.custom.X}`, `{self.view.custom.X}`, or `{self.view.params.X}`.
- It appears in a property binding's target/source path.
- It appears in a tag binding's `tagPath` string.
- It appears in a script (event handler, message handler, custom method, transform), e.g. `self.view.custom.X`, `self.view.params.X`, `self.custom.X`, or `self.params.X`.

A fallback string-scan over every value in the flattened JSON catches references in fields the model builder doesn't surface as dedicated nodes — so most real-world reference patterns get picked up automatically.

## Caveats

- **Output parameters** are evaluated by the same rules as everything else. An output param (`paramDirection: "output"`) with no binding and no inbound references is flagged because it cannot deliver data back to a parent view.
- **`propConfig` entries** are not new definitions — they are binding-owner markers. So `propConfig.params.breakerStatus.binding` marks `view.params.breakerStatus` as used.
- **Wildcard component references**: `{this.custom.foo}` and `self.custom.foo` can't be resolved to a specific component, so they mark **every** `*.custom.foo` definition as used. This means views that share a property name across many components may under-report unused properties (but never produce false positives for legitimate usages).
- **Persistent vs non-persistent**: the rule does not differentiate. Both are scanned the same way and both are eligible to be flagged.
- **Private properties**: names starting with `_` (and the reserved `_JavaDate`) are skipped during property discovery.

## See also

- [Full UnusedCustomPropertiesRule reference](../../reference/properties/unused-custom-properties.md) — every detection phase, every regex, every edge case
- [Configuration overview](../../getting-started/configuration.md) — the `rule_config.json` schema
