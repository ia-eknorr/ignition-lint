---
title: API reference
sidebar_label: API reference
description: Rule registry, base classes, and programmatic access
---

# API reference

Reference for the framework's public Python API. Use this when wiring ignition-lint into custom tooling, building rule generators, or auditing the registry programmatically.

## Rule registry

```python
from ignition_lint.rules.registry import (
    get_registry,
    register_rule,
    discover_rules,
    RuleValidationError,
)
from ignition_lint.rules import get_all_rules
```

### `register_rule(rule_class, rule_name=None) → str`

Register a rule with the global registry. Usable as a decorator or function.

| Parameter | Type | Description |
| --- | --- | --- |
| `rule_class` | `Type[LintingRule]` | The rule class |
| `rule_name` | `str \| None` | Custom name (defaults to class name) |

**Returns:** registered rule name

**Raises:** `RuleValidationError` if validation fails

```python
@register_rule
class MyRule(LintingRule):
    ...

# Or as a function with a custom name
register_rule(MyRule, "CustomName")
```

### `get_registry() → RuleRegistry`

Returns the global `RuleRegistry` singleton.

### `get_all_rules() → dict[str, Type[LintingRule]]`

Returns every registered rule, keyed by name.

```python
from ignition_lint.rules import get_all_rules

rules = get_all_rules()
for name, cls in rules.items():
    print(f"{name}: {cls.__doc__}")
```

### `discover_rules() → list[str]`

Walks `src/ignition_lint/rules/` and registers every valid `LintingRule` subclass it finds. Called automatically on package import; rarely needed manually.

### `RuleValidationError`

Raised when a rule fails registration. Common causes:

- Class doesn't inherit from `LintingRule`
- `error_message` property is missing
- Rule cannot be instantiated with `cls.create_from_config({})`
- Name conflict with an already-registered rule

## RuleRegistry

```python
from ignition_lint.rules.registry import RuleRegistry
```

| Method | Returns | Purpose |
| --- | --- | --- |
| `register_rule(rule_class, rule_name=None)` | `str` | Register a rule |
| `get_rule(rule_name)` | `Type[LintingRule] \| None` | Look up by name |
| `get_all_rules()` | `dict[str, Type[LintingRule]]` | All registered rules |
| `list_rules()` | `list[str]` | Rule names only |
| `is_registered(rule_name)` | `bool` | Check existence |
| `get_rule_metadata(rule_name)` | `dict \| None` | Extracted metadata for a rule |
| `discover_and_register_rules(package_path=None)` | `list[str]` | Run discovery |

### Metadata fields

`get_rule_metadata` returns a dict with:

| Key | Description |
| --- | --- |
| `class_name` | Class name |
| `module` | Defining module |
| `docstring` | Class docstring |
| `source_file` | Path to the source file |
| `error_message` | Rule's `error_message` property value |

Useful for auto-generating rule catalogs or IDE help.

## LintingRule base class

```python
from ignition_lint.rules.common import LintingRule, BindingRule, ScriptRule, FixableMixin
```

### Constructor

```python
LintingRule(
    target_node_types: set[NodeType] | None = None,
    severity: str = "error",
    include_private_properties: bool = False,
)
```

| Parameter | Description |
| --- | --- |
| `target_node_types` | Node types this rule processes (filters which `visit_*` methods receive nodes). `None` ≡ no filtering. |
| `severity` | Default severity: `"error"` or `"warning"` |
| `include_private_properties` | When `False`, properties starting with `_` and the reserved key `_JavaDate` are skipped |

### Required: `error_message`

```python
@property
@abstractmethod
def error_message(self) -> str:
    ...
```

Description of what the rule checks. Used in CLI output and metadata.

### Lifecycle

| Method | Default behavior | Override to... |
| --- | --- | --- |
| `applies_to(node)` | Filter by `target_node_types` and private-property setting | Customize node filtering |
| `process_nodes(nodes)` | Reset state, filter, dispatch via `accept`, call `post_process` | Bypass standard iteration entirely |
| `post_process()` | No-op | Run cross-node analysis after all nodes visited |
| `add_violation(message, severity=None)` | Routes to `errors` or `warnings` | (rarely) |

### `preprocess_config(cls, config)`

Class method that runs before `__init__`. Default behavior strips keys starting with `_` (used for inline comments). Override to convert strings to enums, validate values, etc.

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

### `create_from_config(cls, config)`

Builds a rule instance from a config dict. Calls `preprocess_config` first, then unpacks the result as kwargs to `__init__`. The framework calls this internally when loading `rule_config.json`.

## BindingRule

Specializes `LintingRule` for binding-only rules:

```python
class BindingRule(LintingRule):
    def __init__(self, target_node_types=None, severity="error", include_private_properties=False):
        if target_node_types is None:
            target_node_types = ALL_BINDINGS
        super().__init__(target_node_types, severity, include_private_properties)
```

Use when your rule visits one or more binding types. Same API as `LintingRule` otherwise.

## ScriptRule

Specializes `LintingRule` for script-only rules. Auto-collects scripts and exposes them as a batch:

