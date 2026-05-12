---
title: NamePatternRule (full reference)
sidebar_label: NamePatternRule
description: Full technical reference for NamePatternRule — every option, every edge case, every violation message format.
toc_max_heading_level: 4
---

# NamePatternRule — full reference

:::tip[Looking for the short version?]

See the [user guide](../../rules/naming/name-pattern.md). This page is the complete technical reference — every constructor argument, every default, every edge case the rule deliberately skips. Read it when you're debugging a violation, integrating with custom code, or extending the rule.

:::

## Purpose
Validates that names attached to view nodes (components, properties, custom methods, and message handlers) match a configured naming convention or regex pattern. The same rule instance can apply different conventions, length limits, and severities per node type.

## Severity
`warning` by default — naming violations are stylistic and rarely block runtime behavior, so the rule defers to teams that want to escalate them. Configurable via the `severity` option (or per node type inside `node_type_specific_rules`).

## What it checks
For every node whose `node_type` is in `target_node_types`, the rule:

- Extracts the node's name (`meta.name` for components, the property key for properties, `name`/`message_type` for scripts).
- Skips the name if it appears in `skip_names` (defaults to `{'root'}` for properties — components inherit the same default through the `_get_node_specific_config` lookup).
- Reports a violation if the name appears in `forbidden_names`.
- Reports a violation if `len(name) < min_length` or (when set) `len(name) > max_length`.
- Reports a violation if the name does not match the active regex (`pattern` from `convention`, the `custom_pattern` override, or a per-node override).
- Skips properties that are CSS, position, or SVG path data — see [Edge cases & exemptions](#edge-cases--exemptions).
- Optionally suggests a corrected name (using `suggestion_convention` or the active `convention`) and, when fix mode is active, emits a `Fix` to rename the component.

Event handler nodes are intentionally never validated — Ignition defines those names (`onActionPerformed`, etc.).

## Why it matters
Consistent naming makes views searchable, makes bindings easier to read, and lets teams enforce per-node-type conventions (for example PascalCase for components, camelCase for properties). Violations are warnings by default so projects can adopt the rule incrementally without breaking CI.

## Configuration

The rule accepts 14 options grouped into five categories below. The dataclass `NamePatternConfig` packages the validation, abbreviation, and severity options — you can pass it directly via the `config` keyword, or pass the same fields as top-level kwargs and a `NamePatternConfig` will be built for you.

### Pattern selection

#### `convention`
**Type:** `str | None` &nbsp;·&nbsp; **Default:** `None`

Predefined convention key — see [Predefined naming conventions](#predefined-naming-conventions). When unset and no `custom_pattern` is provided, the rule falls back to `PascalCase` and prints a warning. When `convention` is set but does not match any key, the rule also falls back to `PascalCase`.

---

#### `custom_pattern`
**Type:** `str | None` &nbsp;·&nbsp; **Default:** `None`

Raw regex pattern. Overrides `convention` when set. The rule applies it as-is via `re.match`, so the pattern should anchor itself (`^...$`) if you need a full-name match.

---

#### `target_node_types`
**Type:** `set[NodeType] | list[str]` &nbsp;·&nbsp; **Default:** `{NodeType.COMPONENT}`

Node types this rule applies to. Strings like `"component"` are converted to `NodeType` enums during config preprocessing. When `node_type_specific_rules` is set and `target_node_types` is omitted, target types are auto-derived from the keys of `node_type_specific_rules`.

---

#### `suggestion_convention`
**Type:** `str | None` &nbsp;·&nbsp; **Default:** `None`

Convention used to generate suggested names. Required when `custom_pattern` is set and you want suggestions in violation messages — without it, custom-pattern violations have no suggestion text. Also overrides the suggestion convention when `convention` is set (e.g. validate against `convention: PascalCase` but suggest in `camelCase`).

---

#### `node_type_specific_rules`
**Type:** `dict[NodeType | str, dict] | None` &nbsp;·&nbsp; **Default:** `None`

Per-node-type overrides. Each value is a partial config; missing keys fall back to the top-level value. Recognized override keys: `convention`, `custom_pattern`, `pattern`, `pattern_description`, `suggestion_convention`, `min_length`, `max_length`, `allow_numbers`, `forbidden_names`, `skip_names`, `severity`. See [Per-node-type rules](#per-node-type-rules) for full examples.

### Validation constraints

#### `min_length`
**Type:** `int` &nbsp;·&nbsp; **Default:** `1`

Minimum allowed name length (inclusive). Names shorter than this emit a violation: `<path>: Name '<name>' is too short (minimum <min_length> characters) for <node_type>`.

---

#### `max_length`
**Type:** `int | None` &nbsp;·&nbsp; **Default:** `None`

Maximum allowed name length (inclusive). `None` disables the check. Names longer than this emit: `<path>: Name '<name>' is too long (maximum <max_length> characters) for <node_type>`.

---

#### `allow_numbers`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `False`, the rule removes `0-9` from the active regex character classes. Affects only the predefined-convention patterns; if you supply a `custom_pattern`, it is used unchanged.

---

#### `forbidden_names`
**Type:** `set[str] | list[str] | None` &nbsp;·&nbsp; **Default:** `None`

Names that are always rejected for the targeted node types, regardless of pattern match. Forbidden-name violations short-circuit further checks for that name and emit: `<path>: Name '<name>' is forbidden for <node_type>`.

---

#### `skip_names`
**Type:** `set[str] | list[str] | None` &nbsp;·&nbsp; **Default:** `{'root'}` (via the `skip_names` property)

Names that bypass all validation. Used to exempt framework-defined names (the default `'root'` is the always-present container). Per-node-type overrides can extend this set.

### Abbreviation options

See [Abbreviation handling](#abbreviation-handling) for the behavior these options control and the full built-in abbreviation list.

#### `allowed_abbreviations`
**Type:** `set[str] | list[str] | None` &nbsp;·&nbsp; **Default:** `None`

User-supplied abbreviations. Added to the built-in set unless `auto_detect_abbreviations` is `False`, in which case only your set is used.

---

#### `auto_detect_abbreviations`
**Type:** `bool` &nbsp;·&nbsp; **Default:** `True`

When `True`, the rule's built-in 69-entry abbreviation set is merged with `allowed_abbreviations`. Disable to use only your `allowed_abbreviations`.

### Severity

#### `severity`
**Type:** `"warning" | "error"` &nbsp;·&nbsp; **Default:** `"warning"`

Default severity for emitted violations. Per-node `severity` keys inside `node_type_specific_rules` take precedence over this value. Setting an invalid value raises `ValueError` during construction (validated in `NamePatternConfig.__post_init__`).

### Advanced

#### `name_extractors`
**Type:** `dict[NodeType, Callable[[ViewNode], str]] | None` &nbsp;·&nbsp; **Default:** Built-in extractors for `COMPONENT`, `MESSAGE_HANDLER`, `CUSTOM_METHOD`, `PROPERTY`

Custom callables for extracting a name from a node. Each callable receives the `ViewNode` and returns the name string (or `None` to skip). Override only if you're adding a new node type or you need to extract names from a non-standard attribute. Cannot be set via `rule_config.json` — programmatic API only.

## Predefined naming conventions

| Key | Pattern | Valid examples | Invalid examples |
| --- | --- | --- | --- |
| `PascalCase` | `^[A-Z][a-zA-Z0-9]*$` | `Button1`, `DataTable`, `MyCustomComponent` | `button1`, `data_table`, `my-component` |
| `camelCase` | `^[a-z][a-zA-Z0-9]*$` | `button1`, `dataTable`, `myCustomComponent` | `Button1`, `data_table`, `my-component` |
| `snake_case` | `^[a-z][a-z0-9_]*$` | `button_1`, `data_table`, `my_custom_component` | `Button1`, `dataTable`, `my-component` |
| `kebab-case` | `^[a-z][a-z0-9-]*$` | `button-1`, `data-table`, `my-custom-component` | `Button1`, `dataTable`, `my_component` |
| `SCREAMING_SNAKE_CASE` | `^[A-Z][A-Z0-9_]*$` | `BUTTON_1`, `DATA_TABLE`, `MY_CUSTOM_COMPONENT` | `Button1`, `dataTable`, `my-component` |
| `Title Case` | `^[A-Z][a-z]*(\s[A-Z][a-z]*)*$` | `Button One`, `Data Table`, `My Custom Component` | `button one`, `dataTable`, `my-component` |
| `lower case` | `^[a-z][a-z\s]*$` | `button one`, `data table`, `my custom component` | `Button One`, `dataTable`, `my-component` |

If `convention` is set but does not match any key, the rule prints a warning and falls back to `PascalCase`.

## Abbreviation handling
When `auto_detect_abbreviations` is `True` (the default), the rule's built-in abbreviation set is merged with anything you pass via `allowed_abbreviations`. Abbreviation matching is case-insensitive (`if abbrev in name.upper()` in `_process_abbreviations`), and how a matched abbreviation is normalized depends on the active convention:

| Convention | Abbreviation normalization |
| --- | --- |
| `PascalCase`, `camelCase` | Canonical uppercase form (e.g. `HTTPClient`, `apiHandler`) |
| `snake_case`, `kebab-case` | Lowercase (e.g. `http_client`, `api-handler`) |
| `SCREAMING_SNAKE_CASE` | Entire name uppercased |
| `Title Case` | Canonical uppercase form preserved (e.g. `HTTP Client`) |
| `lower case` | Lowercase everywhere |

Names that contain a recognized abbreviation, regardless of original case, are treated as if the abbreviation appeared in the canonical form for the active convention. This is what allows `APIClient`, `HTTPSConnection`, and `IOModuleController` to pass a PascalCase rule without explicit allow-listing.

### Built-in abbreviation set
The full set of 69 abbreviations recognized by `auto_detect_abbreviations`, sourced verbatim from `name_pattern.py::common_abbreviations`:

| Group | Abbreviations |
| --- | --- |
| Web & networking | `API`, `HTTP`, `HTTPS`, `FTP`, `SSH`, `TCP`, `UDP`, `IP`, `DNS`, `DHCP`, `VPN`, `URL`, `URI`, `UUID`, `REST`, `SOAP`, `AJAX`, `JWT` |
| Data formats | `XML`, `JSON`, `CSV`, `PDF`, `ZIP`, `GIF`, `PNG`, `JPG`, `JPEG`, `SVG` |
| Web technologies | `CSS`, `HTML`, `JS`, `TS`, `PHP`, `ASP`, `JSP`, `CGI`, `DOM` |
| Hardware | `CPU`, `GPU`, `RAM`, `SSD`, `HDD`, `LED`, `LCD`, `OLED`, `CRT` |
| UI / OS | `UI`, `UX`, `GUI`, `CLI`, `OS`, `iOS`, `macOS`, `ID` |
| Security | `SSL`, `TLS` |
| Cloud & vendors | `AWS`, `GCP`, `IBM` |
| AI / data | `AI`, `ML`, `NLP`, `OCR`, `CRUD`, `SQL` |
| Misc | `QR`, `RFID`, `NFC`, `GPS` |

To **disable** the built-in set entirely, pass `auto_detect_abbreviations: false` and supply only the abbreviations you want via `allowed_abbreviations`. To **extend** it, leave `auto_detect_abbreviations: true` (default) and add domain-specific entries through `allowed_abbreviations` — both sets are merged into `self.all_abbreviations`.

## Per-node-type rules
`node_type_specific_rules` lets a single rule instance apply different conventions, length limits, and severities to different node types. Each value is a partial config; missing keys fall back to the top-level value.

Recognized override keys: `convention`, `custom_pattern`, `pattern`, `pattern_description`, `suggestion_convention`, `min_length`, `max_length`, `allow_numbers`, `forbidden_names`, `skip_names`, `severity`.

When `target_node_types` is omitted, it is auto-derived from the keys of `node_type_specific_rules`.

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "node_type_specific_rules": {
        "component": {
          "convention": "PascalCase",
          "severity": "error"
        },
        "property": {
          "convention": "camelCase",
          "severity": "warning"
        }
      }
    }
  }
}
```

A combined PascalCase/SCREAMING_SNAKE_CASE pattern is a common real-world override (taken from `tests/unit/test_component_naming.py::TestNamePatternMixedCase`):

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "target_node_types": ["component"],
      "node_type_specific_rules": {
        "component": {
          "pattern": "^([A-Z][a-zA-Z0-9]*|[A-Z][A-Z0-9_]*)$",
          "pattern_description": "PascalCase or SCREAMING_SNAKE_CASE",
          "suggestion_convention": "PascalCase",
          "min_length": 3,
          "severity": "error"
        }
      }
    }
  }
}
```

## Examples

### Valid

`tests/cases/PascalCase/view.json` passes a PascalCase rule for components:

```json
{
  "root": {
    "children": [
      {
        "meta": { "name": "IconPascalCase" },
        "type": "ia.display.icon"
      }
    ],
    "meta": { "name": "root" },
    "type": "ia.container.flex"
  }
}
```

```json
{
  "NamePatternRule": {
    "enabled": true,
    "kwargs": {
      "target_node_types": ["component"],
      "convention": "PascalCase",
      "allow_numbers": true,
      "min_length": 1
    }
  }
}
```

The MixedCase fixture also demonstrates that abbreviations like `APIClient`, `HTTPSConnection`, `MyAPIHandler`, and `IOModuleController` pass when `auto_detect_abbreviations` is `True`:

```json
{ "meta": { "name": "APIClient" } }
```

### Invalid

A snippet from `tests/cases/inconsistentCase/view.json`:

```json
{
  "children": [
    { "meta": { "name": "GoodLabelName" }, "type": "ia.display.label" },
    { "meta": { "name": "badEmbeddedPotato_0" }, "type": "ia.display.view" },
    { "meta": { "name": "bad potato" }, "type": "ia.display.view" },
    { "meta": { "name": "anotherBadPotato" }, "type": "ia.display.view" }
  ]
}
```

Run against `convention: "PascalCase"`, every name except `GoodLabelName` produces a violation.

**Violation message format** (from `add_violation` in source):

- Pattern mismatch: `<path>: Name '<name>' doesn't follow <pattern_description> for <node_type>`
- Pattern mismatch with suggestion (when `convention` or `suggestion_convention` is set): `<path>: Name '<name>' doesn't follow <pattern_description> for <node_type> (suggestion: '<suggested_name>')`
- Forbidden name: `<path>: Name '<name>' is forbidden for <node_type>`
- Too short: `<path>: Name '<name>' is too short (minimum <min_length> characters) for <node_type>`
- Too long: `<path>: Name '<name>' is too long (maximum <max_length> characters) for <node_type>`

## Auto-fix support
`NamePatternRule` inherits `FixableMixin` and emits `Fix` objects only for `COMPONENT` violations and only when the `LintEngine` is invoked with `json_data` and a `path_translator` (i.e. fix mode is active). A fix is generated when `_suggest_name` returns a name that is non-empty and different from the current one.

The rule classifies each fix by inspecting the JSON for references using `ComponentReferenceFinder`:

- **Safe fix (`is_safe=True`)** — emitted when the component has no incoming references and no `this.meta.name` binding on itself. The fix contains a single `SET_VALUE` operation that updates `meta.name`.
- **Unsafe fix (`is_safe=False`)** — emitted when other expressions/property bindings/scripts reference the component name, or when the component reads its own name via `{this.meta.name}` or a `this.meta.name` property binding. The fix bundles the rename plus `STRING_REPLACE` operations for every reference, and `safety_notes` reports `"component uses 'this.meta.name' binding"` and/or `"updates N reference(s)"`.

`FixEngine.apply_fixes(..., safe_only=True)` skips unsafe fixes; pass `safe_only=False` to apply them. The `root` component is never fixed because it appears in `skip_names`.

## Edge cases & exemptions
The rule deliberately skips:

- **`root` component name** — listed in the default `skip_names` set. No violation, no fix.
- **Event handler names** — `EVENT_HANDLER` is intentionally omitted from `_get_default_name_extractors`, and `visit_event_handler` is not implemented. Names like `onActionPerformed` are framework-defined.
- **CSS properties** — any property whose path contains `.style.`, `.elementStyle.`, `.textStyle.`, or `.instanceStyle.` is skipped (covers values like `touch-action`, `background-color`, `flex-direction`).
- **Position properties** — any property whose path contains `.position.` is skipped (covers `x`, `y`, `width`, `height`, `basis`, `grow`).
- **`props.aspectRatio`** — skipped via the `.props.aspectRatio` container check.
- **SVG path data** — properties named `d` whose path contains `.props.elements` are skipped (handles both direct `props.elements.d` and array forms like `props.elements[0].d`).
- **Private properties** — properties whose name starts with `_` (and the reserved `_JavaDate`) are filtered out by `LintingRule.applies_to` unless `include_private_properties=True`.
- **Array properties** — flattened JSON collapses `myArray[0]`, `myArray[1]`, … to a single property node, so array properties are validated once on the base name.

These exemptions are implemented in `_should_skip_property` and `_is_private_property`.

## See also
- [NamePatternRule user guide](../../rules/naming/name-pattern.md) — the short version
- [Configuration overview](../../getting-started/configuration.md)
- [Creating Rules](../../developing/creating-rules.md)
