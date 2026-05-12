# Ignition Lint

Static analysis for Ignition Perspective `view.json` files. Catches naming inconsistencies, performance problems, broken component references, dead custom properties, and Python errors in embedded scripts — before they hit the gateway.

## Why

Perspective views are JSON-encoded UI definitions with embedded Python scripts. There's no compiler, no IDE checker, no type system. A typo in an event handler, a `now()` polling interval that hammers the gateway, or a custom property nobody references will survive happily in source control until somebody hits the bad path in production.

Ignition Lint runs at design time. It builds an object model of every component, binding, and script in your views, then checks it against a configurable set of rules. Plug it into pre-commit to gate developers, into CI to gate pull requests, or run it standalone to audit an existing project.

## Quick start

```bash
pip install ign-lint
ign-lint path/to/view.json
```

To lint many views with a project-wide config:

```bash
ign-lint --config rule_config.json --files "views/**/view.json"
```

## Built-in rules

| Rule | What it catches |
| --- | --- |
| `NamePatternRule` | Component, property, and script names that don't match a configured convention |
| `BadComponentReferenceRule` | Brittle traversal patterns (`.getSibling()`, `.getParent()`, relative paths) |
| `ComponentReferenceValidationRule` | Relative references that don't resolve to a real component |
| `PollingIntervalRule` | `now()` polling intervals below a configurable minimum |
| `UnusedCustomPropertiesRule` | Custom properties and view parameters defined but never referenced |
| `ExcessiveContextDataRule` | Large datasets stored in custom properties (arrays, breadth, depth, total volume) |
| `PylintScriptRule` | Pylint findings across every script in the view |

Every rule is configurable. Severity is per-rule (error or warning). Several rules support auto-fix.

## Documentation

The full documentation covers configuration, every rule (user guide plus full technical reference), pre-commit and GitHub Actions integration, debug output, and the framework internals for writing custom rules.

**Read the docs:** [bw-design-group.github.io/ignition-lint](https://bw-design-group.github.io/ignition-lint/)

Highlights:

- **Tutorial** — first-run walkthrough on a real view, reading the output, and configuring a rule
- **Per-rule pages** — common configurations, examples drawn from real fixtures, and what each rule's auto-fix does
- **Developer guide** — the visitor pattern, base classes, registry API, and a step-by-step for writing your own rule

## Project status

The package publishes to PyPI as [`ign-lint`](https://pypi.org/project/ign-lint/). Release history lives in [CHANGELOG.md](CHANGELOG.md) (and is mirrored in the docs site). Release process is documented in [RELEASING.md](RELEASING.md).

## License

MIT — see [LICENSE](LICENSE).