```python
class ScriptRule(LintingRule):
    @abstractmethod
    def process_scripts(self, scripts: dict[str, ScriptNode]):
        """Receive all collected scripts at once."""
```

The framework calls every `visit_*_handler` / `visit_custom_method` / `visit_transform` for you (each appends to `self.collected_scripts`), then invokes `process_scripts` in `post_process`. You typically only override `process_scripts` and the constructor.

## FixableMixin

Adds auto-fix capability. Inherit alongside any rule base:

```python
class MyRule(FixableMixin, LintingRule):
    ...
```

| Method | Purpose |
| --- | --- |
| `add_fix(fix: Fix)` | Add a fix to the collection |
| `get_fixes() → list[Fix]` | Return collected fixes |
| `reset_fixes()` | Clear collected fixes |
| `set_fix_context(json_data, path_translator)` | Called by `LintEngine` when fix mode is active |
| `has_fix_context → bool` | True when fix mode is active |
| `supports_fix → bool` | Always True for `FixableMixin` consumers |

## Fix and FixOperation

```python
from ignition_lint.common.fix_operations import Fix, FixOperation, FixOperationType
```

### Fix

| Field | Type | Description |
| --- | --- | --- |
| `rule_name` | `str` | Producing rule (typically `self.error_key`) |
| `violation_message` | `str` | The violation this fix addresses |
| `description` | `str` | Human-readable summary |
| `operations` | `list[FixOperation]` | Edit operations |
| `is_safe` | `bool` | Whether automatic application is safe |
| `safety_notes` | `str` | If unsafe, why (`"updates 3 reference(s)"`, `"component uses 'this.meta.name' binding"`) |

### FixOperation

| Field | Description |
| --- | --- |
| `operation` | One of `FixOperationType.SET_VALUE`, `DELETE`, `INSERT` (see source for current full set) |
| `json_path` | List of dict keys / array indices into the original JSON |
| `old_value` | Value before the fix (for verification) |
| `new_value` | Value after the fix |
| `description` | Per-operation description |

The `LintEngine` resolves `json_path` against the loaded JSON document and applies operations in order.

## NodeType

```python
from ignition_lint.model.node_types import (
    NodeType,
    ALL_BINDINGS,
    ALL_SCRIPTS,
    ViewNode,
    Component,
    Property,
    ExpressionBinding,
    PropertyBinding,
    TagBinding,
    QueryBinding,
    EventHandlerScript,
    MessageHandlerScript,
    CustomMethodScript,
    TransformScript,
)
```

### Enum values

`NodeType` is a string enum — values match the strings used in `rule_config.json` for `target_node_types`:

| Value (string) | Class |
| --- | --- |
| `"component"` | `Component` |
| `"property"` | `Property` |
| `"expression_binding"` | `ExpressionBinding` |
| `"expression_struct_binding"` | `ExpressionStructBinding` |
| `"property_binding"` | `PropertyBinding` |
| `"tag_binding"` | `TagBinding` |
| `"query_binding"` | `QueryBinding` |
| `"event_handler"` | `EventHandlerScript` |
| `"message_handler"` | `MessageHandlerScript` |
| `"custom_method"` | `CustomMethodScript` |
| `"transform"` | `TransformScript` |

### Sets

| Set | Members |
| --- | --- |
| `ALL_BINDINGS` | All binding node types |
| `ALL_SCRIPTS` | All script node types |

## ViewNode and node attributes

Every node has:

```python
node.path        # Full dotted path in the original JSON
node.node_type   # NodeType enum value
node.accept(visitor)  # Visitor pattern dispatch
```

Type-specific attributes (most common):

| Class | Attributes |
| --- | --- |
| `Component` | `name`, `type`, `properties` (dict) |
| `Property` | `name` |
| `ExpressionBinding` | `expression`, `config` |
| `ExpressionStructBinding` | `struct` (dict[str, str]) |
| `PropertyBinding` | `target_path`, `config` |
| `TagBinding` | `tag_path`, `mode` (`"direct"` / `"expression"` / `"indirect"`), `references` |
| `QueryBinding` | `parameters` (dict[str, str]) |
| `*Script` (all) | `script`, `get_formatted_script()` |
| `MessageHandlerScript` | `+ message_type`, `scope` |
| `CustomMethodScript` | `+ name`, `params` |
| `TransformScript` | `+ binding_path` |
| `EventHandlerScript` | `+ event_type`, `scope` |

`get_formatted_script()` on script nodes returns runnable Python with the appropriate indentation and (for custom methods) function definition.

## LintEngine

```python
from ignition_lint.linter import LintEngine
```

The orchestrator. Wraps configuration, model building, and rule execution. Most consumers don't construct it directly — `cli.py` is the canonical entry point — but it's available for embedding in custom tools:

```python
from ignition_lint.linter import LintEngine

engine = LintEngine(config_path="rule_config.json")
report = engine.lint_file("path/to/view.json")
```

See `src/ignition_lint/linter.py` for the full interface.

## See also

- [Architecture](./architecture.md) — conceptual overview
- [Creating rules](./creating-rules.md) — how the API is used in practice
- [Troubleshooting](./troubleshooting.md) — common API misuse
