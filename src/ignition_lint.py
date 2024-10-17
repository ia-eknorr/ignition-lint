""" This script is used to lint Ignition view.json files for style inconsistencies in component and parameter names. """

import json
import sys
import argparse
import os
import glob
import re
from checker import StyleChecker


class JsonLinter:
    """Class for linting Ignition view.json files for style inconsistencies in component and parameter names.

    Attributes:

    component_style (str): The naming convention style for components.
    parameter_style (str): The naming convention style for parameters.
    component_style_rgx (str): The regex pattern for naming convention style of components.
    parameter_style_rgx (str): The regex pattern for naming convention style of parameters.
    allow_acronyms (bool): Whether to allow acronyms in the names.
    errors (dict): Dictionary to store the errors found in the files.
    files_linted (int): The number of files linted.
    parameter_areas (list): The areas in the file where parameters are found.
    component_areas (list): The areas in the file where components are found.
    keys_to_skip (list): The keys to skip while traversing the file.
    component_style_checker (StyleChecker): The StyleChecker object for component names.
    parameter_style_checker (StyleChecker): The StyleChecker object for parameter names

    Usage:
    linter = JsonLinter(component_style="PascalCase", parameter_style="snake_case")
    num_errors = linter.lint_file("path/to/file.json")
    """

    def __init__(
        self,
        component_style,
        parameter_style,
        component_style_rgx,
        parameter_style_rgx,
        allow_acronyms=False,
    ):
        # Check if both named style and regex style are provided for the same type
        if component_style_rgx not in [None, ""] and component_style not in [None, ""]:
            message = "Cannot specify both (component_style: {}, component_style_rgx: {}). Please choose one or the other."
            raise ValueError(message.format(component_style, component_style_rgx))

        if parameter_style_rgx not in [None, ""] and parameter_style not in [None, ""]:
            message = "Cannot specify both (parameter_style: {}, parameter_style_rgx: {}). Please choose one or the other."
            raise ValueError(message.format(parameter_style, parameter_style_rgx))

        if component_style_rgx is None and component_style is None:
            raise ValueError(
                "Component naming style not specified. Use either (component_style) or (component_style_rgx)."
            )

        if parameter_style_rgx is None and parameter_style is None:
            raise ValueError(
                "Parameter naming style not specified. Use either (parameter_style) or (parameter_style_rgx)."
            )

        if parameter_style == "Title Case":
            raise ValueError(
                "Title Case is not a valid parameter naming style. Please use a different style."
            )

        self.parameter_areas = ["custom", "params"]
        self.component_areas = ["root", "children"]
        self.keys_to_skip = [
            "props",
            "position",
            "type",
            "meta",
            "propConfig",
            "scripts",
        ]
        self.component_style = component_style
        self.parameter_style = parameter_style
        self.component_style_rgx = component_style_rgx
        self.parameter_style_rgx = parameter_style_rgx
        self.allow_acronyms = allow_acronyms
        self.errors = {"components": [], "parameters": []}
        self.files_linted = 0

        self.component_style_checker = (
            StyleChecker(component_style_rgx, allow_acronyms)
            if component_style_rgx not in [None, ""]
            else StyleChecker(component_style, allow_acronyms)
        )
        self.parameter_style_checker = (
            StyleChecker(parameter_style_rgx, allow_acronyms)
            if parameter_style_rgx not in [None, ""]
            else StyleChecker(parameter_style, allow_acronyms)
        )

    def lint_file(self, file_path: str) -> int:
        """Lint the file at the given path.

        Args:
        file_path (str): The path to the file to be linted.

        Returns:
        int: The number of errors found in the file.
        """
        # Check for presence of glob special characters
        if re.search(r"[\*\?\[\]]", file_path):
            # If the file_path contains a glob pattern
            files = glob.glob(file_path, recursive=True)
            if not files:
                print(f"No files found matching the pattern: {file_path}")
                return 0

            num_errors = 0
            for file in files:
                num_errors += self.lint_single_file(file)
            return num_errors
        return self.lint_single_file(file_path)

    def lint_single_file(self, file_path: str) -> int:
        """Lint a single file.

        Args:
        file_path (str): The path to the file to be linted.

        Returns:
        int: The number of errors found in the file.
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return 0

        self.errors = {"components": [], "parameters": []}

        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                self.check_component_names(data, self.errors)
            except json.JSONDecodeError as e:
                print(f"Error parsing file {file_path}: {e}")
                return 0

        self.print_errors(file_path, self.errors)
        num_errors = len(self.errors["components"]) + len(self.errors["parameters"])

        self.files_linted += 1
        return num_errors

    def check_parameter_names(self, data, errors: dict, parent_key: str = ""):
        """Check the parameter names in the data.

        Args:
        data (dict): The data to be checked.
        errors (dict): The dictionary to store the errors found.
        parent_key (str): The parent key of the data.

        Returns:
        None
        """
        for key, value in data.items():
            if key in self.keys_to_skip:
                continue

            # If key has the format of a dataset, skip to next key
            if key.startswith("$"):
                continue

            if isinstance(value, dict):
                self.check_parameter_names(value, errors, f"{parent_key}.{key}")
            elif (
                not self.parameter_style_checker.is_correct_style(key)
                and "props.params" not in parent_key
            ):
                errors["parameters"].append(
                    f"{parent_key}.{key}" if parent_key else key
                )

    def check_component_names(self, value, errors: dict, parent_key: str = ""):
        """Check the component names in the data.

        Args:
        value (dict): The data to be checked.
        errors (dict): The dictionary to store the errors found.
        parent_key (str): The parent key of the data.

        Returns:
        None
        """
        component_name = value.get("meta", {}).get("name")
        if component_name == "root":
            parent_key = component_name
        elif component_name is not None:
            parent_key = f"{parent_key}/{component_name}"
            if not self.component_style_checker.is_correct_style(component_name):
                errors["components"].append(parent_key)

        for key, element in value.items():
            if key in self.keys_to_skip:
                continue

            if isinstance(element, dict):
                if key in self.parameter_areas:
                    if not parent_key:
                        parent_key = "view"
                    self.check_parameter_names(element, errors, f"{parent_key}.{key}")
                else:
                    self.check_component_names(element, errors, parent_key)
            elif isinstance(element, list):
                parent_of_list = parent_key
                for item in element:
                    self.check_component_names(item, errors, parent_key)
                    parent_key = parent_of_list

    def print_errors(self, file_path: str, errors: dict) -> None:
        """Print the errors found in the file.

        Args:
        file_path (str): The path to the file.
        errors (dict): The errors found in the file.

        Returns:
        None
        """
        error_logs = []
        if errors["components"]:
            if self.component_style_rgx:
                error_logs.append(
                    f"  Component names should follow pattern '{self.component_style_rgx}':"
                )
            else:
                error_logs.append(
                    f"  Component names should be in {self.component_style}:"
                )
            error_logs.extend([f"    - {error}" for error in errors["components"]])
        if errors["parameters"]:
            if self.parameter_style_rgx:
                error_logs.append(
                    f"  Parameter names should follow pattern '{self.parameter_style_rgx}':"
                )
            else:
                error_logs.append(
                    f"  Parameter keys should be in {self.parameter_style}:"
                )
            error_logs.extend([f"    - {error}" for error in errors["parameters"]])

        if error_logs:
            print(f"\nError in file: {file_path}")
            for error_log in error_logs:
                print(error_log)


def main():
    """Main function to lint the Ignition view.json files for style inconsistencies in component and parameter names."""

    parser = argparse.ArgumentParser()
    # NOTE: The comma separated list vs the space separated list is because with a Space Separated list option you
    # Cannot truly support Title Case with a Space Case formatted file, it will capture it as a separate file path
    parser.add_argument(
        "--files",
        default="**/view.json",
        help="Comma-separated list of ignition files or glob patterns to lint",
    )
    parser.add_argument(
        "--component-style", help="Naming convention style for components"
    )
    parser.add_argument(
        "--parameter-style", help="Naming convention style for parameters"
    )
    parser.add_argument(
        "--component-style-rgx",
        help="Regex pattern for naming convention style of components",
    )
    parser.add_argument(
        "--parameter-style-rgx",
        help="Regex pattern for naming convention style of parameters",
    )
    args = parser.parse_args()

    input_patterns = args.files.split(",")
    input_files = []
    for pattern in input_patterns:
        input_files.extend(glob.glob(pattern, recursive=True))

    if not input_files:
        print("No files found matching the specified patterns")
        sys.exit(0)

    linter = JsonLinter(
        component_style=args.component_style,
        parameter_style=args.parameter_style,
        component_style_rgx=args.component_style_rgx,
        parameter_style_rgx=args.parameter_style_rgx,
    )
    number_of_errors = 0

    for file_path in input_files:
        number_of_errors += linter.lint_file(file_path)

    if not number_of_errors:
        print("No style inconsistencies found")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
