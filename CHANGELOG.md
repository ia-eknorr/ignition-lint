# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auto-fix for trailing whitespace (C0303) in PylintScriptRule via `--fix` flag [d775d45]
- PylintScriptRule now uses FixableMixin so the existing fix infrastructure discovers it automatically [d775d45]

### Changed
- Gitignore jython cache directories [67e8ede]
- Each pre-commit batch invocation now reports its own honest totals; removed the terminal-summary override that aggregated escalating totals across batches (the `_AGGREGATED_SUMMARY.txt` file is still written when batch files exist) [dacf480]

### Fixed
- Stale `_AGGREGATED_SUMMARY.txt` from a previous run no longer pollutes a later passing run's reported totals; cleanup now removes stale summary files (≥5s old) and the aggregator no longer reads existing summaries on non-batch paths [dacf480]

## [0.4.1] - 2026-02-20

### Changed
- Rename PyPI package from `ignition-lint` to `ign-lint` (CLI command is now `ign-lint`) [fef2808]
- Switch PyPI publishing to OIDC trusted publisher (no API tokens needed) [47ce126]
- Split publish workflow into build and publish jobs with GitHub environment approval gates [47ce126]
- Trigger publish workflow from tag push; derive package version from git tag [d284d2d]
- Gate Test PyPI publishing on RC tags and Prod PyPI on stable tags [d284d2d]
- Use `pipx install poetry` for GitHub runner compatibility [7c71154]

## [0.4.0] - 2026-02-15

### Added
- Auto-fix framework with `--fix`, `--fix-unsafe`, `--fix-dry-run`, and `--fix-rules` CLI flags [fd17cbf]
- NamePatternRule generates auto-fix suggestions to rename components to match naming conventions [fd17cbf]
- Safety tiers: safe fixes (unreferenced renames) vs unsafe fixes (reference updates, `this.meta.name` bindings) [fd17cbf]
- FixableMixin for rules to opt into providing auto-fixes [fd17cbf]

### Fixed
- Preserve Ignition unicode escapes (`\u0027`, `\u003c`, etc.) when writing view.json files after fixes [3dc40cb]

## [0.3.6] - 2026-02-15

### Added
- Whitelist feature for managing technical debt by ignoring specific views [dbe1363]
- CLI helper functions to generate whitelist from glob patterns [dbe1363]
- ComponentReferenceValidationRule to validate that component references resolve to actual components [057d0f2]
- BadComponentReference test case with property, expression, and script getChild references [eb08041]
- Mixed tabs/spaces detection with clear error messages [369173a]
- Tests for script indentation with comments [e85b26f]
- Implement feature for custom formatting output by rule and configured pylint category mapping[c7c1402]
- Support for BadComponentReferenceRule severity to be defined by user in rule config [ce39662]

### Changed
- Optimize script error messages in non-batch mode of pylint rule [11a7683]
- ComponentReferenceValidationRule added to default rule_config.json [c63f540]
- Disabled duplicate-code check in pylint config for test files [88b68f5]
- Enforce yapf style file usage in all CLAUDE.md commands [7b5be3a]

### Fixed
- Handle custom property references (.custom.) in ComponentReferenceValidationRule [dd10a0f]
- Skip comment lines when checking script indentation [b2788e7]

## [0.3.5] - 2026-02-13

### Added
- Automatic aggregation of batch results with cleanup for pre-commit workflows [e59d6d1]

### Fixed
- Resolve race conditions and file conflicts when running in parallel execution (e.g., pre-commit hooks) [82f6f21] [bbbda21]
- Add script indentation validation and smart auto-correction for view.json files [3e116b1]
- Improve debug file management with automatic cleanup and source file tracking [3e116b1]

## [0.3.4] - 2026-02-12

### Fixed
- Handle view.params with bindings in UnusedCustomPropertiesRule [536319b]

## [0.3.3] - 2026-02-07

### Fixed
- Upgrade Python to 3.13.1 and remove pre-commit version constraint [71ba2a5]

## [0.3.2] - 2026-02-06

### Added
- Comprehensive tests for mixed naming patterns (PascalCase/SCREAMING_SNAKE_CASE) [b19a336]

### Changed
- Simplify NamePatternRule pattern configuration from 'custom_pattern' to 'pattern' [27dc03f]

### Fixed
- Add common Ignition event handlers to default pylintrc exemptions [16d8c30]

## [0.3.1] - 2026-02-05

### Added
- A suggestion_convention parameter in NamePatternRule to support a default naming convention suggestion when using custom regex pattern [40641c1]

## [0.3.0] - 2026-02-03

