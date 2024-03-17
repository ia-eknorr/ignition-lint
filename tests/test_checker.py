import unittest
import sys
import os

# Add the src directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from checker import StyleChecker

class StyleCheckerTests(unittest.TestCase):
    def test_is_snake_case(self):
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
        checker = StyleChecker("any")
        self.assertTrue(checker.is_correct_style("my_variable"))
        self.assertTrue(checker.is_correct_style("myVariable"))
        self.assertTrue(checker.is_correct_style("MyVariable"))
        self.assertTrue(checker.is_correct_style("MY_VARIABLE"))
        self.assertTrue(checker.is_correct_style("my_variable_123"))
        self.assertTrue(checker.is_correct_style("MyVariable123"))
        self.assertTrue(checker.is_correct_style("myVariable123"))                                                 
        self.assertTrue(checker.is_correct_style("MY_VARIABLE_123"))
    

if __name__ == "__main__":
    unittest.main()