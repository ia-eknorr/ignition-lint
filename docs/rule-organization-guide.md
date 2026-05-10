# Rule Organization and Development Guide

This document defines the organizational structure for ignition-lint rules and provides guidelines for developers to extend the framework using test-driven development principles.

## Table of Contents
- [Rule Folder Structure](#rule-folder-structure)
- [Test Structure](#test-structure)
- [Development Workflow](#development-workflow)
- [Category Definitions](#category-definitions)
- [Migration Guide](#migration-guide)

## Rule Folder Structure

The rules are organized by functional category to provide clear separation of concerns and easy navigation as the codebase scales to hundreds of rules.

### Recommended Structure

```
src/ignition_lint/rules/
├── __init__.py                  # Package initialization
├── common.py                    # Base LintingRule class and utilities
├── registry.py                  # Rule registration system
│
├── _examples/                   # Example rules for learning and testing
│   │                            # (underscore prefix excludes from auto-discovery)
│   ├── __init__.py
│   ├── example_rule.py         # Simple rule examples
│   └── example_mixed_severity.py
│
├── naming/                      # Naming convention rules
│   ├── __init__.py
│   ├── name_pattern.py         # Component naming patterns
│   └── component_naming.py     # Advanced component naming rules
│
├── performance/                 # Performance-related rules
│   ├── __init__.py
│   ├── polling_interval.py     # Binding polling interval validation
│   ├── binding_optimization.py # Binding performance rules
│   └── resource_usage.py       # Resource consumption rules
│
├── structure/                   # Component structure and references
│   ├── __init__.py
│   ├── bad_component_reference.py # Invalid component references
│   ├── layout_validation.py    # Layout structure rules
│   └── hierarchy_rules.py      # Component hierarchy validation
│
├── properties/                  # Property-specific rules
│   ├── __init__.py
│   ├── unused_custom_properties.py # Unused property detection
│   ├── property_validation.py  # Property value validation
│   └── binding_properties.py   # Property binding rules
│
├── scripts/                     # Script-related rules
│   ├── __init__.py
│   ├── lint_script.py         # Script quality via pylint
│   ├── script_security.py     # Script security rules
│   └── script_performance.py  # Script performance rules
│
├── security/                    # Security-focused rules
│   ├── __init__.py
│   ├── sql_injection_check.py # SQL injection detection
│   ├── xss_prevention.py      # XSS prevention rules
│   └── data_exposure.py       # Data exposure validation
│
└── accessibility/              # Accessibility rules
    ├── __init__.py
    ├── screen_reader.py        # Screen reader compatibility
    └── keyboard_navigation.py  # Keyboard navigation rules
```

## Test Structure

The test structure mirrors the rule organization to provide clear mapping between rules and their tests, supporting effective test-driven development.

### Recommended Test Structure

```
tests/
├── __init__.py
├── test_runner.py              # Main test runner
├── README.md                   # Test documentation
│
├── fixtures/                   # Shared test utilities
│   ├── __init__.py
│   ├── base_test.py           # BaseRuleTest class
│   ├── config_framework.py    # Configuration test utilities
│   ├── test_helpers.py        # Common test helpers
│   └── configs/               # Test configuration files
│       ├── component_naming_tests.json
│       ├── polling_interval_tests.json
│       └── script_linting_tests.json
│
├── cases/                      # Test case view.json files
│   ├── BadComponentReferences/
│   ├── ExpressionBindings/
│   ├── LineDashboard/
│   └── [other test cases]/
│
├── unit/                       # Unit tests mirroring rule structure
│   ├── __init__.py
│   ├── test_golden_files.py   # Golden file regression tests
│   │
│   ├── examples/              # Tests for example rules
│   │   ├── __init__.py
│   │   ├── test_example_rule.py
│   │   └── test_example_mixed_severity.py
│   │
│   ├── naming/                # Tests for naming rules
│   │   ├── __init__.py
│   │   ├── test_name_pattern.py
│   │   └── test_component_naming.py
│   │
│   ├── performance/           # Tests for performance rules
│   │   ├── __init__.py
│   │   ├── test_polling_interval.py
│   │   └── test_binding_optimization.py
│   │
│   ├── structure/             # Tests for structure rules
│   │   ├── __init__.py
│   │   ├── test_bad_component_reference.py
│   │   └── test_layout_validation.py
│   │
│   ├── properties/            # Tests for property rules
│   │   ├── __init__.py
│   │   ├── test_unused_custom_properties.py
│   │   └── test_property_validation.py
│   │
│   ├── scripts/               # Tests for script rules
│   │   ├── __init__.py
│   │   ├── test_lint_script.py
│   │   └── test_script_security.py
│   │
│   ├── security/              # Tests for security rules
│   │   ├── __init__.py
│   │   ├── test_sql_injection_check.py
│   │   └── test_xss_prevention.py
│   │
│   └── accessibility/         # Tests for accessibility rules
│       ├── __init__.py
│       ├── test_screen_reader.py
│       └── test_keyboard_navigation.py
│
└── integration/               # Integration tests
    ├── __init__.py
    ├── test_config_framework.py
    ├── test_cli_integration.py
    └── test_rule_interaction.py
```

## Development Workflow

### Test-Driven Development (TDD) Process

The framework follows strict TDD principles for rule development:

#### 1. Create Test First
```bash
# Navigate to tests directory
cd tests

# Create test file in appropriate category
# Example: tests/unit/naming/test_my_new_rule.py
```

#### 2. Write Failing Test
```python
# tests/unit/naming/test_my_new_rule.py
import unittest
from tests.fixtures.base_test import BaseRuleTest
from src.ignition_lint.rules.naming.my_new_rule import MyNewRule

class TestMyNewRule(BaseRuleTest):
    def setUp(self):
        super().setUp()
        self.rule = MyNewRule()

    def test_should_fail_invalid_naming(self):
        # Arrange
        view_data = self.create_mock_view_with_component("invalid-name")

        # Act
        self.rule.visit(view_data)

        # Assert
        self.assertEqual(len(self.rule.errors), 1)
        self.assertIn("invalid-name", self.rule.errors[0])
```

#### 3. Run Test (Should Fail)
```bash
# From tests directory
python test_runner.py --test naming/test_my_new_rule
```

#### 4. Implement Rule
```python
# src/ignition_lint/rules/naming/my_new_rule.py
from ..common import LintingRule
from ..registry import register_rule
from ...model.node_types import NodeType

@register_rule
class MyNewRule(LintingRule):
    def __init__(self):
        super().__init__({NodeType.COMPONENT})

    @property
    def error_message(self) -> str:
        return "Component names should use PascalCase"

    def visit_component(self, component):
        if not component.name[0].isupper():
            self.errors.append(f"{component.path}: {self.error_message}")
```

#### 5. Run Test (Should Pass)
```bash
# From tests directory
python test_runner.py --test naming/test_my_new_rule
```

#### 6. Refactor and Add Edge Cases
Add additional test cases and refine implementation.

#### 7. Integration Testing
```bash
# From tests directory
python test_runner.py --run-integration
```

### File Naming Conventions

#### Rules
- **File names**: `snake_case.py` (e.g., `name_pattern.py`)
- **Class names**: `PascalCase` ending in `Rule` (e.g., `NamePatternRule`)
- **One primary rule per file** (multiple related rules in same file are acceptable)

#### Tests
- **File names**: `test_` + rule file name (e.g., `test_name_pattern.py`)
- **Class names**: `Test` + rule class name (e.g., `TestNamePatternRule`)
- **Method names**: `test_` + descriptive scenario (e.g., `test_should_flag_camelCase_components`)

## Category Definitions

### naming/
Rules that validate naming conventions for components, properties, and other named elements.
- Component naming patterns (PascalCase, camelCase, etc.)
- Property naming conventions
- Consistent naming across related elements

### performance/
Rules that identify performance issues and optimization opportunities.
- Binding polling intervals
- Resource usage patterns
- Expensive operations detection
- Memory leak prevention

### structure/
Rules that validate component structure, hierarchy, and references.
- Component reference validation
- Layout structure requirements
- Hierarchy depth limits
- Circular reference detection

### properties/
Rules that validate component properties and their usage.
- Unused property detection
- Property value validation
- Required property enforcement
- Property type checking

### scripts/
Rules that analyze and validate embedded scripts.
- Script quality via static analysis
- Security vulnerability detection
- Performance optimization
- Best practice enforcement

### security/
Rules focused on security vulnerabilities and best practices.
- SQL injection prevention
- XSS vulnerability detection
- Data exposure risks
- Authentication/authorization issues

### accessibility/
Rules that ensure accessibility compliance and best practices.
- Screen reader compatibility
- Keyboard navigation support
- Color contrast requirements
- ARIA attribute validation

### examples/
Educational rules demonstrating framework capabilities and patterns.
- Simple rule examples for learning
- Complex rule patterns
- Integration examples
- Testing demonstrations

## Import Patterns

### For Rules in Subdirectories
```python
# Rules in subdirectories use relative imports to core files
from ..common import LintingRule
from ..registry import register_rule
from ...model.node_types import NodeType, ViewNode
```

### For Tests
```python
# Tests import from the full path
from src.ignition_lint.rules.naming.name_pattern import NamePatternRule
from tests.fixtures.base_test import BaseRuleTest
```

## Migration Guide

### Migrating Existing Rules

1. **Identify Category**: Determine which category the rule belongs to
2. **Create Directory**: If the category doesn't exist, create it with `__init__.py`
3. **Move Rule File**: Move the rule file to the appropriate subdirectory
4. **Update Imports**: Adjust relative imports in the rule file
5. **Move Test File**: Move corresponding test to the matching test subdirectory
6. **Update Test Imports**: Adjust imports in the test file
7. **Run Tests**: Verify everything works with the test runner

### Example Migration

```bash
# Before
src/ignition_lint/rules/name_pattern.py
tests/unit/test_name_pattern.py

# After
src/ignition_lint/rules/naming/name_pattern.py
tests/unit/naming/test_name_pattern.py
```

```python
# Update imports in rule file
# Before:
from .common import LintingRule
from .registry import register_rule

# After:
from ..common import LintingRule
from ..registry import register_rule
```

```python
# Update imports in test file
# Before:
from src.ignition_lint.rules.name_pattern import NamePatternRule

# After:
from src.ignition_lint.rules.naming.name_pattern import NamePatternRule
```

## Best Practices

### Rule Development
1. **One Primary Responsibility**: Each rule should focus on a single concern
2. **Clear Error Messages**: Provide actionable error messages with context
3. **Performance Conscious**: Avoid expensive operations in rule logic
4. **Configurable**: Make rules configurable where appropriate
5. **Well Documented**: Include docstrings explaining the rule's purpose

### Test Development
1. **Comprehensive Coverage**: Test happy path, edge cases, and error conditions
2. **Isolated Tests**: Each test should be independent and repeatable
3. **Descriptive Names**: Test names should clearly describe the scenario
4. **Use Fixtures**: Leverage shared test utilities and fixtures
5. **Fast Execution**: Keep unit tests fast by using mocks where appropriate

### Documentation
1. **Update This Guide**: When adding new categories, update this documentation
2. **Rule Documentation**: Each rule should have clear docstrings
3. **Example Usage**: Provide configuration examples for complex rules
4. **Migration Notes**: Document any breaking changes or migration requirements

This organizational structure provides a scalable foundation for rule development while maintaining clear separation of concerns and supporting effective test-driven development practices.
