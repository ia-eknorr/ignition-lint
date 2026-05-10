---
title: Configuration
sidebar_label: Configuration
description: Configure rules, severity, and node-type targeting
---

# Configuration

Rules are configured through a JSON file (default name: `rule_config.json`). Each top-level key is a rule class name; the value is an object with `enabled` and `kwargs`.

## Schema

```json
{
  "<RuleName>": {
    "enabled": true,
    "kwargs": {
      "<option>": <value>
    }
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `enabled` | bool | Yes | Whether to run the rule |
| `kwargs` | object | No | Keyword arguments forwarded to the rule's `__init__` |

Anything inside `kwargs` is passed straight to the rule's constructor. See the per-rule pages under **Rules** in the sidebar for the options each rule accepts.

## Comments and metadata

Keys that start with `_` are stripped before instantiation. Use them for inline notes:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "_note": "Tightened from camelCase to PascalCase in Q1 2026 — see ADR-12",
    "kwargs": {
      "convention": "PascalCase"
    }
  }
}
```

## Severity model

Most rules accept a `severity` kwarg with values `"error"` or `"warning"`. The default is set per rule based on its impact:

| Default severity | Meaning |
| --- | --- |
| `"error"` | Functional or performance impact — exits non-zero by default |
| `"warning"` | Style or hygiene — exits zero unless `--ignore-warnings` is unset |

You can override severity per rule:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "convention": "PascalCase",
      "severity": "error"
    }
  }
}
```

`PylintScriptRule` is special — it uses a `category_mapping` dict that assigns severity per pylint category (`F`, `E`, `W`, `C`, `R`). See [PylintScriptRule](../rules/scripts/pylint-script.md) for details.

## Node-type targeting

Rules that visit multiple node types (e.g., `NamePatternRule`) accept a `target_node_types` list to restrict where they run:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "convention": "PascalCase",
      "target_node_types": ["component"],
      "node_type_specific_rules": {
        "custom_method": {
          "convention": "camelCase"
        }
      }
    }
  }
}
```

Available node types:

- `component`
- `property`
- `expression_binding`
- `property_binding`
- `tag_binding`
- `event_handler`
- `message_handler`
- `custom_method`
- `transform`

## Full example

A representative `rule_config.json` for a project that wants strict naming, performance enforcement, and pylint as warnings:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "convention": "PascalCase",
      "target_node_types": ["component"],
      "severity": "warning"
    }
  },
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 10000
    }
  },
  "BadComponentReferenceRule": {
    "enabled": true
  },
  "ComponentReferenceValidationRule": {
    "enabled": true
  },
  "UnusedCustomPropertiesRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning"
    }
  },
  "ExcessiveContextDataRule": {
    "enabled": true,
    "kwargs": {
      "max_array_size": 50,
      "max_data_points": 1000
    }
  },
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

## Disabling a rule

Set `enabled: false` (or omit the rule entirely):

```json
{
  "PylintScriptRule": {
    "enabled": false
  }
}
```

## Multiple configs per project

Pre-commit and CI typically use different configs — pre-commit favors warnings to keep commits flowing, CI escalates everything to errors. A common layout:

- `pre-commit-config.json` — warnings-only for fast feedback
- `rule_config.json` — full strictness for CI

Pass each via `--config`:

```bash
ignition-lint --config pre-commit-config.json --files "**/view.json"
ignition-lint --config rule_config.json --files "**/view.json"
```

## Next

- [Pre-commit integration](../usage/pre-commit.md) — typical pre-commit configuration
- [Whitelist](../usage/whitelist.md) — exempt specific files from linting
