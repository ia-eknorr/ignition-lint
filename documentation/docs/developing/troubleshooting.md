---
title: Troubleshooting
sidebar_label: Troubleshooting
description: Common issues when developing custom linting rules
---

# Troubleshooting

Common problems when writing rules, with the cause and fix for each.

## Registration

### Rule isn't discovered

**Symptoms:** Your rule doesn't appear in `get_all_rules()`. Configuration referencing it errors with "unknown rule."

**Diagnostic:**

```bash
poetry run python -c "from ignition_lint.rules import get_all_rules; print(list(get_all_rules().keys()))"
```

**Fixes:**

1. **Wrong location.** Rule files must live under `src/ignition_lint/rules/` (or a subdirectory). Files under `_examples/` are intentionally excluded from auto-discovery.
2. **Missing inheritance.** `class MyRule(LintingRule):` — without this, the discovery filter skips it.
3. **Import error in the file.** A failing import prevents the module from loading entirely. Run the file directly to see the error:
   ```bash
   poetry run python -m ignition_lint.rules.my_rule  # adjust path
   ```
4. **Absolute imports.** Inside the rules package, use relative imports:
   ```python
   from .common import LintingRule       # Correct
   from ..model.node_types import NodeType  # Correct
   ```
   Absolute imports work at runtime but break some discovery contexts.

### `RuleValidationError`

The registry validates rules during registration. Common failures:

| Error | Cause | Fix |
| --- | --- | --- |
| "must implement `error_message` property" | Forgot the `@property def error_message` | Add it |
| "is already registered" | Two rules with the same class name | Rename one or pass an explicit name to `register_rule(MyRule, "UniqueName")` |
| "Cannot instantiate" | `__init__` requires arguments without defaults | Add defaults — `cls.create_from_config({})` is called during validation |

## Imports

### `ModuleNotFoundError`

Always use **relative imports** inside `src/ignition_lint/rules/`:

```python
from .common import LintingRule           # Correct
from ..model.node_types import NodeType   # Correct
```

Absolute imports work at runtime but cause issues during test discovery and rule auto-discovery.

### Circular imports

If two rules import each other (e.g., `RuleA` references `RuleB` for cross-validation), import lazily inside methods rather than at module top:

```python
class RuleA(LintingRule):
    def post_process(self):
        from .rule_b import RuleB  # lazy import
        ...
```

Better: extract the shared logic into a helper module both rules import.

## Configuration

### Defaults are used instead of my config values

Most likely your config is missing the `"enabled"` and `"kwargs"` envelope:

```json
// Wrong — kwargs go directly under the rule
{
  "MyRule": {
    "min_length": 5
  }
}

// Correct
{
  "MyRule": {
    "enabled": true,
    "kwargs": {
      "min_length": 5
    }
  }
}
```

### Type errors from string config values

JSON only has strings, numbers, bools, etc. — no enums. If your `__init__` expects `NodeType`, you need a `preprocess_config` to convert:

```python
@classmethod
def preprocess_config(cls, config: dict) -> dict:
    processed = super().preprocess_config(config)
    if 'target_node_types' in processed:
        processed['target_node_types'] = {
            NodeType(s) for s in processed['target_node_types']
        }
    return processed
```

`NamePatternRule.preprocess_config` is the reference implementation.

## Visit methods

### `AttributeError` on `node.props.text`

Don't assume optional attributes exist. Use `getattr` or `hasattr`:

```python
# Wrong
text = node.props.text

# Correct
text = getattr(node, "props", {}).get("text")
```

