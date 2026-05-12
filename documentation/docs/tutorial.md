---
title: Tutorial
sidebar_label: Tutorial
sidebar_position: 2
description: Walk through your first ignition-lint run on a real Perspective view
---

# Tutorial

This tutorial walks you through your first ignition-lint run, from a fresh install to fixing your first violations. It assumes no prior knowledge of the framework — it's the equivalent of skipping the manual and jumping in.

By the end you will have:

- Installed ignition-lint
- Run it on a sample Perspective view
- Read and understood the violation output
- Looked up a rule in the docs
- Configured a rule and re-run

## Install

If you haven't already, install ignition-lint from PyPI:

```bash
pip install ign-lint
```

Verify it's available:

```bash
ign-lint --help
```

You should see a usage banner listing the supported arguments. The ones we'll use in this tutorial are:

| Argument | Purpose |
| --- | --- |
| `<file>` (positional) | Lint a single view.json |
| `--files <pattern>` | Lint every file matching a glob |
| `--config <path>` | Use a `rule_config.json` |
| `--verbose` | Print per-rule timing and discovery info |

For a full reference of the CLI, see the [command line guide](./usage/cli.md).

## Get a sample view

Save the following as `dashboard.json`. It's a deliberately small Perspective view with a couple of intentional problems — perfect for the tutorial.

```json
{
  "root": {
    "type": "ia.container.flex",
    "meta": { "name": "root" },
    "props": {},
    "children": [
      {
        "type": "ia.input.button",
        "meta": { "name": "my_button" },
        "props": { "text": "Refresh" },
        "events": {
          "component": {
            "onActionPerformed": {
              "type": "script",
              "script": "self.getSibling('my_button').props.text = 'clicked'",
              "scope": "G"
            }
          }
        }
      },
      {
        "type": "ia.display.label",
        "meta": { "name": "TimeLabel" },
        "propConfig": {
          "props.text": {
            "binding": {
              "type": "expr",
              "config": { "expression": "now(5000)" }
            }
          }
        }
      }
    ]
  },
  "custom": {
    "unusedSetting": "neverReferenced"
  }
}
```

The view has:

- A button named `my_button` (lowercase + underscore — not PascalCase)
- A script using `self.getSibling()` (a brittle traversal pattern)
- A label binding `now(5000)` (5-second polling, below the default 10-second minimum)
- A custom property `unusedSetting` that is never referenced

That's four problems across four different rules. Let's see ignition-lint find them.

## Run ign-lint

In the same directory as `dashboard.json`, run:

```bash
ign-lint dashboard.json
```

With no `--config` flag, every registered rule runs with its default settings. You should see output similar to:

```
Found 5 issues in dashboard.json:

  NamePatternRule (warning):
    • root.children[0].meta.name: Name 'my_button' doesn't follow PascalCase for component (suggestion: 'MyButton')

  BadComponentReferenceRule (error):
    • root.children[0].events.component.onActionPerformed: Script contains '.getSibling(' which creates brittle view structure dependencies. Consider using view.custom properties or message handling for component communication instead.

  ComponentReferenceValidationRule (error):
    • root.children[0].events.component.onActionPerformed: Script references non-existent sibling component 'my_button'

  PollingIntervalRule (error):
    • root.children[1].propConfig.props.text.binding: 'now(5000)'

  UnusedCustomPropertiesRule (error):
    • custom.unusedSetting: custom property 'unusedSetting' is defined but never referenced

Summary: 4 errors, 1 warning
```

ign-lint exits with code 1 because there are error-severity violations. Warnings on their own would still exit 0 unless you enable strict-warning mode.

## Anatomy of a violation

Every violation line follows the same shape:

```
<JSON path>: <human-readable message>
```

Pick the first violation:

```
root.children[0].meta.name: Name 'my_button' doesn't follow PascalCase for component (suggestion: 'MyButton')
```

This tells you four things:

| Part | Value |
| --- | --- |
| Path | `root.children[0].meta.name` |
| Rule that fired | `NamePatternRule` (from the section header above the bullet) |
| Severity | `warning` (also in the section header) |
| What to do | Rename to `MyButton` (the suggestion in parentheses) |

The path uses bracket notation for array indices and dot notation for object keys, exactly as it appears when the framework flattens the view JSON.

## Look up a rule

When you see a rule name you don't recognize, the docs have a dedicated page for each one. The structure is:

- **User guide** (short) — under **Rules** in the sidebar, organized by category
- **Full reference** (deep) — at [Rule Reference → \<category> → \<rule>](./reference/naming/name-pattern.md)

For example, `NamePatternRule` is documented at [Rules → Naming → NamePatternRule](./rules/naming/name-pattern.md). Open it now and skim. You'll see the basic config, common configurations, and a link to the full reference for every option.

The user-guide page covers the 80% case. The reference page covers everything.

## Fix one violation

Edit `dashboard.json` and rename the button:

```diff
-        "meta": { "name": "my_button" },
+        "meta": { "name": "RefreshButton" },
```

Also update the script that referenced it (this would otherwise still target `my_button`):

```diff
-              "script": "self.getSibling('my_button').props.text = 'clicked'",
+              "script": "self.getSibling('RefreshButton').props.text = 'clicked'",
```

Run again:

```bash
ign-lint dashboard.json
```

```
Found 4 issues in dashboard.json:

  BadComponentReferenceRule (error):
    • root.children[0].events.component.onActionPerformed: Script contains '.getSibling(' …

  ComponentReferenceValidationRule (error):
    • root.children[0].events.component.onActionPerformed: Script references non-existent sibling component 'RefreshButton'

  PollingIntervalRule (error):
    • root.children[1].propConfig.props.text.binding: 'now(5000)'

  UnusedCustomPropertiesRule (error):
    • custom.unusedSetting: custom property 'unusedSetting' is defined but never referenced
```

The naming warning is gone. The structure violations remain because we didn't add a sibling component named `RefreshButton` — the script still references something that doesn't exist. That's `ComponentReferenceValidationRule` working: it caught a real bug. (We won't fix that one in this tutorial — just notice that it's there.)

## Configure a rule

Suppose your team uses `camelCase` for component names instead of `PascalCase`. You configure ignition-lint with a `rule_config.json` file. Save the following alongside `dashboard.json`:

```json
{
  "NamePatternRule": {
    "kwargs": {
      "convention": "camelCase"
    }
  }
}
```

Now rerun, pointing at the config:

```bash
ign-lint --config rule_config.json dashboard.json
```

The naming rule now expects camelCase. Other rules continue to run with their defaults — they will be activated even though they aren't listed in the config, because the config is an override layer rather than an allowlist.

To **disable** a rule entirely, add `"enabled": false`:

```json
{
  "PollingIntervalRule": {
    "enabled": false
  }
}
```

For the full configuration schema, see the [configuration guide](./getting-started/configuration.md).

## Lint many files at once

Real projects have many views. The `--files` flag accepts a glob pattern:

```bash
ign-lint --config rule_config.json --files "views/**/view.json"
```

Quote the pattern. ignition-lint expands the glob internally rather than relying on the shell, which keeps very large projects from hitting `ARG_MAX` limits.

## Where to go next

You've now run ignition-lint, read its output, looked up a rule, and configured one. From here:

- **Adopting on an existing repo?** Read the [whitelist guide](./usage/whitelist.md) — it lets you exempt legacy files while still gating new code.
- **Want this in CI?** See [GitHub Actions](./usage/github-actions.md).
- **Want pre-commit gating?** See [pre-commit](./usage/pre-commit.md).
- **Want to write a custom rule?** Start with [Architecture](./developing/architecture.md), then [Creating rules](./developing/creating-rules.md).
- **Want to see every built-in rule?** Open the **Rules** section in the sidebar.
