"""Module for checking naming styles of variables, functions, classes, etc."""
import re

class StyleChecker:
    """Class for defining different naming styles and checking names against them."""

    @staticmethod
    def is_snake_case(name: str) -> bool:
        """Check if the name follows snake_case convention."""
        pattern = r"^[a-z][a-z0-9_]*$"
        return bool(re.match(pattern, name))

    def is_camel_case(self, name: str) -> bool:
        """Check if the name follows camelCase convention."""
        if self.allow_acronyms:
            pattern = r"^(?:[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\s|$)|\d+)(?:[A-Z]*(?=[A-Z][a-z]|\d|\s|$)|\d*)[a-zA-Z0-9]*$"
        else:
            pattern = r"^[a-z][a-z0-9]*(([A-Z][a-z0-9]+)*[A-Z]?|([a-z0-9]+[A-Z])*|[A-Z])$"
        return bool(re.match(pattern, name))

    def is_pascal_case(self, name: str) -> bool:
        """Check if the name follows PascalCase convention."""
        if self.allow_acronyms:
            pattern = r"^(([A-Z][a-z0-9]+)|([A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+))([A-Z][a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+)*$"
        else:
            pattern = r"^[A-Z](([a-z0-9]+[A-Z]?)*)$"
        return bool(re.match(pattern, name))

    @staticmethod
    def is_upper_case(name: str) -> bool:
        """Check if the name follows UPPER_CASE convention."""
        pattern = r"^[A-Z0-9_]+$"
        return bool(re.match(pattern, name))

    def is_title_case(self, name: str) -> bool:
        """Check if the name follows Title Case convention."""
        if self.allow_acronyms:
            pattern = r"^(?:[A-Z]+|[A-Z][a-z0-9]+)(?:\s(?:[A-Z]+|\d+[A-Za-z]*|[A-Z][a-z0-9]+))*$"
        else:
            pattern = r"^[A-Z][a-z0-9]+(?:\s(?:[A-Z][a-z0-9]+|\d+))*$"
        return bool(re.match(pattern, name))

    @staticmethod
    def is_any(_: str) -> bool:
        """Any name is considered correct."""
        return True

    def __init__(self, style_name, allow_acronyms=False):
        self.style_name = style_name
        self.allow_acronyms = allow_acronyms
        self.style_check_function = self._get_style_check_function(style_name)

    def _get_style_check_function(self, style_name):
        naming_styles = {
            "snake_case": self.is_snake_case,
            "camelCase": self.is_camel_case,
            "PascalCase": self.is_pascal_case,
            "UPPER_CASE": self.is_upper_case,
            "Title Case": self.is_title_case,
            "any": self.is_any,
        }
        if style_name in naming_styles:
            return naming_styles[style_name]
        return self._generate_regex_check_function(self.style_name)

    def _generate_regex_check_function(self, pattern):
        regex_pattern = re.compile(pattern)
        return lambda name: bool(regex_pattern.match(name))

    def is_correct_style(self, name):
        return self.style_check_function(name)