For paths in the flattened JSON (when the node doesn't surface them as attributes), use the framework's flattened-JSON access pattern — see [Creating rules — Direct flattened-JSON access](./creating-rules.md#direct-flattened-json-access).

### My visit method isn't called

Three common causes:

1. **`target_node_types` doesn't include the relevant type.** Check `super().__init__(...)` in your rule.
2. **You're targeting the wrong node type.** A property binding is `NodeType.PROPERTY_BINDING`, not `NodeType.PROPERTY`. Use `--debug-nodes <type>` to see what nodes actually exist:
   ```bash
   ignition-lint --files path/to/view.json --debug-nodes property_binding
   ```
3. **Method name typo.** `visit_property_binding`, not `visit_propertybinding`. The framework dispatches on exact method names — see [Architecture — Visit methods](./architecture.md#visit-methods) for the canonical list.

### Infinite loop or stack overflow

You're probably trying to recurse manually:

```python
# Don't do this — the framework already walks the tree
def visit_component(self, node):
    for child in node.children:
        self.visit_component(child)
```

The framework dispatches every matching node automatically. Just process the current node.

## Performance

### My rule is slow on large views

Common causes and fixes:

| Symptom | Cause | Fix |
| --- | --- | --- |
| Slow on large arrays | Linear search over `forbidden_names` | Use a `set` for O(1) membership |
| Slow on every node | Compiling regex inside `visit_*` | Compile once in `__init__` |
| Memory grows during run | Storing every node | Track only what you need; clear in `post_process` |
| Slow on multi-file runs | Per-file pylint invocation | Use `batch_mode=True` (script rules only) |

Use `--analyze-rules` to see which rule dominates runtime:

```bash
ignition-lint --config rule_config.json --files "**/view.json" --analyze-rules
```

## Tests

### Tests pass but the rule fails on real views

Mock views from `create_mock_view` may differ from real Perspective view structure. Test against real fixtures:

```python
# Use the fixtures, not mocks
view = self.test_cases_dir / "PascalCase" / "view.json"
self.assert_rule_passes(view, self.rule_config, "MyRule")
```

If no fixture matches your scenario, add one:

```bash
mkdir tests/cases/MyScenario
# create view.json with the structure you need
python scripts/generate_debug_files.py MyScenario
```

### Golden file tests fail after I change the model

Expected — you changed model output. Regenerate the golden files:

```bash
python scripts/generate_debug_files.py
```

Review the diff carefully before committing. Unintended changes to other test cases likely indicate a regression.

### `BaseRuleTest` setup not running

You forgot `super().setUp()`:

```python
class TestMyRule(BaseRuleTest):
    def setUp(self):
        super().setUp()  # ← required
        self.rule_config = get_test_config("MyRule")
```

Without it, `self.test_cases_dir` is undefined.

## Output and severity

### Violations not appearing

If your rule's violations don't show up in CLI output, check the severity routing:

- `add_violation(message)` uses the rule's default severity (set in `super().__init__(severity=...)`)
- `add_violation(message, severity="warning")` overrides per-call

Double-check that your `--ignore-warnings` flag isn't suppressing what you intend to see.

### "0 errors found" but I see violations

You're using `--warnings-only`. That flag suppresses error reporting. Run without it.

## Auto-fix

### `add_fix` doesn't do anything

Check that fix mode is active:

```python
def visit_component(self, node):
    if self.has_fix_context:  # ← only when fix mode is enabled
        self.add_fix(...)
```

Without `has_fix_context`, the framework hasn't called `set_fix_context` — adding a fix here is a no-op.

### Fix applies the wrong value

The `json_path` field of `FixOperation` must be a list of dict keys / array indices that resolves against the original JSON document, not the flattened representation. Use `self._path_translator` helpers (e.g., `get_component_name_path`) to convert from a model path to a JSON path:

```python
name_path = self._path_translator.get_component_name_path(node.path)
```

`NamePatternRule._generate_component_fix` is the reference.

## Anti-patterns

A few patterns that compile but cause subtle bugs.

### Class-level mutable state

```python
# Shared across all instances and across runs
class MyRule(LintingRule):
    counter = 0
    seen = []
```

Instance state in `__init__`:

```python
class MyRule(LintingRule):
    def __init__(self):
        super().__init__({NodeType.COMPONENT})
        self.counter = 0
        self.seen = []
```

### Mutating the input

```python
# Don't write to nodes
def visit_component(self, node):
    node.processed = True
```

Track external state:

```python
def __init__(self):
    super().__init__({NodeType.COMPONENT})
    self.processed_paths = set()

def visit_component(self, node):
    self.processed_paths.add(node.path)
```

### Raising for violations

```python
# Don't raise — you'll abort the whole run
def visit_component(self, node):
    if bad:
        raise ValueError("invalid component")
```

Use `add_violation`:

```python
def visit_component(self, node):
    if bad:
        self.add_violation(f"{node.path}: invalid component")
```

## Debugging techniques

### Inspect what the framework sees

```bash
# Every component node in a view
ignition-lint --files path/to/view.json --debug-nodes component

# Multiple node types
ignition-lint --files path/to/view.json --debug-nodes expression_binding property
```

### Generate model dump

```bash
python scripts/generate_debug_files.py MyTestCase
ls tests/cases/MyTestCase/debug/
# flattened.json   model.json   stats.json
```

The `model.json` shows exactly what your visit methods will receive.

### Drop into a Python REPL

```python
from ignition_lint.rules import get_all_rules
from ignition_lint.linter import LintEngine
from pathlib import Path

rule_class = get_all_rules()["MyRule"]
engine = LintEngine(config_path="rule_config.json")
report = engine.lint_file(Path("tests/cases/PascalCase/view.json"))
print(report)
```

### Validate registration end-to-end

```bash
poetry run python -c "from ignition_lint.rules.registry import discover_rules; print(discover_rules())"
poetry run python -c "from ignition_lint.rules import get_all_rules; rule = get_all_rules()['MyRule']; instance = rule.create_from_config({}); print('OK')"
```

If both succeed, registration is wired correctly.

## See also

- [Architecture](./architecture.md) — pipeline concepts
- [Creating rules](./creating-rules.md) — patterns and examples
- [API reference](./api-reference.md) — registry, base classes, fix API
- [Debug output](../usage/debug-output.md) — model dumps and golden files
