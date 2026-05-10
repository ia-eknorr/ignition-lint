"""
Example rule demonstrating mixed severity within a single rule.
This shows how developers can append to both self.errors and self.warnings
based on the severity of different conditions.

SEVERITY GUIDELINES:
- Warnings: Style issues, recommendations, non-breaking problems
- Errors: Functional issues, breaking problems, security concerns

This is an EXAMPLE ONLY - not included in default rule configurations.
"""

from ..common import LintingRule
from ..registry import register_rule
from ...model.node_types import NodeType


@register_rule
class ExampleMixedSeverityRule(LintingRule):
	"""Example rule that can generate both warnings and errors for different conditions."""

	def __init__(self):
		super().__init__({NodeType.COMPONENT})

	@property
	def error_message(self) -> str:
		return "Component validation with mixed severity levels"

	def visit_component(self, node):
		"""
		Check components for different types of issues demonstrating severity levels.

		WARNING examples (style/recommendation issues):
		- Temporary naming patterns
		- Short names that hurt readability
		- Missing descriptive suffixes

		ERROR examples (functional/breaking issues):
		- Names indicating unsafe/test code in production
		- Conflicting naming patterns
		- Names that could cause runtime issues
		"""
		name_lower = node.name.lower()

		# WARNING: Style issue - temporary naming pattern
		if name_lower.startswith(('temp', 'test', 'tmp')):
			self.warnings.append(
				f"{node.path}: Component name '{node.name}' "
				f"uses temporary naming pattern (consider renaming for production)"
			)

		# Check for conflicting indicators first (more specific error)
		conflicting_patterns = [('debug', 'prod'), ('test', 'live'), ('dev', 'production'), ('mock', 'real'),
					('sample', 'actual')]
		has_conflicting_pattern = False
		for pattern1, pattern2 in conflicting_patterns:
			if pattern1 in name_lower and pattern2 in name_lower:
				self.errors.append(
					f"{node.path}: Component name '{node.name}' "
					f"contains conflicting indicators '{pattern1}' and '{pattern2}'"
				)
				has_conflicting_pattern = True
				break

		# ERROR: Functional issue - potentially unsafe component (only if no conflicting pattern found)
		if not has_conflicting_pattern:
			unsafe_patterns = ['unsafe', 'debug', 'admin']
			for pattern in unsafe_patterns:
				if pattern in name_lower:
					self.errors.append(
						f"{node.path}: Component name '{node.name}' "
						f"indicates potentially unsafe or debug functionality"
					)
					break

		# WARNING: Style issue - very short names hurt readability
		if len(node.name) < 3 and not name_lower in ['ok', 'no', 'go', 'id']:
			self.warnings.append(
				f"{node.path}: Component name '{node.name}' "
				f"is very short (consider more descriptive naming)"
			)

		# WARNING: Style recommendation - missing component type suffix
		common_types = ['button', 'label', 'input', 'panel', 'container', 'table', 'chart']
		if (
			len(node.name) > 5 and
			not any(comp_type in node.name.lower() for comp_type in common_types) and
			not node.name.lower().endswith(('btn', 'lbl', 'txt', 'img', 'icon'))
		):
			self.warnings.append(
				f"{node.path}: Component name '{node.name}' "
				f"might benefit from a descriptive suffix (e.g., Button, Label, Panel)"
			)
