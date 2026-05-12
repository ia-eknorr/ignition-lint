---
title: ExcessiveContextDataRule
sidebar_label: ExcessiveContextDataRule
description: Flags large datasets embedded directly in custom properties — they belong in databases, not view JSON.
---

# ExcessiveContextDataRule

Catches the most common Perspective anti-pattern: stashing large datasets — lookup tables, device dictionaries, deeply nested config trees — directly inside a view's `custom.*` properties. That data belongs in a database (named queries), the tag historian, or is fetched at runtime via a gateway script and message handler.

**Severity:** `error` by default — embedded data causes real performance and memory problems, so the rule errs on the side of blocking CI. Drop to `"warning"` while migrating off a legacy view.

**Auto-fix:** No. Moving data out of `view.json` is a semantic refactor (database? tag historian? message handler?) that only a developer can decide.

## Basic config

Enable the rule and accept the default thresholds:

```json
{
  "ExcessiveContextDataRule": {
    "enabled": true
  }
}
```

That's it. Any view with an array longer than 50 items, a sibling group wider than 50 keys, a path nested deeper than 5 levels, or more than 1000 total custom-property paths is flagged.

## Common configurations

### Tighten thresholds for production

In tightly-controlled production projects you may want to be stricter than the defaults — small lookup arrays still belong in the database:

```json
{
  "ExcessiveContextDataRule": {
    "enabled": true,
    "kwargs": {
      "max_array_size": 20,
      "max_sibling_properties": 20,
      "max_nesting_depth": 4,
      "max_data_points": 500
    }
  }
}
```

### Relax during legacy migration

When you're inheriting a project full of data-stuffed views and need the rule to surface offenders without breaking CI, demote to a warning and loosen the thresholds:

```json
{
  "ExcessiveContextDataRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning",
      "max_array_size": 200,
      "max_data_points": 5000
    }
  }
}
```

Tighten the values back to the defaults as views get migrated off embedded data.

### Focus on volume, not shape

If your project legitimately needs nested config objects but never large arrays, raise depth and breadth and keep array/volume limits strict:

```json
{
  "ExcessiveContextDataRule": {
    "enabled": true,
    "kwargs": {
      "max_array_size": 50,
      "max_sibling_properties": 200,
      "max_nesting_depth": 10,
      "max_data_points": 1000
    }
  }
}
```

## What it detects

The rule runs four independent checks over every `custom.*` path in the flattened view. A single view can produce up to four violations.

| Check | What it flags | Default |
| --- | --- | --- |
| Array size | A single array under `custom.*` with too many items | `max_array_size = 50` |
| Property breadth | Too many sibling keys under one `custom.*` parent | `max_sibling_properties = 50` |
| Nesting depth | The deepest `custom.*` path goes deeper than allowed | `max_nesting_depth = 5` |
| Total data points | Total count of all flattened paths under `custom.*` | `max_data_points = 1000` |

For exact algorithms (regexes, normalization, and how depth/breadth are counted), see the [full reference](../../reference/properties/excessive-context-data.md#detection-methods-in-detail).

## Examples

### Problematic code: Excessive array size

The fixture `tests/cases/BadContextData/view.json` parks a giant lookup table inside a custom property. The structure looks like:

```json
{
  "custom": {
    "dropdownData": {
      "rows": [
        { "label": "ROW-1A", "value": "ROW-1A" },
        { "label": "ROW-1B", "value": "ROW-1B" },
        { "label": "ROW-1C", "value": "ROW-1C" }
      ]
    }
  }
}
```

The real fixture contains `[ ... 784 items total ]` — well past the default `max_array_size = 50`. The linter emits:

```
ExcessiveContextDataRule (error):
  • custom.dropdownData.rows: Custom property 'dropdownData.rows' contains 784 items. Large datasets should be stored in databases, not view JSON. Maximum recommended: 50 items.
```

## Recommended alternatives

When this rule fires, the fix isn't to raise the threshold — it's to move the data out of the view:

- **Named queries** against the database for lookup tables and reference data
- **Tag historian** for time-series data
- **Server-side pagination** for tabular data displayed in tables or dropdowns
- **Runtime fetch** via a gateway script plus a Perspective message handler when the view actually mounts
- **Session/page properties** for derived data that needs to live during a user session but not in the persisted view

## See also

- [Full ExcessiveContextDataRule reference](../../reference/properties/excessive-context-data.md) — every option, every detection algorithm, every violation message format
- [UnusedCustomPropertiesRule](./unused-custom-properties.md) — the complementary check for custom properties no one reads
- [Configuration overview](../../getting-started/configuration.md) — the `rule_config.json` schema
