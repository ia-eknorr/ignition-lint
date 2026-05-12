---
title: ExcessiveContextDataRule (full reference)
sidebar_label: ExcessiveContextDataRule
description: Full technical reference for ExcessiveContextDataRule — every option, every detection method, every violation message format.
toc_max_heading_level: 4
---

# ExcessiveContextDataRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/properties/excessive-context-data.md). This page is the complete technical reference — every constructor argument, every detection algorithm, every violation message format. Read it when you're tuning thresholds, debugging a violation, or planning a data-migration refactor.

:::

## Purpose
Custom properties on a Perspective view are meant to hold **configuration**, not **data**. This rule flags views that have crossed that line — large arrays, sprawling sibling structures, deep nesting, or huge overall data volume embedded directly in `view.json`. Datasets that large belong in a database (named queries), the tag historian, or are fetched at runtime via gateway scripts and message handlers.

## Severity
`error` by default — excessive data in view JSON causes real performance and memory problems, so the rule errs on the side of blocking CI. Configurable via the `severity` option.

## What it checks
The rule operates on the flattened JSON representation of the view and runs four independent detection methods, each scoped to keys that start with `custom.`:

| Method | What it detects | Default threshold |
| --- | --- | --- |
| Array size | Arrays under `custom.*` with too many items | `max_array_size = 50` |
| Property breadth | Too many sibling properties under any `custom.*` parent | `max_sibling_properties = 50` |
| Nesting depth | Custom property paths nested deeper than the threshold | `max_nesting_depth = 5` |
| Total data points | Total count of all flattened paths under `custom.*` | `max_data_points = 1000` |

Because the four checks run independently, a single view can produce up to four violations from this rule.

## Why it matters
Embedding large datasets in `view.json` causes a chain reaction of problems. The gateway has to parse and hold the full JSON document in memory every time the view loads, model building (and therefore linting) slows down proportionally to the document size, and the file balloons in your version control history. Worse, it conflates two separate concerns: a view file is supposed to describe a UI, not be a dump of the data the UI displays. Once the data is baked into the view, refreshing it requires a redeploy — so the data goes stale, gets duplicated across views, and becomes a maintenance liability. Datasets belong behind named queries or the tag historian, where they can be cached, paginated, and updated independently of the UI.

## Configuration

The rule accepts five options grouped into two categories below. All thresholds are independent — disabling one detection method requires setting its threshold high enough that it cannot be exceeded; there is no single on/off switch per method.

### Detection thresholds

#### `max_array_size`
**Type:** `int` &nbsp;·&nbsp; **Default:** `50`

Maximum allowed length for any array stored under `custom.*`. Computed as `max_observed_index + 1` for each property path that matches the regex `^(custom\.[^\[]+)\[(\d+)\]`. Each array property that exceeds this threshold emits its own violation.

---

#### `max_sibling_properties`
**Type:** `int` &nbsp;·&nbsp; **Default:** `50`

Maximum allowed number of unique sibling keys under any `custom.*` parent path. Array indices `[N]` are stripped before counting, so `custom.data[0].x` and `custom.data[1].x` count as a single child `x` under `custom.data`. Each parent path that exceeds this threshold emits its own violation.

---

#### `max_nesting_depth`
**Type:** `int` &nbsp;·&nbsp; **Default:** `5`

Maximum allowed depth for any `custom.*` path, measured as `len(parts) - 1` after splitting on `.` (so `custom.a.b.c` is depth 3). The rule tracks only the single deepest path it observes and emits at most **one** depth violation per file, even when multiple paths exceed the threshold.

---

#### `max_data_points`
**Type:** `int` &nbsp;·&nbsp; **Default:** `1000`

Maximum allowed count of total flattened paths under `custom.*`. Flattening produces an entry for every leaf **and** every intermediate path component, so deeply nested objects accumulate counts faster than shallow flat ones. At most one violation is emitted per file from this method.

### Severity

#### `severity`
**Type:** `"warning" | "error"` &nbsp;·&nbsp; **Default:** `"error"`

Severity for every violation emitted by this rule (all four detection methods share the same severity). Set to `"warning"` during legacy migrations or initial adoption so the rule reports but does not break CI.

## Detection methods in detail

### 1. Array size
The rule iterates every key in the flattened JSON and matches it against the regex `^(custom\.[^\[]+)\[(\d+)\]`. The first capture group is the property path (e.g., `custom.dropdownData.rows`) and the second is the array index. For each property path, the rule keeps the maximum index it encounters and reports `array_size = max_index + 1`. If that size exceeds `max_array_size`, a violation is added.

