---
title: Pre-commit integration
sidebar_label: Pre-commit
description: Run ignition-lint as a git pre-commit hook
---

# Pre-commit integration

Pre-commit blocks commits that introduce rule violations. Ignition Lint provides a pre-commit-compatible hook out of the box; you choose between two install modes.

## Option A: Remote repository (recommended)

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/bw-design-group/ignition-lint
    rev: v0.2.4  # use the latest release tag
    hooks:
      - id: ign-lint
```

Install hooks:

```bash
pre-commit install
```

The hook automatically runs on `view.json` files. It uses ignition-lint's bundled `.ignition-lint-precommit.json` (warnings-favored config) by default.

**Pros:** zero setup, version-pinned via `rev:`, consistent across the team
**Cons:** clones the full repo (~64 MB) into the pre-commit cache

## Option B: Lightweight install (~1 MB)

Install only the Python package — no test fixtures, docker files, or docs in the cache:

```yaml
repos:
  - repo: local
    hooks:
      - id: ign-lint
        name: Ignition Lint
        entry: ign-lint
        language: python
        types: [json]
        files: view\.json$
        args: ['--config=rule_config.json', '--files']
        pass_filenames: true
        additional_dependencies:
          - 'git+https://github.com/bw-design-group/ignition-lint@v0.2.4'
```

**Pros:** ~1 MB cache footprint
**Cons:** more YAML to maintain

## Custom configuration

Both options accept a custom `rule_config.json`:

```yaml
repos:
  - repo: https://github.com/bw-design-group/ignition-lint
    rev: v0.2.4
    hooks:
      - id: ign-lint
        args: ['--config=rule_config.json', '--files']
```

A common pattern is one config for pre-commit (warnings-favored, fast) and a separate one for CI (strict, full):

```
project/
├── .pre-commit-config.yaml         # references pre-commit-config.json
├── pre-commit-config.json          # warning severity, lighter rule set
└── rule_config.json                # full strictness, used in CI
```

## Warnings vs errors

Default behavior: both warnings and errors block commits.

To allow commits with warnings (block only on errors):

```yaml
hooks:
  - id: ign-lint
    args: ['--config=rule_config.json', '--files', '--ignore-warnings']
```

This is useful when rolling out a new rule — set it to warning, let teams adapt, then promote to error.

## Whitelist for legacy code

Pair pre-commit with a whitelist to exempt legacy files:

```yaml
hooks:
  - id: ign-lint
    args:
      - '--config=rule_config.json'
      - '--whitelist=.whitelist.txt'
      - '--files'
```

Generate the whitelist once and commit it:

```bash
ign-lint --generate-whitelist "views/legacy/**/*.json"
git add .whitelist.txt
git commit -m "Add whitelist for legacy views (technical debt)"
```

See [Whitelist guide](./whitelist.md) for full details.

## Excluding test files

Test fixtures often contain intentional violations. Exclude them:

```yaml
hooks:
  - id: ign-lint
    exclude: '^tests/.*|.*test.*\.json$'
```

## Running manually

```bash
# Install hooks (one-time)
pre-commit install

# Run on all files (full repository scan)
pre-commit run --all-files

# Run on staged files only (default behavior)
pre-commit run

# Run only the ignition-lint hook
pre-commit run ign-lint

# Run on specific files
pre-commit run ign-lint --files path/to/view.json
```

### Caveat: `--all-files` on large repositories

`pre-commit run --all-files` passes every matched file as a CLI argument. With hundreds of view files and long paths, this can exceed `ARG_MAX` on some systems. For full-repository scans, invoke ignition-lint directly:

```bash
ign-lint --files "views/**/view.json" --config rule_config.json
```

The CLI's internal globber sidesteps the argv limit entirely.

## Skipping the hook (one-off)

Sometimes you need to commit despite a known issue:

```bash
git commit --no-verify
```

Use sparingly — `--no-verify` skips ALL pre-commit hooks, not just ignition-lint.

## Setting up a custom configuration

Sample `pre-commit-config.json` favoring warnings:

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "convention": "PascalCase",
      "severity": "warning"
    }
  },
  "PollingIntervalRule": {
    "enabled": true,
    "kwargs": {
      "minimum_interval": 5000
    }
  },
  "PylintScriptRule": {
    "enabled": true,
    "kwargs": {
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

## See also

- [Command line](./cli.md) — every flag the hook can pass
- [Configuration](../getting-started/configuration.md) — full schema
- [Whitelist](./whitelist.md) — manage technical debt
- [GitHub Actions](./github-actions.md) — CI counterpart to pre-commit
