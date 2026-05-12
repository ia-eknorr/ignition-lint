# Ignition Lint Documentation

Documentation site built with [Docusaurus 3](https://docusaurus.io/). The published site is the technical reference for `ignition-lint`.

## Local development

```bash
yarn install
yarn start
```

`yarn start` serves the site on `http://localhost:3000` with live reload.

## Build

```bash
yarn build
```

Static output lands in `build/`. The build is configured with `onBrokenLinks: 'throw'`, so any broken cross-page link fails the build.

## Add a new rule page

1. Add a new markdown file under `docs/rules/<category>/<rule-name>.md` using the per-rule template (see any existing rule page for the structure).
2. Register the file in `sidebars.ts`.
3. Run `yarn build` and confirm no broken-link errors.
