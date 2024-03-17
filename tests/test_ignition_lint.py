import unittest
import os
import sys
import os
from unittest.mock import patch

# Add the src directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ignition_lint import JsonLinter

def get_default_errors():
    return {"components": [], "parameters": [], "scripts": []}

class JsonLinterTests(unittest.TestCase):
    def setUp(self):
        self.linter = JsonLinter("PascalCase", "camelCase", None, None)

    def test_lint_file_with_valid_json(self):
        file_path = "./tests/cases/PreferredStyle/view.json"

        with patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = '{"key": "value"}'
            mock_file.__exit__.return_value = None

            lint_errors = self.linter.lint_file(file_path)

            mock_open.assert_called_once_with(file_path, "r")
            mock_file.read.assert_called_once()
            self.assertEqual(lint_errors, 0)
            self.assertEqual(self.linter.errors, get_default_errors())

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

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, get_default_errors())

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
        expected_errors = get_default_errors()
        expected_errors['components'] = ['root/invalidChildName1']

        self.linter.check_component_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_check_parameter_names_with_valid_parameter_names(self):
        data = {
            "param1": "value1",
            "param2": "value2"
        }

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, get_default_errors())

    def test_check_parameter_names_with_invalid_parameter_names(self):
        data = {
            "Param1": "value1",
            "Param2": "value2"
        }
        expected_errors = get_default_errors()
        expected_errors['parameters'] = ["Param1", "Param2"]

        self.linter.check_parameter_names(data, self.linter.errors)

        self.assertEqual(self.linter.errors, expected_errors)

    def test_lint_file_with_glob_pattern(self):
        valid_file_path = "**/PreferredStyle/view.json"
        invalid_file_path = "nonexistent/**/view.json"

        self.linter.lint_file(valid_file_path)
        self.assertEqual(self.linter.files_linted, 1)

        self.linter.lint_file(invalid_file_path)
        self.assertEqual(self.linter.files_linted, 1)
    
    def test_json_encoded_script_capture(self):
        file_path = "tests/cases/script-confirmation/view.json"
        
        self.linter.lint_file(file_path)
        self.assertEqual(self.linter.errors, get_default_errors())
    
    def test_invalid_json_encoded_script_capture(self):
        data = {
            "meta": {"name": "root"},
            "children": {
                "meta": {"name": "Button"},
                "props": {
                    "params": {
                        "param1": "value1",
                        "param2": "value2"
                    }
                },
                "events": {
                    "component": {
                        "onActionPerformed": {
                            "config": {
                            "script": "\tprint(\"Hello world\") I have invalid syntax! < + -"
                            },
                            "scope": "G",
                            "type": "script"
                        }
                    }
                }
            }
        }
        
        errors = get_default_errors()
        self.linter.check_component_names(data, errors)
        self.assertEqual(len(errors['scripts']), 1)
        

if __name__ == "__main__":
    unittest.main()