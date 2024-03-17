import json
import sys
import argparse
import os
from checker import StyleChecker
import glob
import re


class JsonLinter:
    def __init__(self, component_style, parameter_style, component_style_rgx, parameter_style_rgx):
        # Check if both named style and regex style are provided for the same type
        if component_style_rgx not in [None, ""] and component_style not in [None, ""]:
            raise ValueError("Cannot specify both (component_style: {}, component_style_rgx: {}). Please choose one or the other.".format(component_style, component_style_rgx))

        if parameter_style_rgx not in [None, ""] and parameter_style not in [None, ""]:
            raise ValueError("Cannot specify both (parameter_style: {}, parameter_style_rgx: {}). Please choose one or the other.".format(parameter_style, parameter_style_rgx))

        if component_style_rgx is None and component_style is None:
            raise ValueError("Component naming style not specified. Use either (component_style) or (component_style_rgx).")

        if parameter_style_rgx is None and parameter_style is None:
            raise ValueError("Parameter naming style not specified. Use either (parameter_style) or (parameter_style_rgx).")

        self.parameterAreas = ["custom", "params"]
        self.componentAreas = ["root", "children"]
        self.keysToSkip = ["props", "position", "type", "meta", "propConfig", "scripts"]
        self.component_style = component_style
        self.parameter_style = parameter_style
        self.component_style_rgx = component_style_rgx
        self.parameter_style_rgx = parameter_style_rgx
        self.errors = {"components": [], "parameters": []}
        self.files_linted = 0

        self.component_style_checker = StyleChecker(component_style_rgx) if component_style_rgx not in [None, ""] else StyleChecker(component_style)
        self.parameter_style_checker = StyleChecker(parameter_style_rgx) if parameter_style_rgx not in [None, ""] else StyleChecker(parameter_style)

    def lint_file(self, file_path: str) -> int:
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
        else:
            # If the file_path is a specific file
            return self.lint_single_file(file_path)

    def lint_single_file(self, file_path: str) -> int:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return 0

        with open(file_path, "r") as file:
            try:
                data = json.load(file)
                self.check_component_names(data, self.errors)
            except json.JSONDecodeError as e:
                print(f"Error parsing file {file_path}: {e}")
                return 0

        self.print_errors(file_path, self.errors)
        num_errors = len(self.errors['components']) + len(self.errors['parameters'])

        self.files_linted += 1
        return num_errors

    def check_parameter_names(self, data, errors: dict, parent_key: str = ""):
        for key, value in data.items():
            if isinstance(value, dict):
                self.check_parameter_names(value, errors, f"{parent_key}.{key}")
            elif not self.parameter_style_checker.is_correct_style(key) and "props.params" not in parent_key:
                errors["parameters"].append(f"{parent_key}.{key}" if parent_key else key)

    def check_component_names(self, value, errors: dict, parent_key: str = ""):
        component_name = value.get("meta", {}).get("name")
        if component_name == "root":
            parent_key = component_name
        elif component_name is not None:
            parent_key = f"{parent_key}/{component_name}"
            if not self.component_style_checker.is_correct_style(component_name):
                errors["components"].append(parent_key)

        for key, value in value.items():
            if key in self.keysToSkip:
                continue

            if isinstance(value, dict):
                if key in self.parameterAreas:
                    if not parent_key:
                        parent_key = "view"
                    self.check_parameter_names(value, errors, f"{parent_key}.{key}")
                else:
                    self.check_component_names(value, errors, parent_key)
            elif isinstance(value, list):
                parent_of_list = parent_key
                for item in value:
                    self.check_component_names(item, errors, parent_key)
                    parent_key = parent_of_list

    def print_errors(self, file_path: str, errors: dict) -> None:
        error_logs = []
        if errors["components"]:
            if self.component_style_rgx:
                error_logs.append(f"  Component names should follow pattern '{self.component_style_rgx}':")
            else:
                error_logs.append(f"  Component names should be in {self.component_style}:")
            error_logs.extend([f"    - {error}" for error in errors["components"]])
        if errors["parameters"]:
            if self.parameter_style_rgx:
                error_logs.append(f"  Parameter names should follow pattern '{self.parameter_style_rgx}':")
            else:
                error_logs.append(f"  Parameter keys should be in {self.parameter_style}:")
            error_logs.extend([f"    - {error}" for error in errors["parameters"]])

        if error_logs:
            print(f"\nError in file: {file_path}")
            for error_log in error_logs:
                print(error_log)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', default="**/view.json", help='Space-separated list of ignition files or glob patterns to lint')
    parser.add_argument('--component-style', help='Naming convention style for components')
    parser.add_argument('--parameter-style', help='Naming convention style for parameters')
    parser.add_argument('--component-style-rgx', help='Regex pattern for naming convention style of components')
    parser.add_argument('--parameter-style-rgx', help='Regex pattern for naming convention style of parameters')
    args = parser.parse_args()

    input_patterns = args.files.split()
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
        parameter_style_rgx=args.parameter_style_rgx
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