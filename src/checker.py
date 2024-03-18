import re

class StyleChecker:
    """Class for defining different naming styles and checking names against them."""

    @staticmethod
    def is_snake_case(name: str) -> bool:
        """Check if the name follows snake_case convention."""
        return bool(re.match(r"^[a-z][a-z0-9_]*$", name))

    @staticmethod
    def is_camel_case(name: str) -> bool:
        """Check if the name follows camelCase convention."""
        return bool(re.match(r"^[a-z][a-z0-9]*(([A-Z][a-z0-9]+)*[A-Z]?|([a-z0-9]+[A-Z])*|[A-Z])$", name))
        # return bool(re.match(r"^[a-z]+(?:[0-9a-zA-Z]*)*$", name))

    @staticmethod
    def is_pascal_case(name: str) -> bool:
        """Check if the name follows PascalCase convention."""
        return bool(re.match(r"^[A-Z](([a-z0-9]+[A-Z]?)*)$", name))

    @staticmethod
    def is_upper_case(name: str) -> bool:
        """Check if the name follows UPPER_CASE convention."""
        return bool(re.match(r"^[A-Z0-9_]+$", name))

    @staticmethod
    def is_title_case(name: str) -> bool:
        """Check if the name follows Title Case convention."""
        return bool(re.match(r"^[A-Z][a-z0-9]+(?:\s[A-Z][a-z0-9]+)*$", name))


    @staticmethod
    def is_any(name: str) -> bool:
        """Any name is considered correct."""
        return True

    def __init__(self, style_name):
        self.style_name = style_name
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
        else:
            return self._generate_regex_check_function(self.style_name)

    def _generate_regex_check_function(self, pattern):
        regex_pattern = re.compile(pattern)
        return lambda name: bool(regex_pattern.match(name))

    def is_correct_style(self, name):
        return self.style_check_function(name)
