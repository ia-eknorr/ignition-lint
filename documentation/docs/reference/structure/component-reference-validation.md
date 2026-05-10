---
title: ComponentReferenceValidationRule (full reference)
sidebar_label: ComponentReferenceValidationRule
description: Full technical reference for ComponentReferenceValidationRule — every option, every violation message, every edge case the rule handles.
toc_max_heading_level: 4
---

# ComponentReferenceValidationRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/structure/component-reference-validation.md). This page is the complete technical reference — every constructor argument, every default, every violation message format, every edge case. Read it when you're debugging a violation, integrating the rule with custom code, or extending it.

:::

## Purpose
The rule walks the component tree and verifies that every relative reference — `{../Component.props.value}` style expressions, dotted property binding paths, and `self.getSibling()` / `self.getChild()` script chains — resolves to a component that actually exists in the view. Where [BadComponentReferenceRule](../../rules/structure/bad-component-reference.md) flags the *pattern* as bad practice, this rule flags references that are also *broken*.

## Severity
`error` by default — a reference that doesn't resolve will fail at runtime, often silently (a binding produces `null`, a script raises a `NoneType` attribute error). Configurable via the `severity` option.

## What it checks

| Reference type | Visit method | Pattern |
| --- | --- | --- |
| Expression bindings | `visit_expression_binding` | `{../path}`, `{.../Container/Child.props.value}` |
| Property bindings | `visit_property_binding` | `../sibling.props.x`, `.../Parent/Child.position.display` |
| Event handler scripts | `visit_event_handler` | `self.getSibling('Name')`, chains starting with `self` |
| Message handler scripts | `visit_message_handler` | same as event handlers |
| Custom method scripts | `visit_custom_method` | same as event handlers |
| Transform scripts | `visit_transform` | same as event handlers |

In all script contexts the rule recognizes both simple `self.getSibling('Name')` calls and chained navigation such as `self.parent.getChild('A').getSibling('B')`.

## Why it matters
Relative references are positional — they encode "go up two levels, then down into `Container/Button`". When a developer renames `Button`, deletes `Container`, or moves the binding to a different component, the reference silently breaks. Ignition does not validate these paths at design time; the broken reference compiles and saves cleanly, and only fails when a user opens the view in the gateway. This rule catches those failures at lint time, before they ship. It complements `BadComponentReferenceRule` (which discourages the pattern entirely) by ensuring that any references that *do* exist are at least functionally correct.

## Configuration

The rule accepts 4 options grouped into two categories below. All options can be passed as top-level kwargs in `rule_config.json`.

### Validation toggles

#### `validate_expressions`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `True`, the rule validates `{../path}` references in expression bindings. Set to `False` to skip expression validation entirely — useful when migrating an existing codebase incrementally.

---

#### `validate_property_bindings`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `True`, the rule validates relative target paths in property bindings (`../sibling.props.x`, `.../Parent/Child.position.display`). Absolute paths like `view.params.eq_path_url` or `[default]Tag/Path` are always skipped regardless of this setting — see [Edge cases & exemptions](#edge-cases--exemptions).

---

#### `validate_scripts`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `True`, the rule validates `getSibling`/`getChild` calls inside event handlers, message handlers, custom methods, and transforms. Set to `False` if your team frequently uses dynamic script-based navigation that the static analyzer cannot follow.

### Severity

#### `severity`
**Type:** `"warning" | "error"` &nbsp;·&nbsp; **Default:** `"error"`

Default severity for emitted violations. Unlike `NamePatternRule`, this rule defaults to `error` because broken references cause runtime failures.

## How references are resolved

### Dot-counting (Ignition path semantics)
A reference begins with one or more dots. Each dot **beyond the first** moves one level up the tree:

| Reference | `levels_up` |
| --- | --- |
| `..`  | 1 |
| `...` | 2 |
| `....` | 3 |

Internally the rule computes `levels_up = len(dots) - 1`. After climbing, slashes navigate down. `.../Parent/Child.props.value` means: go up 2 levels, find a child named `Parent`, then find `Child` as `Parent`'s child, then access `props.value`.

This matches the [official Ignition binding property path reference](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/binding-property-path-reference).

### Resolution algorithm
The rule runs two phases (see `process_nodes`):

1. **Index phase** — walk every `Component` node once and build:
   - `component_tree`: full path → `Component`
   - `component_by_name`: name → list of `Component`s (names are not unique across the tree)
   - `parent_map`: child path → parent path
   - `children_map`: parent path → list of child paths

2. **Validation phase** — visit every binding/script and resolve each reference:
   - Climb `levels_up` parents using `parent_map`. If the climb runs out of parents, emit a "navigates above root" violation.
   - For each path segment after the climb, find the named child via `children_map` + `component_tree`.
   - If any step fails, emit a violation.

### Component path extraction
Reference resolution starts from the component that *owns* the binding/script, not from the binding/script path itself. The owner is derived by stripping the first known marker from the source path (see `_get_component_path_from_source`):

| Source path contains | Component path is everything before |
| --- | --- |
| `.propConfig.` | `.propConfig.` (e.g. `root.root.children[1].Button2.propConfig.props.enabled` → `root.root.children[1].Button2`) |
| `.props.` | `.props.` |
| `.events.` | `.events.` (event handler scripts) |
| `.scripts.` | `.scripts.` (custom methods, message handlers) |

If none of these markers match, the rule falls back to the longest component path in the index that prefixes the source path, and finally to `'root'`.

## Examples

### Correct code

Sibling reference in an expression binding — from `tests/unit/structure/test_component_reference_validation.py::test_valid_sibling_reference_in_expression`:

