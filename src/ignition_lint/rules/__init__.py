"""
Linting rules package for ignition-lint.

This module provides the rule system infrastructure and built-in rules
for linting Ignition Perspective view files. It includes the dynamic rule
registration system and auto-discovery of custom rules.
"""

from collections.abc import Mapping

from .common import LintingRule, NodeVisitor, BindingRule
from .registry import register_rule, get_registry, get_all_rules, discover_rules

# Import and register built-in rules
from .scripts.lint_script import PylintScriptRule
from .performance.polling_interval import PollingIntervalRule
from .naming.name_pattern import NamePatternRule
from .structure.bad_component_reference import BadComponentReferenceRule

# Auto-discover and register all rules in this package
_discovered_rules = discover_rules()


def get_rules_map():
	"""Return a snapshot dict of the current rules map."""
	return get_all_rules()


class _LiveRulesMap(Mapping):
	"""
	Read-only Mapping view backed by the live registry.

	Exists so consumers can keep using `RULES_MAP[name]` / `name in RULES_MAP`
	while still seeing rules that get registered after this module is imported
	(e.g. test-only rules under rules/_examples imported explicitly by a test).
	"""

	def __getitem__(self, key):
		return get_registry().get_all_rules()[key]

	def __iter__(self):
		return iter(get_registry().get_all_rules())

	def __len__(self):
		return len(get_registry().get_all_rules())

	def __contains__(self, key):
		return get_registry().is_registered(key)

	def __repr__(self):
		return f"_LiveRulesMap({dict(self)!r})"


RULES_MAP = _LiveRulesMap()

__all__ = [
	"LintingRule",
	"NodeVisitor",
	"BindingRule",
	"PylintScriptRule",
	"PollingIntervalRule",
	"NamePatternRule",
	"BadComponentReferenceRule",
	"RULES_MAP",
	"register_rule",
	"get_registry",
	"get_all_rules",
	"discover_rules",
]
