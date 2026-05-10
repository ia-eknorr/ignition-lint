"""
Example Rule Implementation

This file demonstrates how to create and register a new linting rule
for ignition-lint without modifying core framework files.
"""

from typing import Set
from ..common import LintingRule
from ..registry import register_rule
from ...model.node_types import ViewNode, NodeType, ALL_BINDINGS


# Example 1: Simple rule using decorator registration
@register_rule
class ExampleNameLengthRule(LintingRule):
	"""
	Example rule that checks if component names are too short.

	This demonstrates the minimum requirements for a custom rule.
	"""

	def __init__(self, min_length: int = 3, target_node_types: Set[NodeType] = None):
		"""Initialize the rule with minimum length requirement."""
		super().__init__(target_node_types or {NodeType.COMPONENT})
		self.min_length = min_length

	@property
	def error_message(self) -> str:
		"""Required property describing what this rule checks."""
		return f"Component names must be at least {self.min_length} characters long"

	def visit_component(self, node: ViewNode):
		"""Called for each component node that matches target_node_types."""
		component_name = node.path.split('.')[-1]

		if len(component_name) < self.min_length:
			self.errors.append(
				f"{node.path}: Component name '{component_name}' is too short "
				f"(minimum {self.min_length} characters)"
			)


# Example 2: More advanced rule with custom configuration preprocessing
class ExampleBindingCountRule(LintingRule):
	"""
	Example rule that checks if components have too many bindings.

	This demonstrates advanced features like custom configuration preprocessing
	and working with different node types.
	"""

	@classmethod
	def preprocess_config(cls, config):
		"""Preprocess configuration before rule instantiation."""
		processed = config.copy()

		# Convert string warning levels to integers
		if 'warning_threshold' in processed and isinstance(processed['warning_threshold'], str):
			processed['warning_threshold'] = int(processed['warning_threshold'])

		if 'error_threshold' in processed and isinstance(processed['error_threshold'], str):
			processed['error_threshold'] = int(processed['error_threshold'])

		return processed

	def __init__(self, warning_threshold: int = 5, error_threshold: int = 10):
		"""Initialize with binding count thresholds."""
		# Target both components and bindings
		super().__init__({NodeType.COMPONENT} | ALL_BINDINGS)

		self.warning_threshold = warning_threshold
		self.error_threshold = error_threshold
		self.component_bindings = {}  # Track bindings per component

	@property
	def error_message(self) -> str:
		return f"Components should not have more than {self.error_threshold} bindings"

	def visit_component(self, node: ViewNode):
		"""Initialize binding count for each component."""
		self.component_bindings[node.path] = 0

	def visit_expression_binding(self, node: ViewNode):
		"""Count expression bindings."""
		self._count_binding(node)

	def visit_property_binding(self, node: ViewNode):
		"""Count property bindings."""
		self._count_binding(node)

	def visit_tag_binding(self, node: ViewNode):
		"""Count tag bindings."""
		self._count_binding(node)

	def _count_binding(self, node: ViewNode):
		"""Helper to count bindings for their parent component."""
		# Find the parent component path
		path_parts = node.path.split('.')
		component_path = None

		# Look for parent component in the path
		for i in range(len(path_parts) - 1, 0, -1):
			potential_path = '.'.join(path_parts[:i])
			if potential_path in self.component_bindings:
				component_path = potential_path
				break

		if component_path:
			self.component_bindings[component_path] += 1

	def post_process(self):
		"""Called after all nodes are processed to generate final errors."""
		for component_path, binding_count in self.component_bindings.items():
			component_name = component_path.split('.')[-1]

			if binding_count >= self.error_threshold:
				self.errors.append(
					f"{component_path}: Component '{component_name}' has {binding_count} bindings "
					f"(exceeds error threshold of {self.error_threshold})"
				)
			elif binding_count >= self.warning_threshold:
				# For warnings, you might want a separate warning list
				# For now, we'll add to errors with a warning prefix
				self.errors.append(
					f"{component_path}: WARNING - Component '{component_name}' has {binding_count} bindings "
					f"(exceeds warning threshold of {self.warning_threshold})"
				)