**Violation message format** (from `add_violation` in source):

```
<property_path>: Custom property '<property_name>' contains <N> items. Large datasets should be stored in databases, not view JSON. Maximum recommended: <max_array_size> items.
```

`<property_name>` is `<property_path>` with the leading `custom.` stripped.

### 2. Property breadth
For every flattened path under `custom.*`, array indices `[N]` are stripped (so `custom.data[0].value` and `custom.data[1].value` collapse into `custom.data.value`). The rule then walks each path part-by-part starting at `custom.X` and records the unique child segments observed under each parent. Any parent whose unique child count exceeds `max_sibling_properties` produces a violation.

**Violation message format:**

```
<parent_path>: Contains <N> sibling properties. Large flat structures should be stored in databases, not view JSON. Maximum recommended: <max_sibling_properties> siblings.
```

### 3. Nesting depth
The rule normalizes each `custom.*` path (stripping array indices) and counts depth as `len(parts) - 1` after splitting on `.`. So `custom.a.b.c` is depth 3, `custom.a.b.c.d.e.f` is depth 6. The rule tracks only the single deepest path it sees; if its depth exceeds `max_nesting_depth`, **one** violation is emitted per file (regardless of how many other paths also exceed the threshold).

**Violation message format:**

```
<deepest_path>: Custom properties are nested <N> levels deep. Deeply nested structures indicate complex data that should be in databases. Maximum recommended: <max_nesting_depth> levels.
```

### 4. Data points
The rule counts every flattened path that starts with `custom.`. Because flattening produces an entry for every leaf **and** every intermediate path component, a few large objects can quickly accumulate thousands of paths. If the total exceeds `max_data_points`, a violation is added.

**Violation message format:**

```
custom: Contains <N> total data points across all custom properties. Large volumes of data should be stored in databases, not view JSON. Maximum recommended: <max_data_points> data points.
```

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

The real fixture contains hundreds of rows (`[ ... 784 items total ]`) — enough to push the view well past `max_array_size = 50`.

### Problematic code: Excessive breadth
A flat dictionary of devices keyed by ID will trip the breadth check:

```json
{
  "custom": {
    "devices": {
      "device1": { "name": "Pump A" },
      "device2": { "name": "Pump B" },
      "device3": { "name": "Pump C" }
    }
  }
}
```

Once `custom.devices` accumulates more than 50 unique children, the rule fires.

### Problematic code: Excessive depth
Deep object trees produce a single depth violation for the deepest path:

```json
{
  "custom": {
    "a": { "b": { "c": { "d": { "e": { "f": "value" } } } } }
  }
}
```

`custom.a.b.c.d.e.f` is six levels deep, exceeding the default `max_nesting_depth = 5`.

### Problematic code: Excessive data points
This violation fires when the **total** number of flattened paths under `custom.*` crosses `max_data_points`. A single property with hundreds of nested objects can trip it on its own, even when no individual array, breadth, or depth threshold is breached.

## Auto-fix support
This rule does not provide auto-fixes — moving data out of a view is a semantic refactor that the rule cannot perform safely. The replacement strategy depends on where the data should live (named query, tag historian, message handler), and only a developer can make that call.

## Edge cases & exemptions
- Properties outside `custom.*` (e.g., `params.*`, `propConfig.*`, `props.*`) are not analyzed.
- Each detection method runs independently; one fixture can produce up to 4 violations from this rule.
- Array size is computed as `max_index + 1`; sparse arrays are not handled specially — only the highest observed index matters.
- The depth method reports only the **deepest** path even if many paths exceed the threshold (one violation per file from this method).
- The data-points method counts intermediate path components produced by JSON flattening, not just leaf values, so deeply nested objects accumulate counts faster than wide flat ones.
- The breadth method strips `[N]` array indices before counting siblings, so `custom.data[0].x`, `custom.data[1].x` count as a single child `x` under `custom.data`.
- The rule processes the flattened JSON directly (`set_flattened_json`) rather than visiting model nodes, so `target_node_types` is intentionally an empty set — the rule's logic runs once per file in `process_nodes`.

## See also
- [ExcessiveContextDataRule user guide](../../rules/properties/excessive-context-data.md) — the short version
- [UnusedCustomPropertiesRule](../../rules/properties/unused-custom-properties.md)
- [Configuration overview](../../getting-started/configuration.md)
