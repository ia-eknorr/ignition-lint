---
title: Installation
sidebar_label: Installation
description: Install ignition-lint via pip or set up a Poetry development environment
---

# Installation

Two install paths: install the published package for use, or set up a Poetry workspace for local development on the framework itself.

## Prerequisites

- **Python 3.10 or higher**
- **Poetry ≥ 2.0** (only for development setup) — see [python-poetry.org](https://python-poetry.org/docs/#installation)

## Install from PyPI (recommended)

```bash
pip install ignition-lint
```

Verify:

```bash
ignition-lint --help
```

## Development setup with Poetry

Use this path if you're contributing to the framework or writing custom rules against the source.

```bash
git clone https://github.com/design-group/ignition-lint.git
cd ignition-lint
poetry install
```

Run the CLI through Poetry:

```bash
poetry run ignition-lint --help

# Or activate the virtualenv first
poetry shell
ignition-lint --help
```

Run the test suite:

```bash
cd tests
poetry run python test_runner.py --run-all
```

Format and lint the framework code:

```bash
poetry run yapf -ir --style=.config/.style.yapf src/ tests/
poetry run pylint src/ tests/ scripts/ --rcfile=.config/.pylintrc
```

## Building and distribution

```bash
# Build the package
poetry build

# Export requirements.txt for CI/CD or Docker
poetry export --output requirements.txt --without-hashes
```

## Next

- [Quick start](./quick-start.md) — run ignition-lint against a view file
- [Configuration](./configuration.md) — set up a `rule_config.json`
