"""Tests for the StyleChecker class."""
import unittest
import sys
import os

# Add the src directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from checker import StyleChecker # pylint: disable=wrong-import-position

class StyleCheckerTests(unittest.TestCase):
    """Tests for the StyleChecker class."""

    def test_is_snake_case(self):
        """Test the is_snake_case method."""
        checker = StyleChecker("snake_case")
        self.assertTrue(checker.is_correct_style("my_variable"))
        self.assertFalse(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("myVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertTrue(checker.is_correct_style("my_variable_123"))
        self.assertFalse(checker.is_correct_style("MyVariable123"))
        self.assertFalse(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))

    def test_is_camel_case(self):
        """Test the is_camel_case method."""
        checker = StyleChecker("camelCase")
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertTrue(checker.is_correct_style("myVariable"))
        self.assertFalse(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertFalse(checker.is_correct_style("MyVariable123"))
        self.assertTrue(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))

    def test_is_pascal_case(self):
        """Test the is_pascal_case method."""
        checker = StyleChecker("PascalCase")
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertFalse(checker.is_correct_style("myVariable"))
        self.assertTrue(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertTrue(checker.is_correct_style("MyVariable123"))
        self.assertFalse(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))

    def test_is_upper_case(self):
        """Test the is_upper_case method."""
        checker = StyleChecker("UPPER_CASE")
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertFalse(checker.is_correct_style("myVariable"))
        self.assertFalse(checker.is_correct_style("MyVariable"))
        self.assertTrue(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertFalse(checker.is_correct_style("MyVariable123"))
        self.assertFalse(checker.is_correct_style("myVariable123"))
        self.assertTrue(checker.is_correct_style("MY_VARIABLE_123"))

    def test_is_any(self):
        """Test the is_any method."""
        checker = StyleChecker("any")
        self.assertTrue(checker.is_correct_style("my_variable"))
        self.assertTrue(checker.is_correct_style("myVariable"))
        self.assertTrue(checker.is_correct_style("MyVariable"))
        self.assertTrue(checker.is_correct_style("MY_VARIABLE"))
        self.assertTrue(checker.is_correct_style("my_variable_123"))
        self.assertTrue(checker.is_correct_style("MyVariable123"))
        self.assertTrue(checker.is_correct_style("myVariable123"))
        self.assertTrue(checker.is_correct_style("MY_VARIABLE_123"))

    def test_is_camel_case_with_acronyms(self):
        """Test the is_camel_case method with acronyms allowed."""
        checker = StyleChecker("camelCase", True)
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertTrue(checker.is_correct_style("myVariable"))
        self.assertFalse(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertFalse(checker.is_correct_style("MyVariable123"))
        self.assertTrue(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))
        self.assertTrue(checker.is_correct_style("myVAR1"))
        self.assertTrue(checker.is_correct_style("VAR1"))
        self.assertTrue(checker.is_correct_style("variable"))
        self.assertTrue(checker.is_correct_style("USPopulation"))
        self.assertTrue(checker.is_correct_style("myVAR"))
        self.assertTrue(checker.is_correct_style("myVAR1a"))
        self.assertTrue(checker.is_correct_style("VAR1A"))

    def test_is_pascal_case_with_acronyms(self):
        """Test the is_pascal_case method with acronyms allowed."""
        checker = StyleChecker("PascalCase", True)
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertFalse(checker.is_correct_style("myVariable"))
        self.assertTrue(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertTrue(checker.is_correct_style("MyVariable123"))
        self.assertFalse(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))
        self.assertFalse(checker.is_correct_style("myVAR1"))
        self.assertTrue(checker.is_correct_style("VAR1"))
        self.assertTrue(checker.is_correct_style("Variable"))
        self.assertTrue(checker.is_correct_style("USPopulation"))
        self.assertTrue(checker.is_correct_style("MyVAR"))
        self.assertFalse(checker.is_correct_style("MyVAR1a"))
        self.assertTrue(checker.is_correct_style("VAR1A"))

    def test_is_title_case_with_acronyms(self):
        """Test the is_title_case method with acronyms allowed."""
        checker = StyleChecker("Title Case", True)
        self.assertFalse(checker.is_correct_style("my_variable"))
        self.assertFalse(checker.is_correct_style("myVariable"))
        self.assertFalse(checker.is_correct_style("MyVariable"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE"))
        self.assertFalse(checker.is_correct_style("my_variable_123"))
        self.assertFalse(checker.is_correct_style("MyVariable123"))
        self.assertFalse(checker.is_correct_style("myVariable123"))
        self.assertFalse(checker.is_correct_style("MY_VARIABLE_123"))
        self.assertFalse(checker.is_correct_style("myVAR1"))
        self.assertFalse(checker.is_correct_style("VAR1"))
        self.assertTrue(checker.is_correct_style("Variable"))
        self.assertFalse(checker.is_correct_style("USPopulation"))
        self.assertFalse(checker.is_correct_style("MyVAR"))
        self.assertFalse(checker.is_correct_style("MyVAR1a"))
        self.assertFalse(checker.is_correct_style("VAR1A"))
        self.assertTrue(checker.is_correct_style("US Population"))
        self.assertTrue(checker.is_correct_style("My Variable"))
        self.assertTrue(checker.is_correct_style("My Var 1"))
        self.assertTrue(checker.is_correct_style("Var 1A"))
        self.assertTrue(checker.is_correct_style("My Variable But Longer"))


if __name__ == "__main__":
    unittest.main()
