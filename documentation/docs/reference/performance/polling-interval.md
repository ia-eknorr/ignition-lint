---
title: PollingIntervalRule (full reference)
sidebar_label: PollingIntervalRule
description: Full technical reference for PollingIntervalRule — every option, every binding mode, every edge case.
toc_max_heading_level: 4
---

# PollingIntervalRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/performance/polling-interval.md). This page is the complete technical reference — every constructor argument, every default, every edge case the rule deliberately skips. Read it when you're debugging a violation, integrating with custom code, or extending the rule.

:::

## Purpose
Ensures that any `now()` call inside an expression-based binding uses a polling interval at or above a configurable minimum. This prevents accidental sub-second polling — a common cause of CPU spikes and gateway slowdowns in Ignition Perspective projects.

## Severity
`error` by default — polling intervals that are too aggressive cause real, measurable performance degradation on the gateway and should fail the build. Configurable via the `severity` option.

## What it checks
The rule extends `BindingRule` and visits every binding type (`ALL_BINDINGS`). For each binding it scans the relevant expression text(s) for the substring `now`, then validates the polling argument:

- **Expression bindings** (`visit_expression_binding`) — checks the binding's `expression` field.
- **Expression-struct bindings** (`visit_expression_struct_binding`) — checks every value in the binding's `struct` map, reporting the offending key.
- **Query bindings** (`visit_query_binding`) — checks every parameter expression in `parameters`.
- **Tag bindings, expression mode** (`visit_tag_binding` when `mode == "expression"`) — treats `tagPath` as an expression and checks it.
- **Tag bindings, indirect mode** (`visit_tag_binding` when `mode == "indirect"`) — checks every value in `references`.
- **Tag bindings, direct mode** — not checked (direct mode contains no expressions to evaluate).
- **Expression transforms on property bindings** — these are modeled as `ExpressionBinding` nodes by the builder, so they are covered by `visit_expression_binding`.

## Why it matters
In Ignition Perspective, `now(intervalMs)` is the canonical way to drive time-based polling inside an expression. The Ignition gateway re-evaluates that expression every `intervalMs` milliseconds, regardless of whether anything else has changed. A bare `now()` (no argument) defaults to a 1000 ms (1 second) refresh, and intervals below ~10 seconds add up quickly when multiplied by the number of concurrent sessions, components per view, and views per project. Common symptoms include:

- High gateway CPU usage and slow log files.
- Increased database load when polling expressions feed query bindings.
- Sluggish session updates because the scripting/expression executors are saturated.
- Memory pressure from the volume of intermediate values produced.

Holding all bindings to a sane minimum (10 seconds by default) keeps polling-driven load predictable and forces developers to opt into faster refresh rates explicitly.

## Configuration

The rule accepts 2 options grouped into the categories below.

### Threshold

#### `minimum_interval`
**Type:** `int` &nbsp;·&nbsp; **Default:** `10000`

Minimum polling interval in milliseconds. Any `now(x)` where `0 &lt; x &lt; minimum_interval` is a violation. The bound is **open on both sides** — `now(0)` is allowed (it disables polling in Ignition) and `now(minimum_interval)` is allowed (the comparison uses strict `<`).

### Severity

#### `severity`
**Type:** `"warning" | "error"` &nbsp;·&nbsp; **Default:** `"error"`

Default severity for emitted violations. Passed through to `BindingRule.__init__` and used by `add_violation`. Use `"warning"` to keep the rule informational without failing the build (common during onboarding or when retrofitting an existing project).

## How polling intervals are validated
Validation is performed by `_is_valid_polling`, which uses the regex:

```text
now\s*\(\s*(\d*)\s*\)
```

The behavior is:

1. **No `now` substring in the expression** — returns valid immediately. The rule short-circuits before calling `_is_valid_polling` via the outer `if 'now' in ...` guard, but the helper guards against this case as well.
2. **`now(` appears but the regex finds no matches** — for example `now(someVar)` or any non-empty argument that is not purely digits. A fallback regex (`now\s*\(`) confirms the call site exists, and the rule treats this as a violation (returns `False`).
3. **`now()` with no argument** — the captured group is the empty string. The check `if not interval_str.strip()` triggers and the rule reports a violation. This catches the most common Perspective default of `now()`, which polls at 1000 ms.
4. **`now(0)`** — the comparison is `0 &lt; interval &lt; minimum_interval`, so an interval of exactly `0` is **not** flagged (it falls outside the open interval). In Ignition this disables polling, so treating it as valid is intentional.
5. **`now(x)` where `0 &lt; x &lt; minimum_interval`** — flagged as a violation.
6. **`now(x)` where `x >= minimum_interval`** — valid.
7. **Non-numeric content inside the regex match** — caught by the `int(interval_str)` conversion; a `ValueError` is treated as a violation.

