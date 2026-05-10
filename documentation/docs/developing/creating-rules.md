---
title: Creating rules
sidebar_label: Creating rules
description: Build a custom linting rule from scratch
---

# Creating rules

This guide walks through building a custom rule end-to-end. Read [Architecture](./architecture.md) first if you haven't — the pipeline and visitor concepts here assume that background.

## The shortest possible rule

```python
# src/ignition_lint/rules/example/no_red_buttons.py
from .common import LintingRule
from .registry import register_rule
from ..model.node_types import ViewNode, NodeType


@register_rule
class NoRedButtonsRule(LintingRule):
    """Prevents components with name 'RedButton'."""

    def __init__(self, severity: str = "warning"):
        super().__init__({NodeType.COMPONENT}, severity)

    @property
    def error_message(self) -> str:
        return "Components named 'RedButton' are not allowed"

    def visit_component(self, node: ViewNode):
        if node.name == "RedButton":
            self.add_violation(f"{node.path}: rename to something more specific")
```

Drop this file under `src/ignition_lint/rules/`. The framework auto-discovers it; no other registration needed.

Use it:

```json
{
  "NoRedButtonsRule": {
    "enabled": true,
    "kwargs": {
      "severity": "warning"
    }
  }
}
```

That's the entire onboarding. Everything below is depth — patterns for richer rules.

## Anatomy of a rule

### 1. Imports

```python
from typing import Set
from .common import LintingRule, FixableMixin  # base classes
from .registry import register_rule
from ..model.node_types import ViewNode, NodeType, ALL_BINDINGS, ALL_SCRIPTS
```

Use **relative imports** within the rules package. Absolute imports (`from ignition_lint.rules.common import ...`) work at runtime but break auto-discovery in some test contexts.

### 2. Decorator

```python
@register_rule
class MyRule(LintingRule):
    ...
```

`@register_rule` adds the class to the global registry. Rules under `_examples/` are excluded from auto-discovery — use that subfolder for reference implementations you don't want loaded.

### 3. `__init__`

The constructor receives kwargs from `rule_config.json`. Provide defaults for everything so the rule is instantiable with no config:

```python
def __init__(self, min_length: int = 3, severity: str = "warning"):
    super().__init__({NodeType.COMPONENT}, severity)
    self.min_length = min_length
```

The framework calls `cls.create_from_config({})` during validation. If your `__init__` requires arguments without defaults, registration fails with `RuleValidationError`.

### 4. `error_message` (required)

```python
@property
def error_message(self) -> str:
    return "Description of what this rule checks"
```

This is a class contract — abstract in `LintingRule`. Forgetting it raises `RuleValidationError`. Used in CLI output and rule analysis reports.

### 5. Visit methods

Override only the visit methods for node types you care about:

```python
def visit_component(self, node: ViewNode):
    if condition:
        self.add_violation(f"{node.path}: detail")
```

