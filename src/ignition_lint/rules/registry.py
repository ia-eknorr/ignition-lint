"""
Rule Registration System for ignition-lint

This module provides a dynamic rule registration system that allows developers
to register new linting rules without modifying core framework files.
"""

import inspect
import importlib
from pathlib import Path
from typing import Dict, Type, Set, Optional, List, Any
from .common import LintingRule


class RuleValidationError(Exception):
	"""Raised when a rule fails validation during registration."""


class RuleRegistry:
	"""
	Central registry for managing linting rules.

	Provides dynamic rule discovery, registration, and validation.
	"""

	def __init__(self):
		"""Initialize the rule registry."""
		self._rules: Dict[str, Type[LintingRule]] = {}
		self._validated_rules: Set[str] = set()
		self._rule_metadata: Dict[str, Dict[str, Any]] = {}

	def register_rule(self, rule_class: Type[LintingRule], rule_name: Optional[str] = None) -> str:
		"""
		Register a rule class with the registry.

		Idempotent: registering the same class object under the same name is a
		silent no-op. Registering a *different* class under an already-used name
		raises RuleValidationError.

		Args:
			rule_class: The rule class to register
			rule_name: Optional custom name for the rule (defaults to class name)

		Returns:
			The registered rule name

		Raises:
			RuleValidationError: If the rule fails validation or a different class
				is already registered under the same name.
		"""
		if not rule_name:
			rule_name = rule_class.__name__

		existing = self._rules.get(rule_name)
		if existing is rule_class:
			return rule_name
		if existing is not None:
			raise RuleValidationError(
				f"Rule name {rule_name} is already registered to a different class "
				f"({existing.__module__}.{existing.__name__})"
			)

		# Validate the rule (static checks only — no instantiation)
		self._validate_rule(rule_class, rule_name)

		# Register the rule. Metadata is computed lazily in get_rule_metadata().
		self._rules[rule_name] = rule_class
		self._validated_rules.add(rule_name)

		return rule_name

	def get_rule(self, rule_name: str) -> Optional[Type[LintingRule]]:
		"""Get a rule class by name."""
		return self._rules.get(rule_name)

	def get_all_rules(self) -> Dict[str, Type[LintingRule]]:
		"""Get all registered rules."""
		return self._rules.copy()

	def list_rules(self) -> List[str]:
		"""List all registered rule names."""
		return list(self._rules.keys())

	def get_rule_metadata(self, rule_name: str) -> Optional[Dict[str, Any]]:
		"""Get metadata for a specific rule. Computed lazily on first access."""
		if rule_name not in self._rules:
			return None
		if rule_name not in self._rule_metadata:
			self._rule_metadata[rule_name] = self._extract_rule_metadata(self._rules[rule_name])
		return self._rule_metadata[rule_name]

	def is_registered(self, rule_name: str) -> bool:
		"""Check if a rule is registered."""
		return rule_name in self._rules

	def discover_and_register_rules(self, package_path: Optional[Path] = None) -> List[str]:
		"""
		Discover and register rules from a package.

		Args:
			package_path: Path to search for rules (defaults to current rules package)

		Returns:
			List of discovered and registered rule names
		"""
		if package_path is None:
			package_path = Path(__file__).parent

		discovered_rules = []

		# Walk through Python files in the package recursively
		for py_file in package_path.rglob("*.py"):
			if py_file.name in ["__init__.py", "registry.py", "common.py"]:
				continue

			# Skip private subpackages (e.g. _examples) — they are intentionally
			# excluded from auto-discovery. Test code may still import them directly.
			relative_path = py_file.relative_to(package_path)
			if any(part.startswith("_") for part in relative_path.parts[:-1]):
				continue

			try:
				# Import the module - build the correct module path for subdirectories
				module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
				module_name = f"ignition_lint.rules.{'.'.join(module_parts)}"
				module = importlib.import_module(module_name)

				# Find rule classes in the module
				for name, obj in inspect.getmembers(module, inspect.isclass):
					# Check if it's a rule class (inherits from LintingRule, not LintingRule itself)
					if (
						issubclass(obj, LintingRule) and obj is not LintingRule and
						obj.__module__ == module_name
					):

						try:
							rule_name = self.register_rule(obj)
							discovered_rules.append(rule_name)
						except RuleValidationError as e:
							print(f"Warning: Skipped invalid rule {name}: {e}")

			except ImportError as e:
				print(f"Warning: Could not import {py_file}: {e}")

		return discovered_rules

	def _validate_rule(self, rule_class: Type[LintingRule], rule_name: str) -> None:
		"""
		Validate that a rule class meets the structural requirements.

		Static checks only — does not instantiate the rule. The contract that a
		rule can be created from an empty config is verified by the test suite,
		not at registration time.

		Args:
			rule_class: Rule class to validate
			rule_name: Name the rule will be registered under

		Raises:
			RuleValidationError: If validation fails
		"""
		if not inspect.isclass(rule_class):
			raise RuleValidationError(f"Rule {rule_name} must be a class")

		if not issubclass(rule_class, LintingRule):
			raise RuleValidationError(f"Rule {rule_name} must inherit from LintingRule")

		if rule_class is LintingRule:
			raise RuleValidationError("Cannot register the base LintingRule class")

		if not hasattr(rule_class, 'error_message'):
			raise RuleValidationError(f"Rule {rule_name} must implement error_message property")

		if not callable(getattr(rule_class, 'create_from_config', None)):
			raise RuleValidationError(f"Rule {rule_name} must define create_from_config")

	def _extract_rule_metadata(self, rule_class: Type[LintingRule]) -> Dict[str, Any]:
		"""Extract metadata from a rule class."""
		metadata = {
			'class_name': rule_class.__name__,
			'module': rule_class.__module__,
			'docstring': inspect.getdoc(rule_class),
		}

		# Try to get source file path
		try:
			metadata['source_file'] = inspect.getfile(rule_class)
		except (TypeError, OSError):
			metadata['source_file'] = None

		# Try to get error message
		try:
			instance = rule_class.create_from_config({})
			metadata['error_message'] = instance.error_message
		except (TypeError, ValueError, AttributeError):
			metadata['error_message'] = None

		return metadata


# Global registry instance
_global_registry = RuleRegistry()


def register_rule(rule_class: Type[LintingRule], rule_name: Optional[str] = None) -> Type[LintingRule]:
	"""
	Decorator and function for registering rules.

	Usage:
		@register_rule
		class MyRule(LintingRule):
			...

		# or
		register_rule(MyRule)

		# or with custom name
		register_rule(MyRule, "CustomRuleName")
	"""
	_global_registry.register_rule(rule_class, rule_name)
	return rule_class  # Return the class for proper decorator behavior


def get_registry() -> RuleRegistry:
	"""Get the global rule registry."""
	return _global_registry


def get_all_rules() -> Dict[str, Type[LintingRule]]:
	"""Get all registered rules from the global registry."""
	return _global_registry.get_all_rules()


def discover_rules() -> List[str]:
	"""Discover and register all rules in the rules package."""
	return _global_registry.discover_and_register_rules()