### Added
- Prep package to be available on PyPI - install with `pip install ignition-lint` [02ad134]
- Python 3.13 support [02ad134]
- PyPI metadata: keywords and classifiers for better package discoverability [02ad134]
- Automated release preparation workflow triggered by RC tags [41d9491]
- PyPI publishing workflow for automated package publishing [2430eb1]
- Comprehensive release process documentation in RELEASING.md [d189aa1]
- CLI `--version` flag to display package version [69310f9]
- v0.3.0 implementation documentation [2ccb2b6]

### Changed
- Moved `pre-commit` from runtime dependencies to dev dependencies (cleaner installation) [02ad134]
- Updated Python version constraint to `>=3.10,<3.14` (was `>=3.10,<3.13`) [02ad134]
- Optimized CI pipeline to run only on PRs with smart Python version matrix [bde11a4]
- Renamed ci.yml to ci-pipeline.yml for clarity [bde11a4]
- Updated CLAUDE.md with release process section [5d990bc]
- Moved bundled pylintrc from root to `src/ignition_lint/.config/.pylintrc` [69310f9]
- Updated author order to reflect primary contributor [9e16825]

### Fixed
- NamePatternRule now correctly expects snake_case for custom methods (was incorrectly expecting camelCase) [56669ad]
- Bundled pylintrc now properly included in wheel package for pip installations [69310f9]

### Removed
- `ignition-api-stubs` dependency (not used at runtime, was blocking Python 3.13 support) [02ad134]
- Redundant unittest.yml and integration-test.yml workflows that are covered by the ci-pipeline.yaml [bde11a4]
- Temporary v0.3.0 implementation guide (archived implementation notes kept) [436451d]

## [0.2.10] - 2026-01-29

### Added
- NamePatternRule now skips props.aspectRatio properties to prevent false positives on coordinate containers [eabbb41]

## [0.2.9] - 2026-01-27

### Added
- UnusedCustomPropertiesRule now detects self.params references in script transforms [5cf928d]
- Test coverage expanded for UnusedCustomPropertiesRule with 8 new test cases covering script transforms, tag bindings, message handlers, custom methods, property bindings, and expression patterns [5599aad]

### Fixed
- UnusedCustomPropertiesRule now correctly recognizes view parameters used as self.params in script transforms, preventing false positives [5cf928d]
- Pattern matching in script reference detection now properly handles escaped regex patterns for .params. and .custom. patterns [5cf928d]

## [0.2.8] - 2026-01-26

### Added
- BadComponentReferenceRule added to default rule_config.json to detect brittle component traversal patterns (.getSibling, .getParent, .getChild)
- NamePatternRule now validates message_handler nodes (kebab-case convention)
- NamePatternRule now validates custom_method nodes (snake_case convention)

### Changed
- NamePatternRule no longer validates event_handler nodes as event handler names (onActionPerformed, onClick, etc.) are framework-defined by Ignition components
- rule_config.json updated with comprehensive naming conventions for all user-controllable node types:
  - component: PascalCase (min 3 chars)
  - property: camelCase (min 2 chars)
  - message_handler: kebab-case (min 2 chars)
  - custom_method: snake_case (min 2 chars)
- Add docker/.gitignore and remove tracked files matching ignore patterns [9ce499a]

## [0.2.7] - 2026-01-15

### Security
- Updated Python requirement from >=3.9 to >=3.10 (Python 3.9 reached EOL October 2025)
- Updated filelock from 3.18.0 to 3.20.3 to fix CVE-2025-68146 (TOCTOU race condition vulnerabilities)
- Updated virtualenv from 20.31.2 to 20.36.1 to fix CVE-2026-22702 (TOCTOU vulnerabilities in directory creation)
- Added explicit `permissions: contents: read` to all GitHub Actions workflows following principle of least privilege

### Changed
- NamePatternRule now skips position properties (x, y coordinates) to prevent false positives on coordinate container properties [5e1b209]
- NamePatternRule now skips SVG path properties (d property in props.elements) to prevent false positives on SVG shape components [70b6329]

### Fixed
- UnusedCustomPropertiesRule now properly resets state between files to prevent false positives [30a440b]
- Resolved Pylance type errors in unit test base classes and test files [64afcf9]

## [0.2.6] - 2026-01-09

### Added
- Performance profiling with `--timing-output` and `--results-output` flags [b66e88b]
- Batch processing mode for PylintScriptRule to process all files together [95b81fa]
- ExcessiveContextDataRule to detect large arrays and excessive nesting in custom properties [9d76661]
- Four detection methods for excessive context data: array size, sibling properties, nesting depth, total data points [41e3c95]
- Detailed warnings and errors in results report output [3da2a29]
- Timestamp to timing reports for tracking report generation time [cc3eb3b]
- Auto-save debug files when PylintScriptRule finds errors [0ce3555]
- Configurable debug directory for PylintScriptRule via `debug_dir` parameter [43fa11f]
- File path header display at top of output before violations [ee1cb1f]

