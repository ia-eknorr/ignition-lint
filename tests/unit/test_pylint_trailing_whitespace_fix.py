# pylint: disable=import-error,wrong-import-position,protected-access
"""
Unit tests for PylintScriptRule trailing-whitespace (C0303) auto-fix.

Tests cover:
- Static helper strips trailing whitespace
- No fixes generated when fix mode is off
- Fix generation for scripts with trailing whitespace
- One fix per script (not per C0303 line)
- End-to-end: apply fix then re-lint to confirm C0303 gone
- process_nodes resets fixes in non-batch mode
"""

import os
import sys
import tempfile
import unittest
from collections import OrderedDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ignition_lint.rules.scripts.lint_script import PylintScriptRule
from src.ignition_lint.common.fix_operations import FixOperationType
from src.ignition_lint.common.path_translator import PathTranslator
from src.ignition_lint.common.flatten_json import flatten_json
from src.ignition_lint.common.fix_engine import FixEngine
from src.ignition_lint.linter import LintEngine


def _make_pylintrc():
	"""Create a temporary pylintrc that only enables trailing-whitespace."""
	tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.pylintrc', delete=False, encoding='utf-8')
	tmp.write(
		"[MAIN]\n"
		"load-plugins=\n"
		"\n"
		"[MESSAGES CONTROL]\n"
		"disable=all\n"
		"enable=trailing-whitespace\n"
		"\n"
		"[FORMAT]\n"
		"indent-string='\\t'\n"
		"max-line-length=200\n"
	)
	tmp.close()
	return tmp.name


def _make_view_with_event_handler(script_content):
	"""Build a minimal view.json with a single event handler script."""
	return OrderedDict([
		(
			'root',
			OrderedDict([
				(
					'children', [
						OrderedDict([
							(
								'events',
								OrderedDict([
									(
										'component',
										OrderedDict([
											(
												'onActionPerformed',
												OrderedDict([
													(
														'config',
														OrderedDict([
															(
																'script',
																script_content
															),
														])
													),
													('scope', 'G'),
													(
														'type',
														'script'
													),
												])
											),
										])
									),
								])
							),
							('meta', OrderedDict([('name', 'TestButton')])),
							('props', OrderedDict()),
							('type', 'ia.input.button'),
						]),
					]
				),
				('meta', OrderedDict([('name', 'root')])),
				('props', OrderedDict()),
				('type', 'ia.container.flex'),
			])
		),
	])


class TestStripTrailingWhitespace(unittest.TestCase):
	"""Test the static _strip_trailing_whitespace helper."""

	def test_strips_spaces_and_tabs(self):
		"""Should strip trailing spaces and tabs from each line."""
		script = "\tx = 1   \n\ty = 2\t\n\tz = 3"
		result = PylintScriptRule._strip_trailing_whitespace(script)
		self.assertEqual(result, "\tx = 1\n\ty = 2\n\tz = 3")

	def test_preserves_clean_script(self):
		"""Should return identical string when no trailing whitespace exists."""
		script = "\tx = 1\n\ty = 2"
		result = PylintScriptRule._strip_trailing_whitespace(script)
		self.assertEqual(result, script)

	def test_handles_empty_string(self):
		"""Should handle empty string without error."""
		self.assertEqual(PylintScriptRule._strip_trailing_whitespace(""), "")

	def test_handles_blank_lines(self):
		"""Should strip whitespace-only lines to empty lines."""
		script = "\tx = 1\n   \n\ty = 2"
		result = PylintScriptRule._strip_trailing_whitespace(script)
		self.assertEqual(result, "\tx = 1\n\n\ty = 2")


class TestNoFixWithoutContext(unittest.TestCase):
	"""Fixes should not be generated when fix mode is off."""

	@classmethod
	def setUpClass(cls):
		cls.pylintrc = _make_pylintrc()

	@classmethod
	def tearDownClass(cls):
		os.unlink(cls.pylintrc)

	def test_no_fix_without_fix_context(self):
		"""No Fix objects when path_translator / json_context are not set."""
		script = "\tx = 1   \n\ty = 2\t"
		json_data = _make_view_with_event_handler(script)
		flattened = flatten_json(json_data)

		rule = PylintScriptRule(pylintrc=self.pylintrc)
		engine = LintEngine([rule])

		# Process WITHOUT fix context
		results = engine.process(flattened, source_file_path='test.json')

		self.assertEqual(len(results.fixes), 0)


