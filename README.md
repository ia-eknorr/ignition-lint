# Ignition `view.json` Linter

This GitHub Action performs linting on Ignition `view.json` files to ensure proper naming conventions are followed for component names and parameter keys.

## Inputs

### `files` (required)

Space-separated list of paths to the Ignition `view.json` files to be linted.

### `component_style` (optional)

Naming convention style for components. Default is None. Either `component_style` or `component_style_rgx` should be selected, but not both.

Options:

* `PascalCase`
* `camelCase`
* `snake_case`
* `UPPER_CASE`

### `parameter_style` (optional)

Naming convention style for parameters. Default is None. Either `parameter_style` or `parameter_style_rgx` should be selected, but not both.

Options:

* `PascalCase`
* `camelCase`
* `snake_case`
* `UPPER_CASE`

### `component_style_rgx` (optional)

Regex pattern for naming convention style of components. Default is None. Either `component_style` or `component_style_rgx` should be selected, but not both.

### `parameter_style_rgx` (optional)

Regex pattern for naming convention style of parameters. Default is None. Either `parameter_style` or `parameter_style_rgx` should be selected, but not both.

## Outputs

None

## Usage

To use this Action in your workflow, create a workflow file (e.g., `.github/workflows/lint-ignition-views.yml`) in your repository and add the following configuration:

```yaml
jobs:
  lint:
    name: Lint Ignition Views
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Run JSON linting
        uses: ia-eknorr/ignition-lint@v1.0
        with:
          files: 'path/to/your/view.json'
          component_style: 'PascalCase'
          parameter_style: 'camelCase'

```

### Action scenarios

* No style conflicts
  * The check will pass
* No files given
  * The test will pass
* Style conflicts are found
  * The action will fail with logs showing the bad names
  ![test-failure](images/test-failure.png)
