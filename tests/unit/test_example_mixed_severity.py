# pylint: disable=import-error
"""
Test cases for ExampleMixedSeverityRule demonstrating warnings vs errors.
This serves as both a test and a demonstration of how to test mixed-severity rules.
"""

from fixtures.base_test import BaseRuleTest
from fixtures.test_helpers import get_test_config, create_mock_view, create_temp_view_file

# Example rules live under rules/_examples and are excluded from auto-discovery.
# Importing the module here triggers @register_rule so the test can look it up by name.
import ignition_lint.rules._examples.example_mixed_severity  # noqa: F401  pylint: disable=unused-import


class TestExampleMixedSeverityRule(BaseRuleTest):
	"""Test the ExampleMixedSeverityRule to demonstrate mixed severity testing."""

	def test_warnings_for_style_issues(self):
		"""Test that style issues produce warnings."""
		# Create a view with style issues
		components = [
			{
				"name": "tempButton",
				"type": "button"
			},  # WARNING: temp naming
			{
				"name": "x",
				"type": "label"
			},  # WARNING: very short name
			{
				"name": "MyComponent",
				"type": "container"
			}  # WARNING: no type suffix
		]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Should have warnings but no errors
		self.assert_rule_summary(
			mock_view, rule_config, "ExampleMixedSeverityRule", expected_warnings=3, expected_errors=0
		)

	def test_errors_for_functional_issues(self):
		"""Test that functional issues produce errors."""
		# Create a view with functional issues
		components = [
			{
				"name": "UnsafeComponent",
				"type": "container"
			},  # ERROR: unsafe name
			{
				"name": "DebugProdPanel",
				"type": "panel"
			}  # ERROR: conflicting indicators
		]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Should have errors and may have warnings (components trigger suffix warning too)
		self.assert_rule_summary(
			mock_view, rule_config, "ExampleMixedSeverityRule", expected_warnings=1, expected_errors=2
		)  # UnsafeComponent gets suffix warning

	def test_mixed_warnings_and_errors(self):
		"""Test a view that triggers both warnings and errors."""
		# Create a view with both types of issues
		components = [
			{
				"name": "tempButton",
				"type": "button"
			},  # WARNING: temp naming
			{
				"name": "AdminPanel",
				"type": "panel"
			},  # ERROR: potentially unsafe
			{
				"name": "x",
				"type": "label"
			},  # WARNING: short name
			{
				"name": "TestLiveComponent",
				"type": "container"
			}  # ERROR: conflicting indicators
		]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Should have both warnings and errors
		# 4 warnings: tempButton (temp), TestLiveComponent (temp+suffix), x (short)
		self.assert_rule_summary(
			mock_view, rule_config, "ExampleMixedSeverityRule", expected_warnings=4, expected_errors=2
		)

	def test_clean_components_pass(self):
		"""Test that well-named components pass completely."""
		# Create a view with good component names
		components = [{
			"name": "SubmitButton",
			"type": "button"
		}, {
			"name": "UserNameLabel",
			"type": "label"
		}, {
			"name": "DataPanel",
			"type": "panel"
		}, {
			"name": "MainContainer",
			"type": "container"
		}]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Should pass completely
		self.assert_rule_passes_completely(mock_view, rule_config, "ExampleMixedSeverityRule")

	def test_warning_patterns(self):
		"""Test that warnings contain expected patterns."""
		components = [{"name": "tempLogin", "type": "container"}]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Check warning content
		# 2 warnings: tempLogin (temp naming + missing suffix)
		self.assert_rule_warnings(
			mock_view, rule_config, "ExampleMixedSeverityRule", expected_warning_count=2,
			warning_patterns=["temporary naming pattern", "consider renaming"]
		)

	def test_error_patterns(self):
		"""Test that errors contain expected patterns."""
		components = [{"name": "DebugComponent", "type": "container"}]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Check error content
		self.assert_rule_errors(
			mock_view, rule_config, "ExampleMixedSeverityRule", expected_error_count=1,
			error_patterns=["potentially unsafe", "debug functionality"]
		)

	def test_exception_cases(self):
		"""Test that certain short names are allowed."""
		# Test that common short names don't trigger warnings
		components = [
			{
				"name": "ok",
				"type": "button"
			},  # Should not warn - common short name
			{
				"name": "id",
				"type": "label"
			},  # Should not warn - common short name
			{
				"name": "go",
				"type": "button"
			}  # Should not warn - common short name
		]
		mock_view_content = create_mock_view(components)
		mock_view = create_temp_view_file(mock_view_content)

		rule_config = get_test_config("ExampleMixedSeverityRule")

		# Should pass completely
		self.assert_rule_passes_completely(mock_view, rule_config, "ExampleMixedSeverityRule")
