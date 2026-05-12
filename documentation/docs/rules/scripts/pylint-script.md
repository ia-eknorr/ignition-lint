---
title: PylintScriptRule
sidebar_label: PylintScriptRule
description: Runs pylint on every Python script embedded in a Perspective view.
---

# PylintScriptRule

Runs the full [pylint](https://pylint.readthedocs.io/) static analyzer over every Python script embedded in a Perspective `view.json` — event handlers, message handlers, custom methods, and transform scripts. This is the project's primary defense against script bugs that would otherwise only show up at runtime in the Ignition gateway.

**Severity:** `error` by default for Fatal and Error pylint categories; `warning` for Warning, Convention, and Refactor. Each category can be remapped independently via `category_mapping`.

**Auto-fix:** Yes, for trailing whitespace (C0303 only). Other pylint findings are reported but not auto-fixed.

## Basic config

The simplest setup — accept the defaults:

```json
{
  "PylintScriptRule": {
    "enabled": true
  }
}
```

That's it. The rule discovers a project-local `.config/.ignition-pylintrc` if one exists, otherwise it falls back to the bundled package config, and runs every script through pylint with the default category mapping.

## Common configurations

### Strict — every finding fails the build

For projects that want CI to fail on style violations too, not just bugs:

```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "category_mapping": {
        "F": "error",
        "E": "error",
        "W": "error",
        "C": "error",
        "R": "error"
      }
    }
  }
}
```

### Permissive — only fatal errors fail

For projects that are still cleaning up legacy scripts and only want the build to fail on unparseable code:

```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "category_mapping": {
        "F": "error",
        "E": "warning",
        "W": "warning",
        "C": "warning",
        "R": "warning"
      }
    }
  }
}
```

### Custom pylintrc path

For projects that keep their pylint config somewhere non-standard:

```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "pylintrc": "ci/pylint/perspective.pylintrc"
    }
  }
}
```

Relative paths are resolved against the current working directory.

### Batch mode for faster CI

When linting many views at once, batch mode runs pylint a single time across all scripts instead of once per file:

```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "batch_mode": true
    }
  }
}
```

Trade-off: batch mode disables trailing-whitespace auto-fix and prints fully qualified script paths (`<file>::<script>`) in violation output.

## What it lints

The rule submits four script categories to pylint:

- **Event handler scripts** — `onActionPerformed`, `onClick`, and every other `events.*` script
- **Message handler scripts** — entries under `scripts.messageHandlers`
- **Custom component methods** — entries under `scripts.customMethods`
- **Transform scripts** — script transforms attached to property bindings

For the precise JSON path each node type maps to, see the [reference's script types table](../../reference/scripts/pylint-script.md#script-types-analyzed).

## Examples

### Correct code

A clean event handler from `tests/cases/AllScriptTypes/view.json` passes pylint under the default configuration:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\tsystem.perspective.print('ActionButton Pressed')"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

The script is tab-indented (required so the source is valid Python after the wrapping function header), uses the stubbed `system` global, and has no unresolved references.

### Problematic code

A real event handler from `tests/cases/PylintViolations/view.json` triggers four different pylint categories at once:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\timport json\n\timport sys\n\tprint(undefined_variable)\n\tresult = some_object.nonexistent_method()"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

This single script produces:

- `W0611` — unused import `json` and unused import `sys` (warnings)
- `E0602` — undefined variable `undefined_variable` (error)
- `E1101` — instance has no `nonexistent_method` member (error)

## Output format

Findings are grouped by pylint category and routed to the errors or warnings stream according to `category_mapping`. A typical mixed output:

```
    Pylint - Error (E):
      • root.SubmitButton.onActionPerformed: Line 3: Undefined variable 'undefined_variable' (E0602)

    Pylint - Warning (W):
      • root.SubmitButton.onActionPerformed: Line 1: Unused import json (W0611)
```

Categories always render in `F, E, W, C, R` order regardless of how pylint emits them, and empty categories are omitted.

## What `--fix` does

When run with `--fix`, the rule strips trailing whitespace from any script that has a `C0303` violation. The fix rewrites the script body once (one `SET_VALUE` per affected script, not per line) and is marked safe, so it is applied by default.

No other pylint finding has an auto-fix. "Remove unused import", "rename invalid variable", and "add missing docstring" all require more context than the rule can safely infer, so those are reported as violations only.

Trailing-whitespace fixes are also disabled in `batch_mode` — see the [reference for the full rationale](../../reference/scripts/pylint-script.md#auto-fix-support).

## Pylintrc

If `pylintrc` is not set, the rule searches for `.config/.ignition-pylintrc` starting from the current working directory and walking upward to the filesystem root. The closest match wins. If nothing is found in the project tree, it falls back to the `.config/.ignition-pylintrc` shipped inside the installed `ignition_lint` package. If that's also missing, it falls back to a small inline ruleset: `unused-import`, `undefined-variable`, `syntax-error`, `invalid-name`.

For the full lookup sequence (including how absolute and relative `pylintrc` paths are handled, what happens when the file is missing, and how the bundled config is located), see the [reference's pylintrc resolution order](../../reference/scripts/pylint-script.md#pylintrc-resolution-order).

## Common gotchas

- **Scripts must be indented.** Perspective stores script bodies as plain strings that the rule wraps inside a function header, so the body must start with leading tabs or spaces. Unindented scripts are flagged as a data-quality issue separate from any pylint finding.
- **Don't mix tabs and spaces.** Indentation that contains both tabs and spaces on the same line is flagged with `Script mixes tabs and spaces for indentation. Use either tabs OR spaces consistently.` Pick one style per script.
- **Ignition built-ins are stubbed.** The combined temp file injects `system = None`, `self = {}`, and `event = {}` at the top, so referencing those names does not trigger `undefined-variable` (`E0602`). Anything else pylint cannot resolve is reported normally.
- **Function-redefined is suppressed.** Multiple custom methods can define the same helper name (e.g. two methods that both define a `_validate` helper). The bundling concatenates them, which would otherwise trip pylint's `function-redefined` check, so it's disabled.
- **Empty scripts are skipped.** If a script contains only whitespace, pylint is not invoked for it at all.

## See also

- [Full PylintScriptRule reference](../../reference/scripts/pylint-script.md) — every option, the full pylintrc resolution order, debug output, and edge cases
- [Configuration overview](../../getting-started/configuration.md) — the `rule_config.json` schema
