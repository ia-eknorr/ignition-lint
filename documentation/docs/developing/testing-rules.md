---
title: Testing rules
sidebar_label: Testing rules
description: Unit, integration, and golden-file tests for custom rules
---

# Testing rules

The framework ships with a test harness designed to make rule testing fast and consistent. New rules should ship with unit tests at minimum; integration tests and case fixtures follow if the rule is non-trivial.

## Test layout

```
tests/
├── unit/                    # Per-rule unit tests
├── integration/             # Multi-rule, CLI, end-to-end
│   └── configs/             # Config-driven integration test data
├── cases/                   # view.json fixtures
├── fixtures/                # Test helpers and base classes
│   ├── base_test.py         # BaseRuleTest
│   └── test_helpers.py      # get_test_config, create_mock_view, etc.
├── debug/                   # Generated debug output (gitignored)
└── test_runner.py           # CLI test runner
```

## Running tests

All test commands run from `tests/`:

```bash
cd tests

# Everything
poetry run python test_runner.py --run-all

# Unit only (fastest)
poetry run python test_runner.py --run-unit

# Integration only
poetry run python test_runner.py --run-integration

# Config-driven integration tests
poetry run python test_runner.py --run-config

# A specific test file
poetry run python test_runner.py --test my_rule

# Setup test directories and sample configs
poetry run python test_runner.py --setup
```

You can also use unittest directly:

```bash
# From tests/
poetry run python -m unittest unit.test_my_rule -v

# From repo root
poetry run python -m unittest discover tests
```

## Unit tests with `BaseRuleTest`

Inherit from `BaseRuleTest` (located in `tests/fixtures/base_test.py`) — it sets up paths, loads test cases, and provides assertion helpers.

```python
# tests/unit/test_my_rule.py
import unittest
from tests.fixtures.base_test import BaseRuleTest
from tests.fixtures.test_helpers import get_test_config


class TestMyRule(BaseRuleTest):
    def setUp(self):
        super().setUp()  # IMPORTANT — sets up paths and config
        self.rule_config = get_test_config("MyRule", min_length=5)

    def test_passes_valid_case(self):
        view = self.test_cases_dir / "PascalCase" / "view.json"
        self.assert_rule_passes(view, self.rule_config, "MyRule")

    def test_fails_invalid_case(self):
        view = self.test_cases_dir / "MixedCase" / "view.json"
        self.assert_rule_fails(view, self.rule_config, "MyRule")
```

### `BaseRuleTest` provides

| Attribute / method | Purpose |
| --- | --- |
| `self.test_cases_dir` | Path to `tests/cases/` |
| `self.assert_rule_passes(view, config, rule_name)` | Asserts no violations |
| `self.assert_rule_fails(view, config, rule_name, expected_count=None)` | Asserts at least one violation (or an exact count) |
| `self.run_rule_on_view(view_content, config, rule_name)` | Run the rule and return its violations |
| `self.run_rule_on_file(view_file, config, rule_name)` | Run on a file path |

## Test helpers

`tests/fixtures/test_helpers.py`:

### `get_test_config(rule_name, **kwargs) → dict`

Builds a minimal config for one rule:

```python
config = get_test_config("MyRule", min_length=5, severity="warning")
# {"MyRule": {"enabled": True, "kwargs": {"min_length": 5, "severity": "warning"}}}
```

### `create_mock_view(structure) → str`

Generates view.json content from a dict — useful for unit tests that don't need a full fixture file:

```python
view_content = create_mock_view({
    "root": {
        "type": "@root",
        "children": [
            {
                "type": "ia.display.button",
                "name": "TestButton",
                "props": {"text": "Click Me"},
            }
        ]
    }
})

errors = self.run_rule_on_view(view_content, self.rule_config, "MyRule")
self.assertEqual(len(errors), 0)
```

### `load_test_view(case_name) → str`

Loads a fixture from `tests/cases/<case_name>/view.json`:

```python
view = load_test_view("PascalCase")
```

## Case fixtures

`tests/cases/` holds real view.json files used by both unit tests and integration tests. Each case is a directory:

```
tests/cases/
├── PascalCase/
│   └── view.json          # Valid PascalCase example
├── MixedCase/
│   └── view.json          # Invalid — mixed naming
├── ExpressionBindings/
│   └── view.json          # Polling-violation examples
├── BadComponentReferences/
│   └── view.json          # Bad-traversal examples
└── ...
```

