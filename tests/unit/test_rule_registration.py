# pylint: disable=import-error
"""
Tests for the rule registry contract.

The registry no longer instantiates rules at registration time, so the
"every registered rule must be constructible with an empty config" contract
is enforced here instead.
"""

import unittest

from ignition_lint.rules import RULES_MAP
from ignition_lint.rules.common import LintingRule
from ignition_lint.rules.registry import RuleValidationError, RuleRegistry


class TestEveryRegisteredRuleInstantiates(unittest.TestCase):
	"""Each registered rule must be usable in its default state (empty config)."""

	def test_every_rule_can_be_instantiated_with_empty_config(self):
		"""Every rule registered in RULES_MAP must build cleanly from an empty config."""
		self.assertGreater(len(RULES_MAP), 0, "Expected at least one registered rule")
		for rule_name, rule_class in RULES_MAP.items():
			with self.subTest(rule=rule_name):
				try:
					instance = rule_class.create_from_config({})
				except Exception as exc:  # pylint: disable=broad-except
					self.fail(f"{rule_name}.create_from_config({{}}) raised {exc!r}")
				self.assertIsInstance(instance, LintingRule)
				self.assertTrue(
					isinstance(instance.error_message, str) and instance.error_message,
					f"{rule_name} must expose a non-empty error_message"
				)


class TestRegistryIsIdempotent(unittest.TestCase):
	"""Registering the same class twice is a no-op; conflicting names raise."""

	def test_same_class_registered_twice_is_noop(self):
		"""Re-registering the same class under the same name returns silently."""
		registry = RuleRegistry()

		class DummyRule(LintingRule):
			error_message = "dummy"

			def __init__(self, **_kwargs):
				super().__init__(set())

		first = registry.register_rule(DummyRule)
		second = registry.register_rule(DummyRule)
		self.assertEqual(first, second)
		self.assertEqual(len(registry.list_rules()), 1)

	def test_different_class_same_name_raises(self):
		"""Registering a different class under an in-use name is an error."""
		registry = RuleRegistry()

		class RuleA(LintingRule):
			error_message = "a"

			def __init__(self, **_kwargs):
				super().__init__(set())

		class RuleB(LintingRule):
			error_message = "b"

			def __init__(self, **_kwargs):
				super().__init__(set())

		registry.register_rule(RuleA, "SharedName")
		with self.assertRaises(RuleValidationError):
			registry.register_rule(RuleB, "SharedName")


class TestMetadataIsLazy(unittest.TestCase):
	"""Metadata is computed only when get_rule_metadata() is called."""

	def test_metadata_not_computed_at_registration(self):
		"""register_rule must not instantiate the rule; metadata is lazy and cached."""
		registry = RuleRegistry()
		instantiations = []

		class TrackingRule(LintingRule):
			error_message = "tracking"

			def __init__(self, **_kwargs):
				super().__init__(set())
				instantiations.append(1)

		registry.register_rule(TrackingRule)
		self.assertEqual(instantiations, [], "register_rule must not instantiate the rule")

		registry.get_rule_metadata("TrackingRule")
		self.assertEqual(len(instantiations), 1, "metadata extraction should instantiate once")

		registry.get_rule_metadata("TrackingRule")
		self.assertEqual(len(instantiations), 1, "metadata should be cached after first access")


if __name__ == "__main__":
	unittest.main()
