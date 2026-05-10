---
title: PylintScriptRule (full reference)
sidebar_label: PylintScriptRule
description: Full technical reference for PylintScriptRule — every option, every category, every edge case the rule handles.
toc_max_heading_level: 4
---

# PylintScriptRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/scripts/pylint-script.md). This page is the complete technical reference — every constructor argument, every default, the full pylintrc resolution order, and every edge case the rule deliberately handles. Read it when you're debugging a violation, integrating with custom CI configuration, or extending the rule.

:::

## Purpose
Runs the full [pylint](https://pylint.readthedocs.io/) static analyzer over every Python script embedded in a Perspective `view.json` file. This is the project's primary defense against script-level bugs that would otherwise only surface at runtime in the Ignition gateway.

## Severity
`error` by default — pylint surfaces real bugs (undefined variables, syntax errors). Severity is granular per pylint category via `category_mapping`: by default Fatal (`F`) and Error (`E`) findings raise errors, while Warning (`W`), Convention (`C`), and Refactor (`R`) findings raise warnings. Each category can be remapped independently to either `error` or `warning`.

## What it checks
PylintScriptRule visits every Python script that the model builder produces and submits the full set to pylint. Specifically it covers:

- **Event handler scripts** (`onActionPerformed`, `onClick`, etc.) — `NodeType.EVENT_HANDLER`
- **Message handler scripts** — `NodeType.MESSAGE_HANDLER`
- **Custom component methods** (entries under `scripts.customMethods`) — `NodeType.CUSTOM_METHOD`
- **Transform scripts** (script transforms attached to bindings) — `NodeType.TRANSFORM`

Every collected script is concatenated into a single temporary `.py` file with stub globals injected at the top, then handed to pylint as one batch. The rule maps any reported line numbers back to the originating script using a line map built during concatenation, so violations are reported against the original Perspective script path (e.g. `root.SubmitButton.onActionPerformed`) rather than the temp file.

In addition to running pylint, the rule performs two cheap data-quality checks before invoking pylint:

- Scripts that lack any leading indentation in `view.json` are flagged (Perspective requires script bodies to be indented for valid Python syntax).
- Scripts whose leading whitespace mixes both tabs *and* spaces on the same line are flagged with a clear message asking the author to pick one.

## Why it matters
In Ignition Perspective, every script you write — event handlers, transforms, message handlers, custom methods — is stored as a Python string inside `view.json`. There is no compile step on the Designer side: a typo in a variable name, a missing import, or a syntax error survives a "save" and only surfaces when the gateway tries to execute the script for a real user. By the time you discover the problem, a button is broken in production, a binding is silently failing, or a message handler is swallowing exceptions. Running pylint statically over those scripts before the view is committed catches this entire class of latent bugs in CI or in a pre-commit hook, rather than in the runtime logs.

## How it works
1. **Collect.** During the visitor traversal, every `ScriptNode` (event handler, message handler, custom method, transform) is captured into `self.collected_scripts` keyed by a composite `<file_path>::<script_path>` key. The composite key lets one rule instance handle multiple input files in batch mode without colliding on identical script paths.
2. **Pre-flight data-quality checks.** Before invoking pylint, the rule scans each script for unindented first lines and mixed tab/space indentation. These are added directly to the rule's errors as separate violations (they are independent of any pylint finding).
3. **Combine.** All scripts are concatenated into a single multi-script document via `_combine_scripts`. The document begins with a stub preamble:
    ```python
    # pylint: disable=unused-argument,missing-docstring,redefined-outer-name,function-redefined
    # Stub for common globals, and to simulate the Ignition environment
    system = None
    self = {}
    event = {}
    ```
    Each script is preceded by a header comment (`# File: ... # Script N: <path>`) so debug output is readable, and a per-line-number map is built so output can be remapped.
4. **Write.** The combined content is written to a uniquely-named temp file (`<HHMMSS>_pid<PID>_*.py`) so parallel invocations do not collide.
5. **Run pylint.** `pylint.lint.Run` is invoked on the temp file. If a pylintrc was found (see [Pylintrc resolution order](#pylintrc-resolution-order)), it is passed via `--rcfile`. Otherwise the rule falls back to a small inline ruleset: `--disable=all --enable=unused-import,undefined-variable,syntax-error,invalid-name`. pylint's stdout/stderr are redirected to a `StringIO` buffer for parsing.
6. **Parse.** Each pylint output line matching `<file>:<line>:<col>: <CODE>: <message>` is parsed. The leading character of the code (`F`, `E`, `W`, `C`, or `R`) determines the category; the temp-file line number is mapped back to a source script via the line map, and the original-script-relative line number is computed.
7. **Group.** Each parsed finding is stored as a `PylintViolation` dataclass on `self.pylint_violations`. Output is later assembled by `format_violations_grouped`, which groups findings by category, prints each category's name, and routes the grouped block to either the errors or warnings stream according to `category_mapping`.
8. **Auto-fix (optional).** If fix mode is active and any violation has code `C0303` (trailing-whitespace), `_generate_trailing_whitespace_fixes` produces one safe `Fix` per affected script that strips trailing whitespace from every line via `SET_VALUE` on the script's JSON path.

## Configuration

The rule accepts six options grouped into four categories below. All options are passed through `kwargs` in `rule_config.json`.

### Severity & categories

#### `severity`
**Type:** `str` &nbsp;·&nbsp; **Default:** `"error"`

Default severity used when a pylint category is not present in `category_mapping`. Per-category overrides in `category_mapping` take precedence — `severity` is only consulted as a fallback for unknown category letters (anything outside `F`, `E`, `W`, `C`, `R`).

---

#### `category_mapping`
**Type:** `dict[str, str]` &nbsp;·&nbsp; **Default:** `{'F': 'error', 'E': 'error', 'W': 'warning', 'C': 'warning', 'R': 'warning'}`

Maps pylint message categories to ignition-lint severities. Each key is a single uppercase letter (`F`, `E`, `W`, `C`, or `R`); each value is `"error"` or `"warning"`. Setting every category to `"error"` puts the rule into strict mode; setting all but `F` to `"warning"` puts it into permissive mode. See [Default category mapping](#default-category-mapping) for the table of letters to category names.

### Pylintrc

#### `pylintrc`
**Type:** `str | None` &nbsp;·&nbsp; **Default:** `None`

Path to a pylintrc file. If absolute, used directly. If relative, resolved against `os.getcwd()`. If `None`, the rule searches upward from cwd for `.config/.ignition-pylintrc`, then falls back to the bundled `.config/.ignition-pylintrc` inside the installed package. If still not found, the rule runs pylint with the inline fallback `--disable=all --enable=unused-import,undefined-variable,syntax-error,invalid-name`. See [Pylintrc resolution order](#pylintrc-resolution-order) for the full lookup sequence.

### Execution mode

#### `batch_mode`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `False`

When `True`, accumulates scripts across all linted files into one pylint invocation. Faster on large repos because pylint pays its startup cost only once. The trade-off: auto-fixes for trailing whitespace are disabled in batch mode (the rule does not retain enough per-file context to produce per-file fixes safely), and violation paths are printed with the full composite key `<file>::<script_path>` instead of just `<script_path>`.

### Debug

#### `debug`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `False`

When `True`, the rule always copies the combined script to the debug directory (even on a clean run), writes a sibling `pylintrc_used.txt` recording which pylintrc was resolved, and prints the active `category_mapping`. When `False`, the combined script is only saved when pylint reports findings.

---

#### `debug_dir`
**Type:** `str | None` &nbsp;·&nbsp; **Default:** `None`

Directory for debug script dumps. If absolute, used directly. If relative, joined with `os.getcwd()`. If `None`, the rule looks for the nearest `tests/` ancestor of cwd and uses `<that>/debug`, otherwise falls back to `.ignition-lint/debug` under cwd. The directory is created lazily only when a debug file actually needs to be written.

### Default category mapping
| Pylint category | Letter | Default severity |
| --- | --- | --- |
| Fatal | `F` | `error` |
| Error | `E` | `error` |
| Warning | `W` | `warning` |
| Convention | `C` | `warning` |
| Refactor | `R` | `warning` |

Unknown categories (anything outside `F`, `E`, `W`, `C`, `R`) fall back to the rule's default `severity`.

### Configuration examples

**Default (recommended) — bugs as errors, style as warnings:**
```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {}
  }
}
```

**Strict — every pylint finding fails the build:**
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

**Permissive — only fatal and error categories surface as errors, everything else is hidden as warnings (matches the default but pinned explicitly):**
```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "pylintrc": ".config/.ignition-pylintrc",
      "category_mapping": {
        "F": "error",
        "E": "error",
        "W": "warning",
        "C": "warning",
        "R": "warning"
      }
    }
  }
}
```

**Custom pylintrc with batch mode for faster CI runs:**
```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "pylintrc": "ci/pylint/perspective.pylintrc",
      "batch_mode": true,
      "debug": false
    }
  }
}
```

**Debug mode — always save the combined script for inspection:**
```json
{
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
      "debug": true,
      "debug_dir": "tests/debug"
    }
  }
}
```

## Pylintrc resolution order
`_resolve_pylintrc_path` runs the following lookup in order. The first hit wins:

1. **Explicit absolute path** — if `pylintrc` was passed as an absolute path and the file exists, use it. If it does not exist, a warning is printed and the rule continues with the search below.
2. **Explicit relative path** — if `pylintrc` was passed as a relative path, it is resolved against the current working directory (`os.getcwd()`). If the resolved path exists, use it. If it does not exist, a warning is printed and the rule continues with the search below.
3. **Project-tree search** — starting from cwd and walking upward toward the filesystem root, the rule looks for `<dir>/.config/.ignition-pylintrc` at every level. The first match (i.e. the closest ancestor that contains a `.config/.ignition-pylintrc`) wins. This is how a repository-local pylintrc is discovered automatically.
4. **Bundled package config** — the rule then checks the pylintrc shipped inside the installed `ignition_lint` package at `<package>/.config/.ignition-pylintrc`. This is the fallback that ships with the wheel when no project-local config is present.
5. **No pylintrc** — if all of the above miss, the rule runs pylint with the inline fallback `--disable=all --enable=unused-import,undefined-variable,syntax-error,invalid-name` and `--score=no`.

## Script types analyzed
The rule targets the entire `ALL_SCRIPTS` set from `model/node_types.py`. `_get_script_content_path` is used in fix mode to translate the model node back to its JSON content slot.

| NodeType | What gets analyzed | JSON suffix used by `_get_script_content_path` |
| --- | --- | --- |
| `MESSAGE_HANDLER` | `scripts.messageHandlers[*].script` | `.script` |
| `CUSTOM_METHOD` | `scripts.customMethods[*].script` | `.script` |
| `TRANSFORM` | `propConfig.<prop>.binding.transforms[*].code` | `.code` |
| `EVENT_HANDLER` | `events.<scope>.<eventName>.config.script` (or `.script` as a fallback) | `.config.script`, then `.script` |

For each visited node, the script body is fetched via `node.get_formatted_script()` (which auto-wraps the raw script body inside a Python function with the appropriate signature so pylint sees a syntactically valid function definition).

## Examples

### Correct code

A clean event handler from `tests/cases/AllScriptTypes/view.json`:

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

A clean transform from the same fixture:

```json
{
  "transforms": [
    {
      "code": "\treturn 'Good %s' % (value)",
      "type": "script"
    }
  ]
}
```

A clean custom method from the same fixture:

```json
{
  "customMethods": [
    {
      "name": "good_method",
      "params": ["count"],
      "script": "\t# implement your method here\n\tmessage = 'good data: %s' % (count)\n\tsystem.perspective.print(message)"
    }
  ]
}
```

These all run through pylint without raising a finding under the default category mapping.

### Problematic code

A real event handler from `tests/cases/PylintViolations/view.json` that triggers several different categories at once:

```json
{
  "events": {
    "component": {
      "onActionPerformed": {
        "config": {
          "script": "\t# This script has multiple pylint violations\n\timport json\n\timport sys\n\t\n\t# E0602: Undefined variable\n\tprint(undefined_variable)\n\t\n\t# W0611: Unused import (json, sys above)\n\t# E1101: No member error\n\tresult = some_object.nonexistent_method()\n\t\n\t# C0114: Missing docstring\n\tdef helper_function():\n\t\tpass"
        },
        "scope": "G",
        "type": "script"
      }
    }
  }
}
```

The same fixture also contains a custom method with a fatal-level finding:

```json
{
  "customMethods": [
    {
      "name": "custom_method_with_errors",
      "params": [],
      "script": "\t# Custom method with fatal error\n\t# F0401: Unable to import\n\timport nonexistent_module\n\t\n\t# R0913: Too many arguments (simulated)\n\tdef complex_function(a, b, c, d, e, f, g):\n\t\treturn a + b + c"
    }
  ]
}
```

And a transform with both an unused import and an undefined variable:

```json
{
  "transforms": [
    {
      "code": "\t# Transform with violations\n\timport os\n\timport datetime\n\t\n\t# W0611: Unused imports\n\t# E0602: Undefined variable\n\tvalue = value + missing_var\n\t\n\treturn value",
      "type": "script"
    }
  ]
}
```

When linted under the default `category_mapping`, those scripts produce category-grouped output along these lines:

```
    Pylint - Fatal (F):
      • root.SubmitButton.custom_method_with_errors: Line 3: Unable to import 'nonexistent_module' (F0401)

    Pylint - Error (E):
      • root.SubmitButton.onActionPerformed: Line 7: Undefined variable 'undefined_variable' (E0602)
      • root.SubmitButton.onActionPerformed: Line 11: Instance of 'some_object' has no 'nonexistent_method' member (E1101)
      • root.custom.status.transforms[0]: Line 7: Undefined variable 'missing_var' (E0602)

    Pylint - Warning (W):
      • root.SubmitButton.onActionPerformed: Line 2: Unused import json (W0611)
      • root.SubmitButton.onActionPerformed: Line 3: Unused import sys (W0611)
      • root.custom.status.transforms[0]: Line 2: Unused import os (W0611)
      • root.custom.status.transforms[0]: Line 3: Unused import datetime (W0611)
```

Fatal (`F`) and Error (`E`) blocks are routed to the errors stream and fail the run; Warning (`W`), Convention (`C`), and Refactor (`R`) blocks are routed to the warnings stream and do not fail by default.

## Auto-fix support
PylintScriptRule inherits `FixableMixin` and provides one auto-fix: it strips trailing whitespace (pylint code `C0303`) from script content. The fix is marked safe (`is_safe=True`), so it is applied under the default `--fix` policy that only applies safe fixes.

Implementation details, all verifiable in `_generate_trailing_whitespace_fixes`:

- One `Fix` is produced **per script** that has any `C0303` finding, not one per offending line. So a script with three trailing-whitespace lines yields one fix containing one `SET_VALUE` operation that rewrites the entire script body.
- The `SET_VALUE` operation's `old_value` is the original script string and `new_value` is `'\n'.join(line.rstrip() for line in old.split('\n'))`.
- Fixes are only generated when fix mode is active (i.e. `set_fix_context` has been called by the engine and `has_fix_context` is `True`). They are also skipped in `batch_mode`, because batch mode does not retain enough per-file context to produce per-file fixes safely.
- After applying the fix and re-linting, no `C0303` violations remain (verified end-to-end in `test_pylint_trailing_whitespace_fix.py::TestFixApplicationEndToEnd`).

No other pylint finding has an auto-fix: pylint reports symptoms, but the safe rewrite of (for example) "remove unused import" or "rename invalid identifier" requires more context than the rule has, so those are surfaced as violations only.

## Output format
PylintScriptRule overrides `format_violations_grouped` so output is grouped by pylint category and routed to the appropriate severity stream. The shape is:

```
    Pylint - Fatal (F):
      • <script path>: Line <N>: <pylint message> (<code>)

    Pylint - Error (E):
      • <script path>: Line <N>: <pylint message> (<code>)

    Pylint - Warning (W):
      • <script path>: Line <N>: <pylint message> (<code>)

    Pylint - Convention (C):
      • <script path>: Line <N>: <pylint message> (<code>)

    Pylint - Refactor (R):
      • <script path>: Line <N>: <pylint message> (<code>)
```

Categories always render in `F, E, W, C, R` order, regardless of the order pylint emits them. Categories with no findings are omitted. Each category block is appended to either the errors stream or the warnings stream according to `category_mapping[<category>]`, so a strict-mode configuration sends every block to errors while the default mode splits them.

In non-batch mode, the script path printed in each line is just the script's model path (e.g. `root.SubmitButton.onActionPerformed`). In batch mode, the path is the full composite key `<file_path>::<script_path>`, so findings remain attributable across many input files.

## Debug output
Debug files are saved in two situations:

- **Always when violations are found.** After pylint runs, if any script has at least one finding, the combined temp file is copied to the debug directory before being deleted. The original temp filename — including timestamp and PID — is preserved so concurrent runs do not overwrite each other's output. The console message is `Pylint found issues. Debug file saved to: <path>`.
- **Always when `debug=true`.** With `debug=true`, the combined script is copied to the debug directory even on a clean run, and a sibling `pylintrc_used.txt` is written that records which pylintrc the rule resolved (or that no pylintrc was found and inline config was used). The console message is `Debug mode: Script saved to: <path>`.

The debug directory is determined by `_get_debug_directory` in this order:

1. `debug_dir` config option (absolute or resolved against cwd).
2. The first ancestor of cwd named `tests/`, joined with `debug` — i.e. when running tests, debug output goes to `tests/debug/`.
3. If a `tests/` directory exists somewhere above cwd, `<that ancestor>/tests/debug` is used.
4. Otherwise `.ignition-lint/debug` under cwd is used.

The debug directory is cleaned at the start of each run: any leftover `*.py` files and `pylintrc_used.txt` from previous runs are deleted before this run writes new files. Cleanup is best-effort and never fails the run.

## Edge cases & exemptions
- **Scripts that lack indentation in `view.json`** are flagged as a data quality issue with the message `Script lacks proper indentation in view.json (scripts should be indented with tabs or spaces for valid Python syntax)`. This is independent of any pylint finding — it is added before pylint runs.
- **Scripts that mix tabs and spaces in indentation** are flagged with `Script mixes tabs and spaces for indentation. Use either tabs OR spaces consistently.` Detection scans every line's leading whitespace; the violation is emitted once per script even if multiple lines mix.
- **Empty scripts are skipped entirely.** If `scripts` is empty or every script has only whitespace content, the rule short-circuits before invoking pylint.
- **The temp file injects stub globals** (`system = None`, `self = {}`, `event = {}`) so the Ignition built-ins do not trigger `undefined-variable` (`E0602`) findings. Anything else referenced in the script body that pylint cannot resolve is reported normally.
- **The `# pylint: disable=unused-argument,missing-docstring,redefined-outer-name,function-redefined` directive is automatically prepended** to the combined file. `function-redefined` is included specifically because multiple scripts may define functions with the same name (e.g. two custom methods both called `helper`), and that collision is an artifact of the bundling, not of the source view.
- **Comment-only first lines do not trigger the unindented-script check.** The rule walks past `#`-prefixed lines until it finds the first real code line and uses that for the indentation determination.
- **Composite keys** (`<file>::<path>`) are stripped to just the script path in non-batch mode for readability and preserved in full in batch mode for cross-file traceability.
- **The temp file is always cleaned up.** Whether or not findings were produced and whether or not a debug copy was saved, the original temp file in `/tmp/` is unlinked on exit.

## See also
- [PylintScriptRule user guide](../../rules/scripts/pylint-script.md) — the short version
- [Configuration overview](../../getting-started/configuration.md)
- [Debug output guide](../../usage/debug-output.md)