## Examples

### Correct code
```json
{
  "binding": {
    "config": {
      "expression": "now(11000)"
    },
    "type": "expr"
  }
}
```

`now(11000)` is at or above the default `minimum_interval` of 10000 ms, so the rule passes. `now(0)` is also valid (polling disabled), and any expression that does not call `now` at all is ignored.

### Problematic code
The fixture `tests/cases/ExpressionBindings/view.json` contains five real polling violations under the default configuration. One of them lives on the `BadPollingDateTimeInput` component:

```json
{
  "meta": {
    "name": "BadPollingDateTimeInput"
  },
  "propConfig": {
    "props.value": {
      "binding": {
        "config": {
          "expression": "now()"
        },
        "type": "expr"
      }
    }
  }
}
```

The bare `now()` defaults to a 1-second poll, well below the 10000 ms minimum.

The full set of violations from this fixture (with `minimum_interval: 10000`) covers each binding entry point:

- `view.custom.expressionPolling` → `now()` (expression binding).
- `view.custom.expressionStructurePolling.badPolling` → `now()` (expression-struct binding).
- `view.custom.transformPolling` → `now()` (expression transform on a property binding).
- `view.custom.transformPolling` → `now(5000)` (expression transform on a property binding).
- `root.BadPollingDateTimeInput.props.value` → `now()` (expression binding on a component prop).

**Violation message format:** `<path>: '<expression>'`

For struct, query, and indirect-tag bindings the path is suffixed with the offending key, for example `<path>.<key>: '<expression>'` or `<path>.references.<ref_key>: '<expression>'`.

## Binding modes covered
| Binding type | Visit method | What is scanned |
| --- | --- | --- |
| Expression binding | `visit_expression_binding` | The `expression` field |
| Expression-struct binding | `visit_expression_struct_binding` | Each value in `struct` |
| Query binding | `visit_query_binding` | Each value in `parameters` |
| Tag binding (expression mode) | `visit_tag_binding` | The `tagPath` (treated as expression) |
| Tag binding (indirect mode) | `visit_tag_binding` | Each value in `references` |
| Tag binding (direct mode) | — | Not checked (no expressions to evaluate) |

## Auto-fix support
This rule does not provide auto-fixes. Fixing a polling violation requires intent — either raising the interval to an acceptable value, switching to a tag binding/event-driven update, or explicitly disabling polling with `now(0)`.

## Edge cases & exemptions
- **Identifiers that contain the substring `now`** (for example `snowflakeId`, `knownGood`, or a property called `nowait`) will pass the cheap `'now' in expression` guard and fall through to the regex. Because the regex requires `now` to be followed by `(`, identifiers without a function call will match neither the primary nor fallback regex, and `_is_valid_polling` returns `True`. Be aware that an expression containing a substring like `windowNow(500)` would still match the call pattern and be flagged — the rule does not enforce that `now` is a standalone token.
- **`now()` with no argument** — flagged. The empty captured group is rejected by the `not interval_str.strip()` check.
- **`now(0)`** — not flagged. The interval check is `0 &lt; interval &lt; minimum_interval`, so zero falls outside the open lower bound. This matches Ignition's semantics where `now(0)` disables polling.
- **`now` called with a non-literal argument**, for example `now(myCustomInterval)` or `now({view.params.refreshMs})` — flagged. The primary regex only captures digit sequences, so any non-digit content yields no matches and the fallback regex confirms a call exists. The rule has no way to statically verify that a runtime expression resolves to an acceptable interval, so it conservatively reports a violation.
- **Tag bindings in `direct` mode** — silently skipped. There is no expression text to evaluate.
- **Reserved/private property keys** (names starting with `_`) — excluded by the `LintingRule` base class unless `include_private_properties=True` is set.
- **Multiple `now()` calls in one expression** — every captured interval is checked. Any failing interval causes the whole expression to be reported once.

## See also
- [PollingIntervalRule user guide](../../rules/performance/polling-interval.md) — the short version
- [Configuration overview](../../getting-started/configuration.md)
- [Creating Rules](../../developing/creating-rules.md)