class TestGeneratesFixForTrailingWhitespace(unittest.TestCase):
	"""Fix generation for scripts with trailing whitespace."""

	@classmethod
	def setUpClass(cls):
		cls.pylintrc = _make_pylintrc()

	@classmethod
	def tearDownClass(cls):
		os.unlink(cls.pylintrc)

	def test_generates_fix(self):
		"""Should produce a Fix with is_safe=True and SET_VALUE operation."""
		script = "\tx = 1   \n\ty = 2\t"
		json_data = _make_view_with_event_handler(script)
		flattened = flatten_json(json_data)
		translator = PathTranslator(json_data)

		rule = PylintScriptRule(pylintrc=self.pylintrc)
		engine = LintEngine([rule])

		results = engine.process(
			flattened,
			source_file_path='test.json',
			json_data=json_data,
			path_translator=translator,
		)

		self.assertGreater(len(results.fixes), 0)
		fix = results.fixes[0]
		self.assertTrue(fix.is_safe)
		self.assertEqual(fix.rule_name, 'PylintScriptRule')
		self.assertEqual(len(fix.operations), 1)
		op = fix.operations[0]
		self.assertEqual(op.operation, FixOperationType.SET_VALUE)
		self.assertEqual(op.old_value, script)
		# New value should have whitespace stripped
		self.assertEqual(op.new_value, "\tx = 1\n\ty = 2")


class TestOneFixPerScript(unittest.TestCase):
	"""Multiple C0303 lines in one script should produce exactly one Fix."""

	@classmethod
	def setUpClass(cls):
		cls.pylintrc = _make_pylintrc()

	@classmethod
	def tearDownClass(cls):
		os.unlink(cls.pylintrc)

	def test_one_fix_per_script(self):
		"""Multiple trailing-whitespace lines → one Fix, not N fixes."""
		script = "\tx = 1   \n\ty = 2   \n\tz = 3   "
		json_data = _make_view_with_event_handler(script)
		flattened = flatten_json(json_data)
		translator = PathTranslator(json_data)

		rule = PylintScriptRule(pylintrc=self.pylintrc)
		engine = LintEngine([rule])

		results = engine.process(
			flattened,
			source_file_path='test.json',
			json_data=json_data,
			path_translator=translator,
		)

		# Exactly one fix, even though 3 lines have C0303
		pylint_fixes = [f for f in results.fixes if f.rule_name == 'PylintScriptRule']
		self.assertEqual(len(pylint_fixes), 1)


class TestFixApplicationEndToEnd(unittest.TestCase):
	"""Apply fix then re-lint: C0303 should be gone."""

	@classmethod
	def setUpClass(cls):
		cls.pylintrc = _make_pylintrc()

	@classmethod
	def tearDownClass(cls):
		os.unlink(cls.pylintrc)

	def test_fix_then_relint(self):
		"""After applying the fix, re-linting should find zero C0303 violations."""
		script = "\tx = 1   \n\ty = 2\t"
		json_data = _make_view_with_event_handler(script)
		flattened = flatten_json(json_data)
		translator = PathTranslator(json_data)

		rule = PylintScriptRule(pylintrc=self.pylintrc)
		engine = LintEngine([rule])

		# First pass: detect and fix
		results = engine.process(
			flattened,
			source_file_path='test.json',
			json_data=json_data,
			path_translator=translator,
		)
		self.assertGreater(len(results.fixes), 0)

		# Apply fixes to json_data
		fix_engine = FixEngine(translator)
		fix_result = fix_engine.apply_fixes(results.fixes, safe_only=True)
		self.assertGreater(fix_result.applied_count, 0)

		# Re-flatten and re-lint
		flattened2 = flatten_json(json_data)
		translator2 = PathTranslator(json_data)
		rule2 = PylintScriptRule(pylintrc=self.pylintrc)
		engine2 = LintEngine([rule2])

		results2 = engine2.process(
			flattened2,
			source_file_path='test.json',
			json_data=json_data,
			path_translator=translator2,
		)

		# No C0303 violations should remain
		c0303 = [v for v in rule2.pylint_violations if v.code == 'C0303']
		self.assertEqual(len(c0303), 0)
		self.assertEqual(len(results2.fixes), 0)


class TestProcessNodesResetsFixes(unittest.TestCase):
	"""Non-batch mode should clear fixes between files."""

	@classmethod
	def setUpClass(cls):
		cls.pylintrc = _make_pylintrc()

	@classmethod
	def tearDownClass(cls):
		os.unlink(cls.pylintrc)

	def test_resets_between_files(self):
		"""Fixes from file 1 should not leak into file 2 results."""
		script = "\tx = 1   "
		json_data = _make_view_with_event_handler(script)
		flattened = flatten_json(json_data)
		translator = PathTranslator(json_data)

		rule = PylintScriptRule(pylintrc=self.pylintrc)
		engine = LintEngine([rule])

		# Process first file (produces fixes)
		results1 = engine.process(
			flattened,
			source_file_path='file1.json',
			json_data=json_data,
			path_translator=translator,
		)
		fix_count_1 = len(results1.fixes)
		self.assertGreater(fix_count_1, 0)

		# Process a clean file (no trailing whitespace)
		clean_script = "\tx = 1\n\ty = 2"
		clean_json = _make_view_with_event_handler(clean_script)
		clean_flat = flatten_json(clean_json)
		clean_translator = PathTranslator(clean_json)

		results2 = engine.process(
			clean_flat,
			source_file_path='file2.json',
			json_data=clean_json,
			path_translator=clean_translator,
		)

		# Second file should have zero fixes
		self.assertEqual(len(results2.fixes), 0)


if __name__ == '__main__':
	unittest.main()
