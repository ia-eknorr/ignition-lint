---
title: BadComponentReferenceRule (full reference)
sidebar_label: BadComponentReferenceRule
description: Full technical reference for BadComponentReferenceRule — every option, every default pattern, every edge case.
toc_max_heading_level: 4
---

# BadComponentReferenceRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/structure/bad-component-reference.md). This page is the complete technical reference — every constructor argument, every default pattern, every edge case the rule deliberately skips. Read it when you're debugging a violation, customizing the pattern list, or integrating with custom rule code.

:::

## Purpose
Flags object-traversal patterns in scripts and expression bindings that create tight coupling to the view's structural layout. These patterns reach across the component tree by name or position, so any rename or reparent silently breaks them at runtime.

## Severity
`error` by default — these patterns reliably cause runtime breakage when view structure changes, so the rule fails the lint run unless explicitly downgraded. Configurable via the `severity` option.

## What it checks
The rule scans script and expression text for substrings from a `forbidden_patterns` list. Matching is plain Python `in`-substring containment (no AST analysis). When a match is found, the rule emits one violation per content unit, reporting the first pattern that matched plus a count of any additional matches.

The rule visits the following node types (`target_types = ALL_SCRIPTS | {NodeType.EXPRESSION_BINDING}`):

- `MessageHandlerScript`
- `CustomMethodScript`
- `TransformScript`
- `EventHandlerScript`
- `ExpressionBinding`

### Default `forbidden_patterns`

Sourced verbatim from `BadComponentReferenceRule.__init__`:

| Group | Patterns |
| --- | --- |
| Method calls | `.getSibling(`, `.getParent(`, `.getChild(`, `.getChildren(` |
| `self.parent` property access | `self.parent.`, `self.parent)`, `self.parent,`, `self.parent\n`, `self.parent\r` |
| `self.children` property access | `self.children.`, `self.children)`, `self.children,`, `self.children\n`, `self.children\r` |
| Relative path traversal | `../`, `./` |

The trailing-character variants (`.`, `)`, `,`, `\n`, `\r`) for `self.parent` and `self.children` exist so substring matching can detect property-access usage in realistic surrounding code without false-positive matches on identifiers like `self.parents`.

## Why it matters
Object traversal hard-codes view structure into scripts and bindings. Renaming a sibling component, reparenting a Container, or restructuring a layout silently breaks every script and expression that walked the tree. Because these references resolve at runtime, the breakage shows up as a failure at the moment the user interacts with the view — not at design time.

Recommended alternatives are decoupled communication mechanisms:

- `view.custom.*` properties for shared state within a view
- `system.perspective.sendMessage` + message handlers for cross-component events
- Session-scope and page-scope properties for cross-view state

These survive renames and reorganizations because they reference data, not tree positions.

## Configuration

The rule accepts three constructor options grouped into two categories.

### Detection

