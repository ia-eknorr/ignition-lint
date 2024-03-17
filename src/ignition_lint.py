import json
import sys
import argparse
import os
from checker import StyleChecker
import glob
import re
import subprocess

class IgnitionLintException(Exception):
    pass

class PythonLintException(IgnitionLintException):
    pass

class PythonLinter:
    def __init__(self, pylint_args=None):
        self.pylint_args = pylint_args or []
        self.scripts_linted = 0

    def lint_encoded_script(self, code: str, errors: dict, parent_key: str = ""):
        # Encoded code from Ignition has some unique quirks, so we need to ignore a few things
        ignored_rules = [
            "missing-final-newline", # Ignition does not add a newline at the end of the file
            "missing-docstring" # The docstring is baked into the code interface
        ]


        # If _temp_script.py already exists, remove it
        if os.path.exists("_temp_script.py"):
            os.remove("_temp_script.py")

        number_of_artificially_added_lines = 0
        with open("_temp_script.py", "w") as temp_file:
            # NOTE: Write the ignored rules to the top of the file
            temp_file.write("# pylint: disable=" + ",".join(ignored_rules) + "\n")
            number_of_artificially_added_lines += 1
            
            # NOTE: Add a default function definition to the top of the file
            temp_file.write("def main():\n")
            number_of_artificially_added_lines += 1
            
            temp_file.write(code)

        try:
            # Confirm that pylint is installed and accessible
            subprocess.run(["pylint", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            process = subprocess.run(["pylint", "_temp_script.py", "--score=no"] + self.pylint_args, capture_output=True, text=True)

            output = process.stdout if process.returncode == 0 else process.stdout + process.stderr

            if output != "":
                # If there is an output from pylint, we need to adjust the output format to account for our changes
                # We should remove the first line, because it is just the fake file definition
                output = "\n".join(output.split("\n")[1:])
                
                # We need to add all of the errors for this file into the errors dictionary
                # Pylint outputs each error with newlines between, so we should split them all out
                error_lines = output.split("\n")
                for line in error_lines:
                    if line != "":
                        # Replace the fake file definition
                        line = line.replace("_temp_script.py", "")
                        # Remove the pylint callout to the file
                        line = line.replace("_temp_script, ", "")

                        # We should remove the artificially added lines from the line number
                        written_line_number = int(line.split(":")[1])
                        line_number = written_line_number - number_of_artificially_added_lines

                        line  = line.replace("(line %s)" % written_line_number, f"(line {line_number})")

                        line = f"{parent_key}:{line_number}:{line.split(':', 2)[2]}"

                        errors['scripts'].append(line)

        except FileNotFoundError:
            print("Pylint is not installed. Please install pylint to lint Python code.")
            raise PythonLintException("Pylint is not installed. Please install pylint to lint Python code.")
        except subprocess.CalledProcessError as e:
            print(f"PyLint Error:\n{e.output}")
        
        finally:
            os.remove("_temp_script.py")
            self.scripts_linted += 1


class JsonLinter:
    def __init__(self, component_style, parameter_style, component_style_rgx, parameter_style_rgx, pylint_args=None):
        # Check if both named style and regex style are provided for the same type
        if component_style_rgx not in [None, ""] and component_style not in [None, ""]:
            raise ValueError("Cannot specify both (component_style: {}, component_style_rgx: {}). Please choose one or the other.".format(component_style, component_style_rgx))

        if parameter_style_rgx not in [None, ""] and parameter_style not in [None, ""]:
            raise ValueError("Cannot specify both (parameter_style: {}, parameter_style_rgx: {}). Please choose one or the other.".format(parameter_style, parameter_style_rgx))

        if component_style_rgx is None and component_style is None:
            raise ValueError("Component naming style not specified. Use either (component_style) or (component_style_rgx).")

        if parameter_style_rgx is None and parameter_style is None:
            raise ValueError("Parameter naming style not specified. Use either (parameter_style) or (parameter_style_rgx).")

        try:
            self.python_linter = PythonLinter(pylint_args)
        except PythonLintException as e:
            print(f"Error initializing Python linter: {e}, python linting will be skipped")
            self.python_linter = None
        
        self.parameterAreas = ["custom", "params"]
        self.componentAreas = ["root", "children"]
        self.keysToSkip = ["props", "position", "type", "meta", "propConfig"]
        self.script_keys = ["script", "code"]
        self.keys_to_hide_in_output = ["children"]
        self.component_style = component_style
        self.parameter_style = parameter_style
        self.component_style_rgx = component_style_rgx
        self.parameter_style_rgx = parameter_style_rgx
        self.errors = {"components": [], "parameters": []}

        if self.python_linter:
            self.errors['scripts'] = []

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

        num_errors = sum([len(errors) for errors in self.errors.values()])

        self.files_linted += 1
        return num_errors

    def check_parameter_names(self, data, errors: dict, parent_key: str = ""):
        for key, value in data.items():
            if isinstance(value, dict):
                self.check_parameter_names(value, errors, f"{parent_key}.{key}")
            elif not self.parameter_style_checker.is_correct_style(key) and "props.params" not in parent_key:
                errors["parameters"].append(f"{parent_key}.{key}" if parent_key else key)

    def check_component_names(self, value, errors: dict, parent_key: str = "", current_path: str = ""):
        # NOTE: If you have stepped into an array, you may hit direct strings and you should not lint these.
        if isinstance(value, str):
            return

        component_name = value.get("meta", {}).get("name")
        if component_name == "root":
            parent_key = component_name
        elif component_name is not None:
            parent_key = f"{parent_key}/{component_name}"
            if not self.component_style_checker.is_correct_style(component_name):
                errors["components"].append(parent_key)

			# NOTE: Reset our path in the json stack since we're below a component
            current_path = None

        for key, value in value.items():
            # NOTE: Add our current key to the path
            current_path = key if current_path is None else f"{current_path}.{key}"
            
            if key in self.keysToSkip:
                continue
            
            if key in self.script_keys:
                self.validate_encoded_script(value, errors, f"{parent_key}")
            elif isinstance(value, dict):
                if key in self.parameterAreas:
                    if not parent_key:
                        parent_key = "view"
                    self.check_parameter_names(value, errors, f"{parent_key}.{key}")
                else:
                    self.check_component_names(value, errors, parent_key, current_path)

            elif isinstance(value, list):
                parent_of_list = parent_key
                for index, item in enumerate(value):
                    self.check_component_names(item, errors, parent_key, current_path)
                    parent_key = parent_of_list
        
    
    def validate_encoded_script(self, script_content, errors: dict, parent_key: str = ""):
        self.python_linter.lint_encoded_script(script_content, errors, parent_key)

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
        if errors["scripts"]:
            error_logs.append("  Python scripts should be linted with pylint:")
            error_logs.extend([f"    - {error}" for error in errors["scripts"]])

        if error_logs:
            print(f"\nError in file: {file_path}")
            for error_log in error_logs:
                print(error_log)

def main():
    parser = argparse.ArgumentParser()
    # NOTE: The comma separated list vs the space separated list is because with a Space Separated list option you cannot truly support Title Case
    # With a Space Case formatted file, it will capture it as a separate file path
    parser.add_argument('--files', default="**/view.json", help='Comma-separated list of ignition files or glob patterns to lint')
    parser.add_argument('--component-style', help='Naming convention style for components')
    parser.add_argument('--parameter-style', help='Naming convention style for parameters')
    parser.add_argument('--component-style-rgx', help='Regex pattern for naming convention style of components')
    parser.add_argument('--parameter-style-rgx', help='Regex pattern for naming convention style of parameters')
    parser.add_argument('--pylint-args', nargs='*', help='Additional arguments to pass to pylint')
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
        pylint_args=args.pylint_args
    )
    number_of_errors = 0

    for file_path in input_files:
        number_of_errors += linter.lint_file(file_path)

    print("Number of JSON files linted = ", linter.files_linted)
    if linter.python_linter.scripts_linted:
        print("Number of Python scripts linted = ", linter.python_linter.scripts_linted)

    if not number_of_errors:
        print("No style inconsistencies found")
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()