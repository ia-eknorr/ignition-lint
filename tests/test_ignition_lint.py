""" This module contains the tests for the Ignition Lint tool. """

import unittest
import os
import sys
from unittest.mock import patch
from io import StringIO

# Add the src directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import ignition_lint  # pylint: disable=wrong-import-position, import-error


class JsonLinterTests(unittest.TestCase):
    """Tests for the JsonLinter class."""

    def setUp(self):
        self.linter = ignition_lint.JsonLinter(
            "PascalCase", "camelCase", None, None, False
        )

    def test_lint_file_with_valid_json(self):
        """Test the lint_file method with a valid JSON file."""
        file_path = "./tests/cases/PreferredStyle/view.json"
        expected_errors = {"components": [], "parameters": []}

        with patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = '{"key": "value"}'
            mock_file.__exit__.return_value = None

            lint_errors = self.linter.lint_file(file_path)

            mock_open.assert_called_once_with(file_path, "r", encoding="utf-8")
            mock_file.read.assert_called_once()
            self.assertEqual(lint_errors, 0)
            self.assertEqual(self.linter.errors, expected_errors)

    def test_lint_file_with_invalid_json(self):
        """Test the lint_file method with an invalid JSON file."""
        file_path = "./nonexistent/test/view.json"
        expected_errors = 0

        with patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = '{"key": "value}'
            mock_file.__exit__.return_value = None

            errors = self.linter.lint_file(file_path)

            self.assertEqual(errors, expected_errors)

    def test_check_component_names_with_valid_component_names(self):
        """Test the check_component_names method with valid component names."""
        data = {
            "meta": {"name": "root"},
            "children": {
                "meta": {"ValidName": "value"},
                "props": {"params": {"param1": "value1", "param2": "value2"}},
            },
        }
        expected_errors = {"components": [], "parameters": []}

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_component_names_with_invalid_component_names(self):
        """Test the check_component_names method with invalid component names."""
        data = {
            "meta": {"name": "root"},
            "children": {
                "meta": {"name": "invalidChildName1"},
                "props": {"params": {"param1": "value1", "param2": "value2"}},
            },
        }
        expected_errors = {"components": ["root/invalidChildName1"], "parameters": []}

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_valid_parameter_names(self):
        """Test the check_parameter_names method with valid parameter names."""
        data = {"param1": "value1", "param2": "value2"}
        expected_errors = {"components": [], "parameters": []}

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_invalid_parameter_names(self):
        """Test the check_parameter_names method with invalid parameter names."""
        data = {"Param1": "value1", "Param2": "value2"}
        expected_errors = {"components": [], "parameters": ["Param1", "Param2"]}

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_dataset(self):
        """Test the check_parameter_names method with a dataset."""
        data = {
            "$": ["ds", 192, 1723242356734],
            "$columns": [
                {
                    "name": "City",
                    "type": "String",
                    "data": [
                        "New York",
                        "Los Angeles",
                        "Chicago",
                        "Houston",
                        "Phoenix",
                    ],
                },
                {
                    "name": "Population",
                    "type": "Integer",
                    "data": [8363710, 3833995, 2853114, 2242193, 1567924],
                },
                {
                    "name": "Timezone",
                    "type": "String",
                    "data": ["EST", "PST", "CST", "CST", "MST"],
                },
                {"name": "GMTOffset", "type": "Integer", "data": [-5, -8, -6, -6, -7]},
            ],
        }

        # Should skip the $ key, yielding no errors
        expected_errors = {"components": [], "parameters": []}

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_main_with_multiple_files(self):
        """Test the main function with multiple files."""
        file_paths = [
            "./tests/cases/camelCase/view.json",
            "./tests/cases/PascalCase/view.json",
        ]
        expected_errors = {
            "./tests/cases/camelCase/view.json": [
                "- root/iconCamelCase",
                "- view.custom.customViewParam",
                "- view.params.viewParam",
                "- root/iconCamelCase.custom.componentCustomParam",
                "- root.custom.rootCustomParam",
            ],
            "./tests/cases/PascalCase/view.json": [],
        }
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch(
                "sys.argv",
                ["ignition_lint.py", "--files"]
                + [",".join(file_paths)]
                + [
                    "--component-style",
                    "PascalCase",
                    "--parameter-style",
                    "PascalCase",
                ],
            ):
                try:
                    ignition_lint.main()
                except SystemExit:
                    pass

                output = mock_stdout.getvalue().strip()
                lines = output.split("\n")

            errors_dict = {file_path: [] for file_path in file_paths}

            for line in lines:
                if line.startswith("Error in file: "):
                    current_file_path = line.replace("Error in file: ", "").strip()
                elif line.strip().startswith("-"):
                    errors_dict[current_file_path].append(line.strip())

            self.assertEqual(
                len(errors_dict[file_paths[0]]), len(expected_errors[file_paths[0]])
            )
            self.assertEqual(
                len(errors_dict[file_paths[1]]), len(expected_errors[file_paths[1]])
            )

    def test_lint_file_with_glob_pattern(self):
        """Test the lint_file method with a glob pattern."""
        valid_file_path = "**/PreferredStyle/view.json"
        invalid_file_path = "nonexistent/**/view.json"

        self.linter.lint_file(valid_file_path)
        self.assertEqual(self.linter.files_linted, 1)

        self.linter.lint_file(invalid_file_path)
        self.assertEqual(self.linter.files_linted, 1)


if __name__ == "__main__":
    unittest.main()