```json
{
  "children": [
    { "meta": { "name": "Button1" }, "type": "ia.input.button", "props": { "text": "Button 1" } },
    {
      "meta": { "name": "Button2" },
      "type": "ia.input.button",
      "propConfig": {
        "props.enabled": {
          "binding": {
            "config": { "expression": "{../Button1.props.text}" },
            "type": "expr"
          }
        }
      }
    }
  ],
  "meta": { "name": "root" },
  "type": "ia.container.coord"
}
```

`Button2`'s binding climbs one level (to `root`) and resolves `Button1` as a child. Passes.

Nested path reference — from `test_valid_nested_path_in_expression`:

```json
{
  "config": { "expression": "{../Container1/NestedButton.props.text}" },
  "type": "expr"
}
```

Climbs one level to `root`, then drills into `Container1 → NestedButton`. Passes.

Four-dot navigation — from `test_multiple_levels_up_three_dots` (`....` means 3 levels up):

```json
{
  "config": { "expression": "{..../TopContainer.props.style}" },
  "type": "expr"
}
```

`DeepButton` (3 levels deep) climbs 3 levels to `root`, then resolves `TopContainer` as a child. Passes.

### Problematic code

Reference to a non-existent sibling — from `test_invalid_sibling_reference_in_expression`:

```json
{
  "config": { "expression": "{../NonExistentButton.props.text}" },
  "type": "expr"
}
```

Produces:

```
<binding path>: Expression references non-existent component 'NonExistentButton' in: {../NonExistentButton.props.text}
```

Navigating above root — from `test_navigate_above_root_error`. A top-level child uses `.../` (2 levels up), but the tree only has 1 level above it:

```json
{
  "config": { "expression": "{.../SomethingAboveRoot.props.enabled}" },
  "type": "expr"
}
```

Produces:

```
<binding path>: Relative expression '{.../SomethingAboveRoot.props.enabled}' navigates above root component
```

Broken script chain — from `test_invalid_chained_navigation`:

```python
nested = self.getSibling('Container1').getChild('MissingButton')
```

`Container1` resolves, but it has no child named `MissingButton`. Produces:

```
<script path>: Component 'MissingButton' not found as child in: self.getSibling('Container1').getChild('MissingButton')
```

### Violation message formats (verbatim from source)
The rule emits one of six message templates:

- Navigation above root:<br/>
  `<path>: Relative <ref_type> '<full_ref>' navigates above root component`
- Component not found (expression / property binding):<br/>
  `<path>: <Ref_type> references non-existent component '<component_ref>' in: <full_ref>`
- Sibling not found (simple `getSibling`):<br/>
  `<path>: Script references non-existent sibling component '<name>'`
- Sibling not found in chain:<br/>
  `<path>: Component '<name>' not found as sibling in: <chain>`
- Child not found in chain:<br/>
  `<path>: Component '<name>' not found as child in: <chain>`
- Chain climbs past root:<br/>
  `<path>: Navigation chain goes beyond root: <chain>`

`<ref_type>` is one of `expression` / `property binding`. The "component not found" template title-cases the prefix, producing `Expression references non-existent component...` or `Property binding references non-existent component...`.

## Real-world example: `BadComponentReferences` test fixture

The shipped `tests/cases/BadComponentReferences/view.json` deliberately mixes valid and invalid references so this rule can be regression-tested end-to-end. Notable broken references the rule catches:

- Line 273 / 406: `../NestedButton4.props.enabled` — `NestedButton4` does not exist as a sibling
- Line 517: `self.getSibling("UnknownButton")` — `UnknownButton` is not a sibling of the calling component

The `test_bad_component_references_test_case` test asserts that both `NestedButton4` and `UnknownButton` appear in the rule's violations.

## Auto-fix support
This rule does not provide auto-fixes. Fixing a broken reference requires knowing what the developer *intended* to reference, which the rule cannot infer from the AST alone — `{../NonExistentButton.props.text}` could mean any of several existing siblings, or a component that needs to be re-added.

## Edge cases & exemptions

- **Absolute paths are skipped.** `visit_property_binding` returns early when `target_path` does not start with `.`, so absolute paths like `view.params.eq_path_url` or `[default]Tag/Path` are never validated by this rule.
- **Empty bindings/scripts are skipped.** If `node.expression`, `node.target_path`, or `node.script` is empty/`None`, the visitor returns early.
- **Name collisions are tolerated.** Two components named `Button` in different containers do not conflict — resolution walks the parent/child maps by tree position, not by global name lookup. `component_by_name` is built but used only as an index.
- **Property suffixes are stripped before navigation.** `_extract_component_reference` strips `.props.`, `.position.`, `.meta.`, and `.custom.` from the reference, so `{../Switch1.custom.energized}` and `{../Switch1.props.text}` both resolve as long as `Switch1` exists.
- **Property names are not validated.** The rule only validates that the *component path* resolves. `{../Sibling.props.totallyMadeUp}` passes as long as `Sibling` exists, even if `totallyMadeUp` is not a real prop on it.
- **Duplicate violations on simple `getSibling` calls are possible.** A simple `self.getSibling('X')` is matched both by the simple-pattern path and by the chained-pattern path; the test `test_invalid_get_sibling_script` asserts `assertGreaterEqual(len(rule_errors), 1)` for that reason.

## See also
- [ComponentReferenceValidationRule user guide](../../rules/structure/component-reference-validation.md) — the short version
- [BadComponentReferenceRule](../../rules/structure/bad-component-reference.md) — flags the pattern itself as bad practice
- [Ignition binding path reference](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/binding-property-path-reference)
- [Perspective component methods](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/perspective/scripting-in-perspective/perspective-component-methods)
- [Configuration overview](../../getting-started/configuration.md)