When adding a fixture for a new rule:

1. Create `tests/cases/<MyCase>/view.json` with the minimum structure that exercises the rule
2. Reference it from your unit tests via `self.test_cases_dir / "<MyCase>" / "view.json"`
3. Regenerate debug files: `python scripts/generate_debug_files.py <MyCase>`
4. Commit both the fixture and its generated `debug/` artifacts

## Config-driven integration tests

Tests under `tests/integration/configs/<category>/` drive runs from JSON, allowing many test scenarios per rule without writing more Python:

```
tests/integration/configs/
├── naming/
│   └── name_pattern_tests.json
├── performance/
│   └── polling_interval_tests.json
└── cross-rule/
    └── warnings_vs_errors.json
```

Each JSON file contains a list of test cases:

```json
[
  {
    "name": "PascalCase positive",
    "view": "tests/cases/PascalCase/view.json",
    "config": {
      "NamePatternRule": {
        "enabled": true,
        "kwargs": {"convention": "PascalCase"}
      }
    },
    "expect_errors": 0,
    "expect_warnings": 0
  },
  {
    "name": "MixedCase negative",
    "view": "tests/cases/MixedCase/view.json",
    "config": {
      "NamePatternRule": {
        "enabled": true,
        "kwargs": {"convention": "PascalCase"}
      }
    },
    "expect_errors": 0,
    "expect_warnings_min": 1
  }
]
```

Run them via `python test_runner.py --run-config`.

## Golden-file tests

`tests/unit/test_golden_files.py` validates that the model-building pipeline produces consistent output. For every case under `tests/cases/<Name>/`:

- `flattened.json` — flattening output
- `model.json` — serialized object model
- `stats.json` — statistics

These are committed reference files. The test compares freshly generated artifacts against the committed ones; any drift fails the test.

### When you change something that affects model output

1. Update the case (or the framework code)
2. Regenerate the golden files:
   ```bash
   python scripts/generate_debug_files.py <CaseName>
   # Or for everything:
   python scripts/generate_debug_files.py
   ```
3. Review the diff carefully — does it match what you intended?
4. Run golden-file tests:
   ```bash
   cd tests && poetry run python -m unittest unit.test_golden_files -v
   ```
5. Commit both the framework change and the regenerated golden files

Skipping step 4 is the most common cause of CI failures after model-builder changes.

## Testing rules with auto-fix

Auto-fixes need their own test pattern — exercise the fix path explicitly:

```python
def test_generates_fix(self):
    config = get_test_config("MyRule")
    view_path = self.test_cases_dir / "MyCase" / "view.json"

    # Run with fix mode active
    fixes = self.run_rule_with_fixes(view_path, config, "MyRule")

    self.assertEqual(len(fixes), 1)
    self.assertTrue(fixes[0].is_safe)
    self.assertEqual(fixes[0].operations[0].new_value, "ExpectedValue")
```

`tests/unit/test_fix_framework.py` is the reference for fix-aware tests.

## Local CI testing

Before pushing, run GitHub Actions locally with `act`:

```bash
scripts/test-actions.sh ci          # Full CI pipeline
scripts/test-actions.sh unittest    # Unit tests only
```

See [GitHub Actions](../usage/github-actions.md#testing-workflows-locally-with-act) for setup.

## Best practices

- **Write the failing test first.** Small TDD cycles catch design issues early.
- **Test correct AND problematic cases.** A rule that always passes is invisible until something breaks the test setup.
- **Use real fixtures over mocks** for non-trivial rules. `create_mock_view` is for unit-test edge cases; case fixtures are for behavior validation.
- **Test severity routing explicitly.** Confirm your rule reports to `errors` vs `warnings` correctly.
- **For preprocessing logic, test it directly:** `MyRule.preprocess_config({"target_node_types": "component"})` should produce the expected output.
- **Pin the violation count.** `assert_rule_fails(..., expected_count=3)` catches off-by-one regressions that `expected_count >= 1` misses.

## See also

- [Creating rules](./creating-rules.md) — building the rule itself
- [Architecture](./architecture.md) — what the model under test looks like
- [Debug output](../usage/debug-output.md) — golden file generation in depth
- [Troubleshooting](./troubleshooting.md) — common test failures
