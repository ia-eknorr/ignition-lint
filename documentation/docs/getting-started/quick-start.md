---
title: Quick start
sidebar_label: Quick start
description: Run ignition-lint against a view.json file with a minimal configuration
---

# Quick start

After [installing](./installation.md), the fastest way to get a feel for ignition-lint is to point it at a view file with the default rule set.

## Lint a single file

```bash
ign-lint path/to/view.json
```

With no `--config` flag, the tool runs every registered rule with default options.

## Lint many files

```bash
ign-lint --files "**/view.json"
```

The `--files` flag accepts glob patterns. Quote the pattern so the shell doesn't expand it before ignition-lint sees it.

## Use a configuration file

Create `rule_config.json` in your project root:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "convention": "PascalCase",
      "target_node_types": ["component"]
    }
  },
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 10000
    }
  },
  "PylintScriptRule": {
    "enabled": true
  }
}
```

Run with the config:

```bash
ign-lint --config rule_config.json --files "**/view.json"
```

See [Configuration](./configuration.md) for the full schema.

## Verbose mode

`--verbose` adds per-file timing, ignored-file lists, and rule-coverage statistics:

```bash
ign-lint --config rule_config.json --files "**/view.json" --verbose
```

## Stats only (no rules)

`--stats-only` skips rule execution and just prints model statistics — useful when developing rules or auditing what's in a view:

```bash
ign-lint --files "**/view.json" --stats-only
```

## Output

A typical successful run with no violations exits 0 and prints:

```
No issues found
```

Violations look like this (warnings exit 0 by default; errors exit 1):

```
Found 2 errors in views/dashboard/view.json:
  PollingIntervalRule (error):
    • root.Container.props.text.binding: 'now(5000)'

  NamePatternRule (warning):
    • root.Container.children[0].my_button: Name 'my_button' doesn't follow PascalCase for component (suggestion: 'MyButton')

Summary:
  Total issues: 2
```

## Next

- [Configuration](./configuration.md) — full rule and severity reference
- [Pre-commit integration](../usage/pre-commit.md) — block bad views at commit time
- [GitHub Actions](../usage/github-actions.md) — fail CI on rule violations