Available visit methods are listed in [Architecture — Visit methods](./architecture.md#visit-methods).

### 6. Reporting violations

Use `add_violation()`:

```python
self.add_violation(f"{node.path}: too long ({len(node.name)} > {self.max_length})")
self.add_violation(f"{node.path}: warning level", severity="warning")  # override severity
```

Don't write to `self.errors` / `self.warnings` directly in new code — `add_violation` handles severity routing.

## Common patterns

### Per-node-type severity

Some rules want different severities for different node types (e.g., `error` on components, `warning` on properties). Look at [`NamePatternRule`](../rules/naming/name-pattern.md) for the canonical implementation — it uses a `node_type_specific_rules` dict and resolves severity per-visit.

### Cross-node analysis

Collect during `visit_*`, analyze in `post_process`:

```python
class CrossReferenceRule(LintingRule):
    def __init__(self):
        super().__init__({NodeType.COMPONENT, NodeType.PROPERTY_BINDING})
        self.component_paths: set[str] = set()
        self.binding_targets: list[tuple[str, str]] = []

    @property
    def error_message(self) -> str:
        return "Property bindings must target real components"

    def visit_component(self, node: ViewNode):
        self.component_paths.add(node.path)

    def visit_property_binding(self, node: ViewNode):
        self.binding_targets.append((node.path, node.target_path))

    def post_process(self):
        for binding_path, target_path in self.binding_targets:
            if target_path not in self.component_paths:
                self.add_violation(f"{binding_path}: target '{target_path}' not found")
```

[`ComponentReferenceValidationRule`](../rules/structure/component-reference-validation.md) is a production example of this pattern.

### Direct flattened-JSON access

Some rules can't be expressed via the model alone. The framework injects flattened JSON via `set_flattened_json` if your rule defines that method:

```python
class FlatJsonRule(LintingRule):
    def __init__(self):
        super().__init__(set())  # no node-type filter — we operate on JSON directly
        self.flattened_json = {}

    def set_flattened_json(self, flattened_json):
        self.flattened_json = flattened_json

    def process_nodes(self, nodes):
        # Override to bypass node iteration entirely
        self.errors = []
        for path in self.flattened_json:
            if path.startswith("custom.") and len(self.flattened_json[path]) > 1000:
                self.add_violation(f"{path}: value too long")
```

[`ExcessiveContextDataRule`](../rules/properties/excessive-context-data.md) and [`UnusedCustomPropertiesRule`](../rules/properties/unused-custom-properties.md) use this approach.

### Configuration preprocessing

When kwargs need type conversion (e.g., string node-type names → `NodeType` enum), implement `preprocess_config`:

```python
@classmethod
def preprocess_config(cls, config: dict) -> dict:
    processed = super().preprocess_config(config)  # strips _-prefixed keys
    if 'target_node_types' in processed:
        processed['target_node_types'] = {
            NodeType(s) for s in processed['target_node_types']
        }
    return processed
```

`NamePatternRule.preprocess_config` is the reference — it converts strings to enums, validates, and warns on bad values.

### Auto-fixes

Inherit `FixableMixin` alongside the rule base:

```python
from .common import LintingRule, FixableMixin
from ..common.fix_operations import Fix, FixOperation, FixOperationType


class MyFixableRule(FixableMixin, LintingRule):
    def __init__(self):
        super().__init__({NodeType.COMPONENT})

    @property
    def error_message(self) -> str:
        return "Components must not be named 'temp'"

    def visit_component(self, node):
        if node.name == "temp":
            violation = f"{node.path}: rename 'temp' to something specific"
            self.add_violation(violation)

            if self.has_fix_context:  # only when fix mode is active
                fix = Fix(
                    rule_name=self.error_key,
                    violation_message=violation,
                    description=f"Rename component 'temp' to 'TempComponent'",
                    operations=[
                        FixOperation(
                            operation=FixOperationType.SET_VALUE,
                            json_path=self._path_translator.get_component_name_path(node.path),
                            old_value="temp",
                            new_value="TempComponent",
                        )
                    ],
                    is_safe=True,
                )
                self.add_fix(fix)
```

[`NamePatternRule._generate_component_fix`](../reference/naming/name-pattern.md#auto-fix-support) shows the full unsafe-fix path including reference rewriting.

## Choosing the right base class

| Goal | Use |
| --- | --- |
| Generic rule | `LintingRule` |
| Operates only on bindings | `BindingRule` (defaults `target_node_types` to `ALL_BINDINGS`) |
| Operates only on scripts | `ScriptRule` (auto-collects scripts; override `process_scripts(self, scripts)`) |
| Provides auto-fixes | Add `FixableMixin` as the first parent: `class MyRule(FixableMixin, LintingRule):` |

`ScriptRule` is the most specialized — you implement `process_scripts(scripts: dict[str, ScriptNode])` instead of individual `visit_*` methods. The framework collects scripts across the whole view first, then hands them to you in one batch. This is what enables `PylintScriptRule` to run pylint once across the whole view rather than once per script.

## Where to put your rule

```
src/ignition_lint/rules/
├── naming/        ← naming-related rules
├── structure/     ← view-tree / component-relationship rules
├── performance/   ← performance-related rules
├── properties/    ← property hygiene rules
├── scripts/       ← script analysis rules
├── accessibility/ ← (future) accessibility rules
├── security/      ← (future) security rules
└── <new>/         ← create a new subdirectory if your rule doesn't fit
```

Match the categorization to the rule's purpose, not its mechanism. A rule about excessive script length goes under `scripts/`, not `performance/`, even if performance is the motivation.

## Configuration in `rule_config.json`

Rules pull every kwarg from the `kwargs` block:

```json
{
  "MyRule": {
    "enabled": true,
    "kwargs": {
      "min_length": 5,
      "severity": "error"
    }
  }
}
```

Use `_`-prefixed keys for inline notes — they're stripped before instantiation:

```json
{
  "MyRule": {
    "enabled": true,
    "_note": "Tightened to error severity in Q1 2026 — see ADR-12",
    "kwargs": { ... }
  }
}
```

## Testing your rule

See [Testing rules](./testing-rules.md) for the full guide. Minimal:

```python
# tests/unit/test_my_rule.py
import unittest
from tests.fixtures.base_test import BaseRuleTest
from tests.fixtures.test_helpers import get_test_config


class TestMyRule(BaseRuleTest):
    def setUp(self):
        super().setUp()
        self.rule_config = get_test_config("MyRule", min_length=5)

    def test_passes_valid_case(self):
        view = self.test_cases_dir / "PascalCase" / "view.json"
        self.assert_rule_passes(view, self.rule_config, "MyRule")

    def test_fails_invalid_case(self):
        view = self.test_cases_dir / "MixedCase" / "view.json"
        self.assert_rule_fails(view, self.rule_config, "MyRule")
```

Run:

```bash
cd tests
poetry run python test_runner.py --test my_rule
```

## Best practices

- **One rule, one concern.** A naming-and-length rule is two rules.
- **Lead error messages with the path.** `f"{node.path}: ..."` lets users navigate directly.
- **Include a suggestion when possible.** "Name 'temp' should be PascalCase (suggestion: 'Temp')."
- **Compile regexes in `__init__`, not in `visit_*`.** Per-node calls are hot paths.
- **Use sets for membership checks**, lists for ordered data.
- **Avoid mutating nodes.** Track state in `self.*`.
- **Default to warning severity for style rules**, error for correctness/performance rules.

## See also

- [Architecture](./architecture.md) — pipeline and visitor concepts
- [API reference](./api-reference.md) — registry, base classes, validation
- [Testing rules](./testing-rules.md) — `BaseRuleTest`, golden files, test fixtures
- [Troubleshooting](./troubleshooting.md) — common pitfalls
- Reference rules under `src/ignition_lint/rules/_examples/` — short, illustrative implementations
