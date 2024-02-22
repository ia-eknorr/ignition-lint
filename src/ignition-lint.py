import json
import sys
import argparse
from checker import StyleChecker

class JsonLinter:
    def __init__(self, component_style, parameter_style, component_style_rgx, parameter_style_rgx):
        # Check if both named style and regex style are provided for the same type
        if component_style_rgx:
            raise ValueError("Cannot specify both component_style and component_style_rgx. Please choose one or the other.")
        if parameter_style_rgx:
            raise ValueError("Cannot specify both parameter_style and parameter_style_rgx. Please choose one or the other.")

        self.parameterAreas = ["custom", "params"]
        self.componentAreas = ["root", "children"]
        self.keysToSkip = ["props", "position", "type", "meta", "propConfig", "scripts"]
        self.component_style = component_style
        self.parameter_style = parameter_style
        self.component_style_rgx = component_style_rgx
        self.parameter_style_rgx = parameter_style_rgx

        self.component_style_checker = StyleChecker(component_style_rgx) if component_style_rgx is not None else StyleChecker(component_style)
        self.parameter_style_checker = StyleChecker(parameter_style_rgx) if parameter_style_rgx is not None else StyleChecker(parameter_style)

    
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
    parser.add_argument('--files', required=True, help='Space-separated list of ignition files to lint')
    parser.add_argument('--component-style', default='PascalCase', help='Naming convention style for components')
    parser.add_argument('--parameter-style', default='snake_case', help='Naming convention style for parameters')
    parser.add_argument('--component-style-rgx', help='Regex pattern for naming convention style of components')
    parser.add_argument('--parameter-style-rgx', help='Regex pattern for naming convention style of parameters')
    args = parser.parse_args()

    input_files = args.files.split()
    if not input_files:
        print("No files")
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

    if number_of_errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
