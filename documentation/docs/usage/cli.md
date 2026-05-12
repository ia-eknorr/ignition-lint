---
title: Command line
sidebar_label: Command line
description: Full CLI reference for ignition-lint
---

# Command line

Complete reference for the `ign-lint` CLI. The CLI is the primary interface — every other integration (pre-commit, GitHub Actions, custom scripts) wraps it.

## Synopsis

```bash
ign-lint [<files>...] [--files <pattern>...] [options]
```

## Common invocations

```bash
# Single file
ign-lint path/to/view.json

# Glob pattern (quote it!)
ign-lint --files "**/view.json"

# Multiple patterns
ign-lint --files "views/**/view.json" --files "components/**/view.json"

# With config
ign-lint --config rule_config.json --files "**/view.json"

# Verbose, with timing
ign-lint --config rule_config.json --files "**/view.json" --verbose
```

## Options

### Files and configuration

| Flag | Description |
| --- | --- |
| `--files <pattern>` | Glob pattern of view files to lint. Repeatable. |
| `--config <path>` | Path to a `rule_config.json`. If omitted, every registered rule runs with defaults. |

### Whitelist

Whitelisting lets you exclude specific files from linting — useful for legacy code. By default ignition-lint does NOT use a whitelist.

| Flag | Description |
| --- | --- |
| `--whitelist <path>` | Path to a whitelist file (typically `.whitelist.txt`) |
| `--no-whitelist` | Disable whitelist (overrides `--whitelist`) |
| `--generate-whitelist <pattern>...` | Generate a whitelist file from glob patterns |
| `--whitelist-output <path>` | Output file for `--generate-whitelist` (default: `.whitelist.txt`) |
| `--append` | Append to existing whitelist (use with `--generate-whitelist`) |
| `--dry-run` | Preview without writing (use with `--generate-whitelist`) |

See [Whitelist guide](./whitelist.md) for details.

### Output and severity

| Flag | Description |
| --- | --- |
| `--verbose` | Print per-file timing, ignored-file lists, rule coverage |
| `--ignore-warnings` | Exit zero even if warnings are present (errors still fail) |
| `--warnings-only` | Run rules but only report warnings (suppress errors) |
| `--timing-output <path>` | Write per-file timing to a file |
| `--results-output <path>` | Write a structured results report to a file |

### Analysis and debugging

| Flag | Description |
| --- | --- |
| `--stats-only` | Skip rule execution; print model statistics only |
| `--debug-nodes <type>...` | Print all nodes of the given type(s) — `component`, `expression_binding`, `property`, etc. |
| `--analyze-rules` | Print which rules visited which node types and how many violations each produced |
| `--debug-output <dir>` | Write debug artifacts (flattened JSON, model dump) to the directory |

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No errors (warnings may still be present) |
| 1 | One or more error-severity violations |
| 2 | Configuration or file-loading failure |

`--ignore-warnings` doesn't change exit codes — warnings already exit 0 by default. `--warnings-only` suppresses errors entirely so the run always exits 0.

## Reading the output

A typical violation report:

```
Found 2 errors in views/dashboard/view.json:
  PollingIntervalRule (error):
    • root.Container.props.text.binding: 'now(5000)'

  NamePatternRule (warning):
    • root.Container.children[0].my_button: Name 'my_button' doesn't follow PascalCase for component (suggestion: 'MyButton')

Summary:
  Total issues: 2
```

Each violation includes the JSON path inside the view, the rule name, the severity, and the message. For pylint-detected issues the format is grouped by category — see [PylintScriptRule](../rules/scripts/pylint-script.md).

## Patterns and globbing

`--files` patterns are matched by ignition-lint's internal globber, not the shell. **Quote your patterns** to prevent shell expansion:

```bash
# Right
ign-lint --files "**/view.json"

# Wrong (shell expands first; long arg lists may exceed ARG_MAX)
ign-lint --files **/view.json
```

For very large repositories (hundreds of view files), use the CLI's globbing rather than shelling out `find ... -exec`. Some pre-commit configurations pass every matched file as an arg, which can exceed system `ARG_MAX` limits — the CLI's internal globbing avoids this.

## Stats-only mode

`--stats-only` builds the model but skips rule execution. Useful for:

- Auditing what's in a view (component count, binding count, script count)
- Sanity-checking a view loads correctly
- Profiling model-build performance separately from rule execution

```bash
ign-lint --files "**/view.json" --stats-only --verbose
```

## Rule analysis mode

`--analyze-rules` reports which rules ran, what node types they visited, and how many violations each produced. Useful when:

- Onboarding a new rule and you want to confirm it's actually executing
- Debugging unexpected behavior — does the rule see the nodes it expects?
- Auditing CI cost — which rules dominate runtime?

```bash
ign-lint --config rule_config.json --files "**/view.json" --analyze-rules
```

## Debug-nodes mode

`--debug-nodes` dumps every node of the given type(s) the framework discovered:

```bash
ign-lint --files path/to/view.json --debug-nodes component expression_binding
```

Useful when developing a rule — see exactly what your visit method will receive.

## Combining modes

Modes compose. A representative debugging session:

```bash
ign-lint \
  --config rule_config.json \
  --files "views/Dashboard/view.json" \
  --verbose \
  --debug-output ./analysis \
  --analyze-rules
```

## See also

- [Configuration](../getting-started/configuration.md) — full `rule_config.json` schema
- [Pre-commit](./pre-commit.md) — wrap the CLI in a git hook
- [GitHub Actions](./github-actions.md) — wrap it in CI
- [Whitelist](./whitelist.md) — exempt files
- [Debug output](./debug-output.md) — generate model dumps and golden files
