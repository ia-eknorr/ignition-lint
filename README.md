# Ignition `view.json` Linter

This GitHub Action performs linting on Ignition `view.json` files to ensure proper naming conventions are followed for component names and parameter keys.

## Inputs

### `files` (required)

Space-separated list of paths to the Ignition `view.json` files to be linted.

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
        uses: ia-eknorr/ignition-lint@v0.2
        with:
          files: 'path/to/your/view.json'
```

## Default Case Checks

This Action performs the following checks. At the moment, these are not configurable.

* Component Names: PascalCase
* Custom Properties: camelCase
* Parameters: camelCase
