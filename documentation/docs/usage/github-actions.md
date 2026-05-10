---
title: GitHub Actions
sidebar_label: GitHub Actions
description: Run ignition-lint in GitHub Actions and test workflows locally with act
---

# GitHub Actions

Run ignition-lint in CI to catch rule violations on every push and pull request. The setup mirrors pre-commit but runs server-side, so it cannot be bypassed with `--no-verify`.

## Quick start

Create `.github/workflows/ignition-lint.yml`:

```yaml
name: Ignition Lint

on:
  push:
    paths:
      - '**/*.json'
  pull_request:
    paths:
      - '**/*.json'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install ignition-lint
        run: pip install ign-lint

      - name: Lint views
        run: ign-lint --config rule_config.json --files "views/**/view.json"
```

The job fails (exit 1) if any error-severity violation is found. Warnings exit 0, so warnings appear in logs but don't fail the build unless you escalate them.

## Using the bundled action

Ignition Lint also ships as a composite GitHub Action — use it directly without installing the package:

```yaml
- name: Lint Ignition view files
  uses: bw-design-group/ignition-lint@v0.2.4
  with:
    files: "**/view.json"
    config: "rule_config.json"
    verbose: "false"
```

## Failing on warnings

By default, only errors fail the build. To fail on warnings too:

```yaml
- name: Lint views
  run: ign-lint --config rule_config.json --files "**/view.json"
```

Warnings already block in this configuration. Pre-commit's `--ignore-warnings` is the opposite — it relaxes the default. CI typically runs without `--ignore-warnings` so warnings still fail.

## Running multiple configurations

A common pattern is to lint different directories with different configs:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        config:
          - {dir: "views/legacy", config: "legacy-config.json"}
          - {dir: "views/modern", config: "rule_config.json"}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ign-lint
      - run: ign-lint --config ${{ matrix.config.config }} --files "${{ matrix.config.dir }}/**/view.json"
```

## Annotating PRs with violations

Use the [`reviewdog/action-suggester`](https://github.com/reviewdog/action-suggester) or pipe results to `::error::` and `::warning::` log commands. A minimal example:

```yaml
- name: Lint views
  id: lint
  run: |
    ign-lint --config rule_config.json --files "**/view.json" \
      --results-output results.txt || echo "violations found"

- name: Annotate
  if: always()
  run: |
    while IFS= read -r line; do
      echo "::error file=${line%%:*}::${line#*:}"
    done < results.txt
```

(Format depends on `--results-output` — see [Command line](./cli.md).)

## Testing workflows locally with `act`

Run GitHub Actions on your machine with [`nektos/act`](https://github.com/nektos/act). The repo includes scripts to make this easier.

### Setup

```bash
# Install act
curl -q https://raw.githubusercontent.com/nektos/act/master/install.sh | bash

# Validate setup
scripts/validate-local-actions.sh
```

### Run a workflow

```bash
# All workflows (push event)
scripts/test-actions.sh

# Specific workflow
scripts/test-actions.sh ci
scripts/test-actions.sh unittest

# With a specific event
scripts/test-actions.sh unittest pull_request

# List available workflows
scripts/test-actions.sh list
```

### Available workflows

| Workflow | File | Purpose |
| --- | --- | --- |
| `ci` | `.github/workflows/ci.yml` | Full CI pipeline with multi-Python testing |
| `unittest` | `.github/workflows/unittest.yml` | Unit tests only |
| `integration-test` | `.github/workflows/integration-test.yml` | Integration tests |
| `example-ci` | `.github/workflows/example-ci.yaml` | Example CI with pre-commit hooks |

### Apple Silicon

If `act` errors out with image-architecture issues:

```bash
act --container-architecture linux/amd64
```

Or add to `.actrc`:

```
--container-architecture linux/amd64
```

### Debugging act runs

```bash
# Verbose output
act --verbose

# Specific job within a workflow
act -j test

# Dry run (parse only)
act --dry-run

# Validate workflow syntax
act --dry-run -W .github/workflows/ci.yml
```

## Caching pip installs

Speed up CI by caching pip:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'

- run: pip install ign-lint
```

## Common patterns

### Fail-fast on PRs, advisory on push

```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    continue-on-error: ${{ github.event_name == 'push' }}
    steps:
      # ...
```

### Lint changed files only

```yaml
- name: Get changed view files
  id: changed
  uses: tj-actions/changed-files@v44
  with:
    files: '**/view.json'

- name: Lint changed files
  if: steps.changed.outputs.any_changed == 'true'
  run: ign-lint --config rule_config.json ${{ steps.changed.outputs.all_changed_files }}
```

## See also

- [Command line](./cli.md) — flags the workflow can pass
- [Pre-commit](./pre-commit.md) — pre-commit counterpart to CI
- [Whitelist](./whitelist.md) — exempt files from linting