#### `forbidden_patterns`
**Type:** `list[str] | None` &nbsp;·&nbsp; **Default:** See [Default `forbidden_patterns`](#default-forbidden_patterns) above

Substrings to search for in script and expression content. When `None` (the default), the rule uses its built-in list of 16 patterns covering method calls, property access on `self.parent`/`self.children`, and relative-path traversal in expressions.

Providing a custom list **replaces** the defaults entirely — it is not merged. To add a pattern without losing the defaults, copy the default list and append. To relax the rule (for example, allow relative path expressions), copy the defaults and drop the entries you want to ignore.

Matching is plain `in`-substring containment. Pattern strings include their surrounding delimiters intentionally (the `(` after method names, the `.`/`)`/`,`/newline after `self.parent`) so unrelated identifiers do not produce false positives.

---

#### `case_sensitive`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `False`, both the content and the patterns are lowercased before matching. This catches non-canonical capitalizations like `Self.GetSibling("x")` or `COMPONENT.GETPARENT()`. Leave at `True` for normal Python and Ignition expression code — those are case-sensitive languages, so a non-canonical capitalization would already fail at runtime.

### Severity

#### `severity`
**Type:** `"error" | "warning"` &nbsp;·&nbsp; **Default:** `"error"`

Controls which list (errors vs. warnings) violations are reported under and whether the lint run fails. Default is `error` because every traversal pattern is a known source of runtime breakage. Downgrade to `warning` when adopting the rule incrementally on a legacy codebase you cannot fix all at once.

## Examples

### Correct code

A button event handler that uses `view.custom` for cross-component state passes the rule:

```python
# Update shared state — the StatusLabel binds to view.custom.statusText
self.view.custom.statusText = 'Button clicked!'
```

A message-handler-based equivalent also passes:

```python
system.perspective.sendMessage(
	messageType='button-clicked',
	payload={'source': self.props.name},
	scope='view'
)
```

### Problematic code: script with `.getSibling()`

From `tests/cases/BadComponentReferences/view.json`, the `BadButton.onActionPerformed` event handler script:

```python
# Bad pattern 1: getSibling
sibling = self.getSibling('StatusLabel')
sibling.props.text = 'Button clicked!'

# Bad pattern 2: getParent
parent = self.getParent()
parent.props.style.backgroundColor = 'red'
```

**Violation message format:**

```
<path>: <Content_type> contains '<pattern>' which creates brittle view structure dependencies. Consider using view.custom properties or message handling for component communication instead.
```

Where `<Content_type>` is `"Script"` or `"Expression"` depending on the node type. When more than one pattern matches in the same content unit, the message lists the count: `'<first>' and <N> other object traversal pattern(s)`.

### Problematic code: custom method with multiple traversal patterns

From the same fixture, the `CustomMethodComponent.navigateHierarchy` custom method contains three patterns in one script:

```python
# Multiple bad patterns in one method
if direction == 'up':
    return self.getParent().props.name
elif direction == 'down':
    children = self.getChildren()
    return [child.props.name for child in children]
else:
    sibling = self.getSibling('StatusLabel')
    return sibling.props.text
```

The rule reports one violation for this script and notes the additional matches in the message.

### Problematic code: expression with relative path

The `BadButton.props.enabled` binding uses a relative-path expression:

```
{../StatusLabel.position.display} || {../ContainerWithBadScript.position.display}
```

The `../` pattern matches and the rule emits an `Expression contains '../'` violation.

### Problematic code: expression with `.getSibling`

The view's root-level child expression binding:

```
self.getSibling('OtherLabel').props.text + ' - Updated'
```

### Problematic code: property-access traversal in an expression

The `ContainerWithBadScript.props.children` binding chains `self.parent.getChild`:

```
self.parent.getChild('DataSource').props.data
```

This expression matches both `self.parent.` and `.getChild(` — the rule reports the first found, plus the additional-match count.

## Relationship to ComponentReferenceValidationRule
The two rules complement each other:

| Rule | When it fires |
| --- | --- |
| `BadComponentReferenceRule` | The pattern is used at all — even if it resolves to a real component |
| `ComponentReferenceValidationRule` | The pattern is used AND it does not resolve to a real component in the view tree |

Run both together for the strongest signal: `BadComponentReferenceRule` discourages the practice everywhere, while `ComponentReferenceValidationRule` upgrades the severity for references that are also broken. A team migrating off traversal patterns can keep `BadComponentReferenceRule` at `warning` for visibility and `ComponentReferenceValidationRule` at `error` to block actual runtime breakage.

## Recommended alternatives
- **Shared state**: store data on `view.custom.*` and bind multiple components to it. Renames are isolated to the binding path, not buried inside script logic.
- **Message handlers**: use `system.perspective.sendMessage` plus a message handler for cross-component events. The publisher and subscriber are decoupled by message type, not tree position.
- **Session and page properties**: for state that spans views, use `session.custom.*` or page-scope properties.
- **Direct property bindings**: where two components really do need to mirror each other, use a property binding from the source's path rather than a script that reads via `getSibling`.

## Auto-fix support
This rule does **not** provide auto-fixes. Replacing a traversal call requires understanding the semantic intent — which custom property to bind to, which message to send, what state to lift — and the rule cannot infer that from string matching. Migrations need to be done by hand.

## Edge cases & exemptions
- The rule reports the **first matching pattern** found per content unit (script or expression) and mentions the count of additional matches in the violation message. This avoids spamming a single script with one violation per pattern.
- Pattern matching is plain Python `in`-substring matching; there is no AST analysis. A method named `notGetSibling(` would NOT trigger because it does not contain `.getSibling(`. Conversely, the pattern matches inside comments and string literals — for example, a docstring that mentions `.getSibling()` will be flagged. This is documented behavior; in practice it's rare and often desirable (don't reference banned APIs even in docs).
- Both `./` and `../` are considered violations. This catches relative path expressions in property bindings even when they look harmless. Teams that intentionally rely on relative paths can remove these two entries from `forbidden_patterns` while keeping the script-level checks.
- Empty or missing content is skipped — the rule short-circuits when `content` is empty.
- Case-sensitive matching is the default. Switching to `case_sensitive: false` lowercases both sides, so `component.GETSIBLING("test")` would match `.getsibling(`.
- Providing your own `forbidden_patterns` **replaces** the default list; it is not additive. Copy the defaults and edit if you want to extend or relax them.

## See also
- [BadComponentReferenceRule user guide](../../rules/structure/bad-component-reference.md) — the short version
- [ComponentReferenceValidationRule](../../rules/structure/component-reference-validation.md)
- [Configuration overview](../../getting-started/configuration.md)
