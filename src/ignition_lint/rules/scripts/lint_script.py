"""
This module defines a PylintScriptRule class that runs pylint on the scripts contained within a Perspective View.
It collects all script nodes, combines them into a single temporary file, and runs pylint on that file.
"""

import datetime
import glob
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from io import StringIO
from pylint import lint
from pylint.reporters.text import TextReporter

from ..common import ScriptRule, FixableMixin
from ...common.fix_operations import Fix, FixOperation, FixOperationType
from ...model.node_types import ScriptNode, NodeType


@dataclass
class PylintViolation:
	"""
	Structured data for a pylint violation.

	This is a specialized violation type for pylint that stores category-specific information.
	"""
	category: str  # E, W, C, R, F
	code: str  # E0602, W0611, etc.
	message: str  # The violation message
	path: str  # Script path
	line: int  # Line number within script
	severity: str = ''  # Severity level ("error" or "warning") - set by rule


class PylintScriptRule(FixableMixin, ScriptRule):
	"""Rule to run pylint on all script types using the simplified interface."""

	def __init__(
		self, severity="error", pylintrc=None, debug=False, batch_mode=False, *, debug_dir=None,
		category_mapping=None
	):
		super().__init__(severity=severity)  # Targets all script types by default
		self.debug = debug  # Debug mode disabled by default for performance
		self.batch_mode = batch_mode  # Batch mode DISABLED by default for clearer per-file reporting (set to True for faster processing)
		self.debug_dir_config = debug_dir  # User-configured debug directory
		self.current_source_file = None  # Track current file being processed
		self.pylintrc = self._resolve_pylintrc_path(pylintrc)

		# Category mapping: maps pylint categories (E, W, C, R, F) to ignition-lint severity (error, warning)
		# Default: Fatal and Error → error, Warning/Convention/Refactor → warning
		self.category_mapping = category_mapping or {
			'F': 'error',  # Fatal
			'E': 'error',  # Error
			'W': 'warning',  # Warning
			'C': 'warning',  # Convention
			'R': 'warning',  # Refactor
		}

		# Structured storage for pylint violations (for category-grouped output)
		self.pylint_violations: List[PylintViolation] = []

		# Track if debug directory has been cleaned up this run
		self._debug_cleanup_done = False

		if self.debug:
			if self.pylintrc:
				print(f"🔍 PylintScriptRule: Using pylintrc: {self.pylintrc}")
			else:
				print("🔍 PylintScriptRule: No pylintrc found, using inline configuration")
			print(f"🔍 PylintScriptRule: Category mapping: {self.category_mapping}")

	def set_source_file(self, source_file_path: Optional[str]) -> None:
		"""Set the current source file being processed (called by LintEngine)."""
		self.current_source_file = source_file_path

	def _resolve_pylintrc_path(self, pylintrc: Optional[str]) -> Optional[str]:
		"""Resolve the pylintrc file path with fallback to standard location."""
		# If a specific pylintrc is provided, use it if it exists
		if pylintrc:
			if os.path.isabs(pylintrc):
				if os.path.exists(pylintrc):
					return pylintrc
				print(f"⚠️  Warning: Specified pylintrc not found: {pylintrc}")
				print("   Falling back to standard location search...")
			else:
				# Try relative to current working directory
				abs_path = os.path.join(os.getcwd(), pylintrc)
				if os.path.exists(abs_path):
					return abs_path
				print(f"⚠️  Warning: Specified pylintrc not found: {pylintrc}")
				print(f"   Tried: {abs_path}")
				print(f"   Current directory: {os.getcwd()}")
				print("   Falling back to standard location search...")

		# Fall back to standard location: .config/ignition.pylintrc
		# First, search from current directory up to find the project root (user's custom config)
		current_path = os.getcwd()
		while current_path != os.path.dirname(current_path):  # Until we reach root
			standard_pylintrc = os.path.join(current_path, ".config", ".ignition-pylintrc")
			if os.path.exists(standard_pylintrc):
				return standard_pylintrc
			current_path = os.path.dirname(current_path)

		# If not found in user's repo, check the package installation directory
		# This is where the bundled default config will be when installed via pip/poetry
		# __file__ is: site-packages/ignition_lint/rules/scripts/lint_script.py
		# We need to go up to: site-packages/ignition_lint/.config/.pylintrc
		package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
		bundled_pylintrc = os.path.join(package_dir, ".config", ".ignition-pylintrc")
		if os.path.exists(bundled_pylintrc):
			return bundled_pylintrc

		# No pylintrc found - will use pylint defaults or inline config
		return None

	@property
	def error_message(self) -> str:
		return "Pylint detected issues in script"

	def _collect_script(self, node):
		"""Override to include file path in script tracking."""
		if isinstance(node, ScriptNode):
			# Use composite key: file_path::script_path for unique identification
			file_prefix = self.current_source_file if self.current_source_file else "unknown"
			composite_key = f"{file_prefix}::{node.path}"
			self.collected_scripts[composite_key] = node

	def process_nodes(self, nodes):
		"""Override to handle batch mode - don't reset scripts when batching across files."""
		if not self.batch_mode:
			# Non-batch mode: reset everything per file and process immediately
			self.errors = []
			self.warnings = []
			self.pylint_violations = []
			self.collected_scripts = {}
			self.reset_fixes()
		# In batch mode: don't reset anything - accumulate across all files

		# Filter nodes that this rule applies to
		applicable_nodes = [node for node in nodes if self.applies_to(node)]

		# Visit each applicable node (collect scripts)
		for node in applicable_nodes:
			node.accept(self)

		# Call post_process (in batch mode this does nothing)
		self.post_process()

	def post_process(self):
		"""Override to skip processing in batch mode - wait for finalize() instead."""
		if not self.batch_mode:
			# Non-batch mode: process immediately
			if self.collected_scripts:
				self.process_scripts(self.collected_scripts)
				self.collected_scripts = {}
			# Note: Don't clear errors here - they'll be collected by LintEngine after process_nodes

	def finalize(self):
		"""Process all accumulated scripts across all files (batch mode only)."""
		if self.batch_mode and self.collected_scripts:
			self.process_scripts(self.collected_scripts)
			self.collected_scripts = {}
		elif not self.batch_mode:
			# In non-batch mode, errors were already reported during post_process
			# Clear them so they don't get collected again by finalize
			self.errors = []
			self.warnings = []
			self.pylint_violations = []

	def _format_script_path(self, composite_key: str) -> str:
		"""Format script path for error messages, removing file path in non-batch mode."""
		if self.batch_mode:
			# Batch mode: keep full path for clarity across multiple files
			return composite_key
		# Non-batch mode: strip file path prefix (everything before ::)
		if "::" in composite_key:
			return composite_key.split("::", 1)[1]
		return composite_key

	@staticmethod
	def _strip_trailing_whitespace(script_content: str) -> str:
		"""Strip trailing whitespace from each line of a script."""
		return '\n'.join(line.rstrip() for line in script_content.split('\n'))

	def _get_script_content_path(self, node: ScriptNode) -> Optional[str]:
		"""
		Map a script node to its JSON path for the script content value.

		Returns the JSON dict access path (list), or None if not resolvable.
		"""
		if not self._path_translator:
			return None

		# Determine the suffix based on node type
		suffix_candidates = []
		if node.node_type == NodeType.TRANSFORM:
			suffix_candidates = ['.code']
		elif node.node_type == NodeType.EVENT_HANDLER:
			suffix_candidates = ['.config.script', '.script']
		elif node.node_type in (NodeType.MESSAGE_HANDLER, NodeType.CUSTOM_METHOD):
			suffix_candidates = ['.script']

		for suffix in suffix_candidates:
			model_path = f"{node.path}{suffix}"
			json_path = self._path_translator.model_path_to_json_path(model_path)
			if json_path is not None:
				return json_path

		return None

	def _generate_trailing_whitespace_fixes(self, scripts: Dict[str, ScriptNode]):
		"""Generate Fix objects for scripts that have C0303 (trailing-whitespace) violations."""
		if not self.has_fix_context or self.batch_mode:
			return

		# Collect composite keys that have C0303 violations
		affected_keys = {v.path for v in self.pylint_violations if v.code == 'C0303'}
		if not affected_keys:
			return

		for composite_key in affected_keys:
			if composite_key not in scripts:
				continue

			node = scripts[composite_key]
			original = node.script
			stripped = self._strip_trailing_whitespace(original)

			if stripped == original:
				continue

			json_path = self._get_script_content_path(node)
			if json_path is None:
				continue

			display_path = self._format_script_path(composite_key)
			fix = Fix(
				rule_name='PylintScriptRule',
				violation_message=f"{display_path}: Trailing whitespace (C0303)",
				description=f"Remove trailing whitespace from script at {display_path}",
				operations=[
					FixOperation(
						operation=FixOperationType.SET_VALUE,
						json_path=json_path,
						old_value=original,
						new_value=stripped,
						description="Strip trailing whitespace from all lines",
					)
				],
				is_safe=True,
			)
			self.add_fix(fix)

	def get_category_grouped_violations(self) -> Dict[str, Dict[str, List[str]]]:
		"""
		Get violations grouped by category with severity mapping information.

		Returns:
			Dict with structure:
			{
				'F': {'severity': 'error', 'name': 'Fatal', 'violations': [...]},
				'E': {'severity': 'error', 'name': 'Error', 'violations': [...]},
				...
			}
		"""
		category_names = {
			'F': 'Fatal',
			'E': 'Error',
			'W': 'Warning',
			'C': 'Convention',
			'R': 'Refactor',
		}

		# Group violations by category
		grouped = {}
		for violation in self.pylint_violations:
			if violation.category not in grouped:
				grouped[violation.category] = {
					'severity': self.category_mapping.get(violation.category, self.severity),
					'name': category_names.get(violation.category, violation.category),
					'violations': []
				}

			formatted_path = self._format_script_path(violation.path)
			message = f"{formatted_path}: Line {violation.line}: {violation.message} ({violation.code})"
			grouped[violation.category]['violations'].append(message)

		# Sort categories: F, E, W, C, R
		category_order = ['F', 'E', 'W', 'C', 'R']
		return {cat: grouped[cat] for cat in category_order if cat in grouped}

	def format_violations_grouped(self) -> Optional[Dict[str, str]]:
		"""
		Format violations grouped by category for display.

		This method provides custom formatting for pylint violations,
		grouping them by category (Fatal, Error, Warning, Convention, Refactor).

		Returns:
			Dictionary with 'warnings' and 'errors' keys containing formatted strings,
			or None if no violations.
		"""
		grouped = self.get_category_grouped_violations()

		if not grouped:
			return None

		warnings_lines = []
		errors_lines = []

		# Format each category, splitting by severity
		for category, data in grouped.items():
			# Category header (no emoticons for cleaner output)
			category_output = [f"\n    Pylint - {data['name']} ({category}):"]

			# Violations
			for violation in data['violations']:
				category_output.append(f"      • {violation}")

			# Add to appropriate severity list
			if data['severity'] == "error":
				errors_lines.extend(category_output)
			else:
				warnings_lines.extend(category_output)

		return {
			"warnings": '\n'.join(warnings_lines) if warnings_lines else None,
			"errors": '\n'.join(errors_lines) if errors_lines else None
		}

	def process_scripts(self, scripts: Dict[str, ScriptNode]):
		"""Process all collected scripts with pylint."""
		# Clean up debug directory from previous runs (only done once per run)
		self._cleanup_debug_directory()

		# Quick exit: Skip processing if there are no scripts
		if not scripts:
			return

		# Quick exit: Skip if all scripts are empty
		if all(not script.script.strip() for script in scripts.values()):
			return

		# Check for improperly indented scripts (data quality issue)
		for composite_key, script_obj in scripts.items():
			if script_obj.script.strip():
				# Check if script lacks proper indentation (skip comment-only lines)
				lines = script_obj.script.split('\n')
				first_code_line = next(
					(line for line in lines if line.strip() and not line.strip().startswith('#')),
					None
				)
				if first_code_line and not (
					first_code_line.startswith('\t') or first_code_line.startswith('    ')
				):
					# Script is not indented - this is a data quality issue
					self.add_violation(
						f"{self._format_script_path(composite_key)}: Script lacks proper indentation in view.json "
						"(scripts should be indented with tabs or spaces for valid Python syntax)"
					)

				# Check for mixed tabs and spaces in indentation (data quality issue)
				# Look for lines that have both tabs AND spaces in their leading whitespace
				for line in lines:
					if line.strip():  # Skip empty lines
						leading_whitespace = line[:len(line) - len(line.lstrip())]
						if '\t' in leading_whitespace and ' ' in leading_whitespace:
							self.add_violation(
								f"{self._format_script_path(composite_key)}: Script mixes tabs and spaces for indentation. "
								"Use either tabs OR spaces consistently."
							)
							break  # Only report once per script

		# Run pylint on all scripts at once (with auto-fixed indentation)
		# Note: _run_pylint_batch populates self.pylint_violations with structured data
		_path_to_issues = self._run_pylint_batch(scripts)

		# Generate auto-fixes for trailing whitespace violations
		self._generate_trailing_whitespace_fixes(scripts)

		# Add placeholder violations for counting purposes (won't be displayed due to custom formatting)
		# This ensures file counts are correct
		for violation in self.pylint_violations:
			# Map pylint category to ignition-lint severity
			severity = self.category_mapping.get(violation.category, self.severity)
			# Add empty placeholder - format_violations_grouped() will provide actual display
			self.add_violation("", severity=severity)

	def _run_pylint_batch(self, scripts: Dict[str, ScriptNode]) -> Dict[str, List[str]]:
		"""Run pylint on multiple scripts at once."""
		combined_content, line_map = self._combine_scripts(scripts)
		path_to_issues = {path: [] for path in scripts.keys()}
		temp_file_path = None
		try:
			temp_file_path = self._create_temp_file(combined_content)
			pylint_output = self._run_pylint_on_file(temp_file_path)
			self._parse_pylint_output(pylint_output, line_map, path_to_issues)
		except (OSError, IOError) as e:
			error_msg = f"Error with file operations during pylint: {str(e)}"
			self._handle_pylint_error(error_msg, path_to_issues)
		except ImportError as e:
			error_msg = f"Error importing pylint modules: {str(e)}"
			self._handle_pylint_error(error_msg, path_to_issues)
		finally:
			self._cleanup_temp_file(temp_file_path, path_to_issues)

		return path_to_issues

	def _cleanup_debug_directory(self) -> None:
		"""Clean up debug directory at the start of a run (called once per run)."""
		if self._debug_cleanup_done:
			return

		try:
			debug_dir = self._get_debug_directory()
			if os.path.exists(debug_dir):
				# Remove all .py files from previous runs
				for debug_file in glob.glob(os.path.join(debug_dir, "*.py")):
					try:
						os.remove(debug_file)
					except OSError:
						pass  # Ignore errors removing individual files

				# Also remove pylintrc info files
				for info_file in glob.glob(os.path.join(debug_dir, "pylintrc_used.txt")):
					try:
						os.remove(info_file)
					except OSError:
						pass

				if self.debug:
					print(f"🧹 Cleaned up debug directory: {debug_dir}")

			self._debug_cleanup_done = True
		except (OSError, IOError):
			# If cleanup fails, just continue - not critical
			self._debug_cleanup_done = True

	def _get_debug_directory(self) -> str:
		"""Determine debug directory path without creating it. Called lazily only when needed."""
		cwd = os.getcwd()

		# Priority 1: User-configured debug directory
		if self.debug_dir_config:
			if os.path.isabs(self.debug_dir_config):
				return self.debug_dir_config
			return os.path.join(cwd, self.debug_dir_config)

		# Priority 2: Try to detect if we're in a test environment and use tests/debug
		current_path = cwd
		while current_path != os.path.dirname(current_path):  # Until we reach root
			if os.path.basename(current_path) == 'tests':
				# We're in tests directory
				return os.path.join(current_path, "debug")
			if os.path.exists(os.path.join(current_path, 'tests')):
				# Tests directory exists in current path
				return os.path.join(current_path, "tests", "debug")
			current_path = os.path.dirname(current_path)

		# Priority 3: Use .ignition-lint/debug as standard location for user repos
		return os.path.join(cwd, ".ignition-lint", "debug")

	def _combine_scripts(self, scripts: Dict[str, ScriptNode]) -> Tuple[str, Dict[int, str]]:
		"""Combine all scripts into a single string with line mapping."""
		line_map = {}
		line_count = 1

		combined_scripts = [
			"#pylint: disable=unused-argument,missing-docstring,redefined-outer-name,function-redefined",
			"# Stub for common globals, and to simulate the Ignition environment",
			"# Note: function-redefined is disabled because multiple scripts may define the same function names",
			"system = None  # Simulated Ignition system object",
			"self = {} # Simulated self object for script context",
			"event = {}  # Simulated event object",
			"",
		]
		line_count += len(combined_scripts)

		# Track current file and script number per file
		current_file = None
		script_num_in_file = 0

		for composite_key, script_obj in scripts.items():
			# Parse composite key: file_path::script_path
			if "::" in composite_key:
				file_path, script_path = composite_key.split("::", 1)

				# Check if we've moved to a new file
				if file_path != current_file:
					current_file = file_path
					script_num_in_file = 1
				else:
					script_num_in_file += 1

				header = f"# File: {file_path}\n# Script {script_num_in_file}: {script_path}"
			else:
				# Fallback for non-composite keys
				script_num_in_file += 1
				header = f"# Script {script_num_in_file}: {composite_key}"
				script_path = composite_key

			combined_scripts.append(header)
			line_count += 2 if "::" in composite_key else 1  # Account for 2-line header

			formatted_script = script_obj.get_formatted_script()
			script_lines = formatted_script.count('\n') + 1

			# Record line numbers for this script (use composite key for full context)
			for line_num in range(line_count, line_count + script_lines):
				line_map[line_num] = composite_key

			combined_scripts.append(formatted_script)
			line_count += script_lines

			combined_scripts.append("")  # Blank line separator
			line_count += 1

		return "\n".join(combined_scripts), line_map

	def _create_temp_file(self, content: str) -> str:
		"""Create temporary file with script content. Uses PID for uniqueness in parallel execution."""
		timestamp = datetime.datetime.now().strftime("%H%M%S")
		pid = os.getpid()
		with tempfile.NamedTemporaryFile(
			prefix=f"{timestamp}_pid{pid}_", suffix=".py", delete=False
		) as temp_file:
			temp_file.write(content.encode('utf-8'))
			return temp_file.name

	def _run_pylint_on_file(self, temp_file_path: str) -> str:
		"""Execute pylint on the temporary file and return output."""
		pylint_output = StringIO()

		# Build pylint arguments
		args = []

		# Use custom or standard pylintrc if available
		if self.pylintrc:
			args.extend(['--rcfile', self.pylintrc])
		else:
			# Fallback to inline configuration if no pylintrc found
			args.extend([
				'--disable=all',
				'--enable=unused-import,undefined-variable,syntax-error,invalid-name',
			])

		# Common arguments
		args.extend([
			'--output-format=text',
			'--score=no',
			'--module-rgx=.*',  # Allow any module name (temp files have timestamps + PID)
			temp_file_path,
		])

		# Redirect stdout/stderr to capture all pylint output
		old_stdout = sys.stdout
		old_stderr = sys.stderr
		try:
			sys.stdout = pylint_output
			sys.stderr = pylint_output
			lint.Run(args, reporter=TextReporter(pylint_output), exit=False)
		finally:
			sys.stdout = old_stdout
			sys.stderr = old_stderr

		return pylint_output.getvalue()

	def _parse_pylint_output(
		self, output: str, line_map: Dict[int, str], path_to_issues: Dict[str, List[str]]
	) -> None:
		"""Parse pylint output and map issues back to original scripts."""
		# Enhanced pattern to capture category and code: E0602, W0611, etc.
		# Example line: test.py:10:5: E0602: Undefined variable 'x' (undefined-variable)
		pattern = r'.*:(\d+):\d+: ([EWCRF]\d+): (.+)'
		for line in output.splitlines():
			match = re.match(pattern, line)
			if not match:
				continue

			try:
				line_num = int(match.group(1))
				code = match.group(2)  # E0602, W0611, etc.
				message = match.group(3)  # Rest of the message
				category = code[0]  # E, W, C, R, or F

				script_path = self._find_script_for_line(line_num, line_map)

				if script_path and script_path in path_to_issues:
					relative_line = self._calculate_relative_line(line_num, script_path, line_map)

					# Store structured violation for category-grouped output
					violation = PylintViolation(
						category=category, code=code, message=message, path=script_path,
						line=relative_line
					)
					self.pylint_violations.append(violation)

					# Also add to path_to_issues for backward compatibility
					path_to_issues[script_path].append(f"Line {relative_line}: {message} ({code})")

			except (ValueError, IndexError) as e:
				if self.debug:
					print(
						f"⚠️  Warning: Error parsing pylint output line: {line}\n  Exception: {str(e)}"
					)

	def _find_script_for_line(self, line_num: int, line_map: Dict[int, str]) -> Optional[str]:
		"""Find which script a line number belongs to."""
		for ln in sorted(line_map.keys(), reverse=True):
			if ln <= line_num:
				return line_map[ln]
		return None

	def _calculate_relative_line(self, line_num: int, script_path: str, line_map: Dict[int, str]) -> int:
		"""Calculate the relative line number within the original script."""
		script_start_line = min(ln for ln, path in line_map.items() if path == script_path)
		return line_num - script_start_line + 1

	def _handle_pylint_error(self, error_msg: str, path_to_issues: Dict[str, List[str]]) -> None:
		"""Handle and log pylint execution errors."""
		if self.debug:
			print(f"⚠️  Pylint error: {error_msg}")
		for path in path_to_issues:
			path_to_issues[path].append(error_msg)

	def _cleanup_temp_file(self, temp_file_path: str, path_to_issues: Dict[str, List[str]]) -> None:
		"""Clean up temporary file. Only saves to debug dir if debug=True OR there are issues."""
		if not temp_file_path or not os.path.exists(temp_file_path):
			return

		has_issues = any(issues for issues in path_to_issues.values())
		should_save_debug = has_issues or self.debug

		if should_save_debug:
			try:
				# Lazily create debug directory only when actually needed
				debug_dir = self._get_debug_directory()
				os.makedirs(debug_dir, exist_ok=True)

				# Preserve original temp filename (timestamp + PID + random chars)
				original_filename = os.path.basename(temp_file_path)
				debug_file_path = os.path.join(debug_dir, original_filename)

				# Copy temp file to debug directory
				shutil.copyfile(temp_file_path, debug_file_path)

				# Save additional debug info if in debug mode
				if self.debug:
					print(f"🔍 Debug directory: {debug_dir}")
					# Write pylintrc info
					pylintrc_file = os.path.join(debug_dir, "pylintrc_used.txt")
					with open(pylintrc_file, 'w', encoding='utf-8') as f:
						if self.pylintrc:
							f.write(f"Using pylintrc: {self.pylintrc}\n")
						else:
							f.write("No pylintrc found - using inline configuration\n")

				# Print appropriate message
				if has_issues:
					print(f"🐛 Pylint found issues. Debug file saved to: {debug_file_path}")
				elif self.debug:
					print(f"🔍 Debug mode: Script saved to: {debug_file_path}")

			except (OSError, IOError) as e:
				if self.debug:
					print(f"⚠️  Warning: Could not save debug file: {str(e)}")

		# Always clean up the temp file from /tmp/ (was already copied to debug if needed)
		try:
			os.remove(temp_file_path)
		except OSError:
			# Silently ignore if file was already deleted
			pass
