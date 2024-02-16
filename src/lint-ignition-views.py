import os
import json
import re
import sys

class JsonLinter:
    def __init__(self):
        self.parameterAreas = ["custom", "params"]
        self.componentAreas = ["root", "children"]
        self.keysToSkip = ["props", "position", "type", "meta", "propConfig", "scripts"]

    def lint_file(self, file_path: str) -> int:
        errors = {"components": [], "parameters": []}

        with open(file_path, "r") as file:
            try:
                data = json.load(file)
                self.check_component_names(data, errors)
            except json.JSONDecodeError as e:
                errors["components"].append(f"Error parsing JSON: {e}")

        self.print_errors(file_path, errors)
        return len(errors['components']) + len(errors['parameters'])

    def check_parameter_names(self, data, errors: dict, parent_key: str = ""):
        for key, value in data.items():
            if isinstance(value, dict):
                self.check_parameter_names(value, errors, f"{parent_key}.{key}")
            elif not self.is_camel_case(key) and "props.params" not in parent_key:
                errors["parameters"].append(f"{parent_key}.{key}" if parent_key else key)

    def check_component_names(self, value, errors: dict, parent_key: str = ""):
        component_name = value.get("meta", {}).get("name")
        if component_name == "root":
            parent_key = component_name
        elif component_name is not None:
            parent_key = f"{parent_key}/{component_name}"
            if not self.is_pascal_case(component_name):
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

    def is_camel_case(self, s: str) -> bool:
        return re.match(r"^[a-z][a-zA-Z0-9]*$", s) is not None

    def is_pascal_case(self, s: str) -> bool:
        return re.match(r"^[A-Z][a-zA-Z0-9]*$", s) is not None

    def print_errors(self, file_path: str, errors: dict) -> None:
        error_logs = []
        if errors["components"]:
            error_logs.append(f"  Component names should be in PascalCase:")
            error_logs.extend([f"    - {error}" for error in errors["components"]])
        if errors["parameters"]:
            error_logs.append(f"  Parameter keys should be in camelCase:")
            error_logs.extend([f"    - {error}" for error in errors["parameters"]])

        if error_logs:
            print(f"\nError in file: {file_path}")
            for error_log in error_logs:
                print(error_log)

def main():
    input_files = sys.argv[1:]
    print(input_files)
    if not input_files:
        print("No files")
        sys.exit(0)

    linter = JsonLinter()
    number_of_errors = 0

    for file_path in input_files:
        number_of_errors += linter.lint_file(file_path)

    if number_of_errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