### Changed
- Disabled batch mode by default for clearer per-file output [28ac26e]
- `--warnings-only` flag replaced with `--ignore-warnings` for clearer intent [e81c1c1]
- Removed confusing "additional" wording from batch results output [20a8956]
- File path now shown once at top instead of repeated in each violation header [ee1cb1f]

### Fixed
- Pre-commit compatibility and configuration simplification [942cc7f]
- CSS property detection now includes all style containers [8c2d21f]
- Deprecated stage names in pre-commit configuration [cdc1bc0]
- Duplicate model building in LintEngine [7f0c84b]
- Duplicate violation output in non-batch mode [52295bb]
- Duplicate warning statements in output [d667c78]
- Report styling improvements [f83ea8a]
- Strip array indices from script function names for valid Python [33271a6]
- Warn when specified pylintrc file is not found [c1b904f]
- Always show pylintrc resolution in debug mode [5936f59]
- Create parent directories for timing and results output files [bf1a9bd]
- Suppress pylint module name errors for temporary files with timestamps [cf7ba13]
- Rule name spacing in output [8ac97c1]

### Performance
- Optimized `_is_property_persistent` with propConfig caching (30s → <1s for large files) [a618dda]
- PylintScriptRule quick optimization wins [dbb00e5]

### Documentation
- Added ExcessiveContextDataRule documentation [5ffa23d]
- Corrected pre-commit workflow documentation (incremental checks vs full scans) [795d9a1]

## [0.2.5] - 2026-01-09

### Added
- Pre-push hooks for comprehensive validation (full pylint + full test suite)
- yapf format check to pre-commit stage
- Clear section comments distinguishing pre-commit vs pre-push hook stages
- Changelog skills for automated changelog management
- .lfsconfig to skip LFS downloads during pre-commit installation

### Changed
- Reorganized pre-commit hooks into fast pre-commit stage (5-10s) and comprehensive pre-push stage (1-2min)
- Pre-commit pylint now only runs on changed files for faster feedback
- Migrated deprecated stage names (`commit` → `pre-commit`, `push` → `pre-push`)
- Updated PR template with breaking change section and type of change checklist
- Bundle .config/ directory with package for default pylintrc access
- Pylintrc resolution order now: rule_config.json → repo .config → package .config → pylint defaults
- Use Pythonic any() approach for CSS property detection

### Fixed
- Pre-commit installation failing due to LFS 404 errors
- CSS property detection now includes all style containers (.textStyle., .elementStyle., .instanceStyle.)
- CSS properties (kebab-case) no longer incorrectly flagged as naming violations
- Deprecated stage name warnings in pre-commit configuration

### Removed
- Redundant .ignition-lint-precommit.json file
- --pylintrc CLI argument (all configuration now via rule_config.json)
- Unnecessary target_node_types from rule_config.json (auto-derived)

## [0.2.4] - 2024-12-XX

### Added
- Configurable pylintrc parameter for PylintScriptRule
- Improved output capture for pylint script linting
- Makefile for convenience commands
- Support for CSS properties in style and elementStyle properties

### Fixed
- Model builder now properly handles arrays
- Event handler domain and event type extraction
- Transform script key now correctly uses "code"
- CSS property detection includes all style containers
- Pre-commit compatibility and configuration simplification
- View script linting issues

### Changed
- Debug files regenerated with corrected event handler extraction
- Rule coverage target types now sorted alphabetically

### Removed
- .DS_Store files from repository

## [0.2.3] - 2024-XX-XX

### Changed
- Reworked name rule to not require node_types list in arguments
- Updated pre-commit configuration

## [0.2.2] - 2024-XX-XX

### Fixed
- Severity levels on name patterns for different node types

## [0.2.1] - 2024-XX-XX

### Initial tracked release

[Unreleased]: https://github.com/design-group/ignition-lint/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/design-group/ignition-lint/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/design-group/ignition-lint/compare/v0.3.6...v0.4.0
[0.3.6]: https://github.com/design-group/ignition-lint/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/design-group/ignition-lint/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/design-group/ignition-lint/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/design-group/ignition-lint/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/design-group/ignition-lint/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/design-group/ignition-lint/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/design-group/ignition-lint/compare/v0.2.10...v0.3.0
[0.2.10]: https://github.com/design-group/ignition-lint/compare/v0.2.9...v0.2.10
[0.2.9]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.8...v0.2.9
[0.2.8]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.7...v0.2.8
[0.2.7]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/bw-design-group/ignition-lint/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/bw-design-group/ignition-lint/releases/tag/v0.2.1
