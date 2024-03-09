import unittest
import os
import sys
import os
from unittest.mock import patch
from json import JSONDecodeError

# Add the src directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ignition_lint import JsonLinter

class JsonLinterTests(unittest.TestCase):
    def setUp(self):
        self.linter = JsonLinter("PascalCase", "camelCase", None, None)

    def test_lint_file_with_valid_json(self):
        file_path = "./tests/cases/PreferredStyle/view.json"
        expected_errors = {"components": [], "parameters": []}

        with patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = '{"key": "value"}'
            mock_file.__exit__.return_value = None

            lint_errors = self.linter.lint_file(file_path)

            mock_open.assert_called_once_with(file_path, "r")
            mock_file.read.assert_called_once()
            self.assertEqual(lint_errors, 0)
            self.assertEqual(self.linter.errors, expected_errors)

    def test_lint_file_with_invalid_json(self):
        file_path = "./nonexistent/test/view.json"
        expected_errors = 0

        with patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = '{"key": "value}'
            mock_file.__exit__.return_value = None

            errors = self.linter.lint_file(file_path)

            self.assertEqual(errors, expected_errors)

    def test_check_component_names_with_valid_component_names(self):
        data = {
            "meta": {"name": "root"},
            "children": {
                "meta": {"ValidName": "value"},
                "props": {
                    "params": {
                        "param1": "value1",
                        "param2": "value2"
                    }
                }
            }
        }
        expected_errors = {"components": [], "parameters": []}

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_component_names_with_invalid_component_names(self):
        data = {
            "meta": {"name": "root"},
            "children": {
                "meta": {"name": "invalidChildName1"},
                "props": {
                    "params": {
                        "param1": "value1",
                        "param2": "value2"
                    }
                }
            }
        }
        expected_errors = {'components': ['root/invalidChildName1'], 'parameters': []}

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_valid_parameter_names(self):
        data = {
            "param1": "value1",
            "param2": "value2"
        }
        expected_errors = {"components": [], "parameters": []}

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_invalid_parameter_names(self):
        data = {
            "Param1": "value1",
            "Param2": "value2"
        }
        expected_errors = {"components": [], "parameters": ["Param1", "Param2"]}

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

if __name__ == "__main__":
    unittest.main()