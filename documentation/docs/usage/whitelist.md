---
title: Whitelist
sidebar_label: Whitelist
description: Exempt specific files from linting to manage technical debt
---

# Whitelist

The whitelist feature exempts specific files from linting. It's the right tool for managing technical debt at scale — when you have legacy views that violate today's rules but can't be refactored immediately.

By default ignition-lint does **not** use a whitelist. You have to opt in explicitly with `--whitelist <path>`.

## Quick start

```bash
# 1. Generate a whitelist from your legacy directories
ign-lint --generate-whitelist "views/legacy/**/*.json" "views/deprecated/**/*.json"

# 2. Lint with the whitelist
ign-lint --config rule_config.json --whitelist .whitelist.txt --files "**/view.json"
```

## File format

- **Filename**: `.whitelist.txt` (recommended default)
- **Location**: anywhere; pass via `--whitelist <path>`
- **Format**: plain text, one path per line, relative to the repository root
- **Comments**: lines starting with `#` are ignored
- **Blank lines**: ignored
- **Globs**: not supported in the file (use `--generate-whitelist` to expand them)

```text
# Legacy views — scheduled for refactor Q2 2026 (JIRA-1234)
views/legacy/OldDashboard/view.json
views/legacy/MainScreen/view.json

# Deprecated views — being replaced
views/deprecated/TempView/view.json

# Third-party vendor code (cannot modify)
views/vendor/VendorDashboard/view.json
```

## Generating

```bash
# Single pattern
ign-lint --generate-whitelist "views/legacy/**/*.json"

# Multiple patterns
ign-lint --generate-whitelist \
    "views/legacy/**/*.json" \
    "views/deprecated/**/*.json"

# Custom output filename
ign-lint --generate-whitelist "views/legacy/**/*.json" \
    --whitelist-output custom-whitelist.txt

# Append to existing whitelist (deduplicates automatically)
ign-lint --generate-whitelist "views/temp/**/*.json" --append

# Preview without writing
ign-lint --generate-whitelist "views/legacy/**/*.json" --dry-run
```

## Using

```bash
# Whitelist enabled
ign-lint --config rule_config.json --whitelist .whitelist.txt --files "**/view.json"

# Whitelist disabled (overrides --whitelist if both are set)
ign-lint --config rule_config.json --whitelist .whitelist.txt --no-whitelist --files "**/view.json"

# Verbose mode shows ignored files
ign-lint --config rule_config.json --whitelist .whitelist.txt --files "**/view.json" --verbose
```

Verbose output:

```
Loaded whitelist with 612 files
Ignored 8 whitelisted files
  • views/legacy/Dashboard/view.json
  • views/legacy/MainScreen/view.json
  ... and 6 more files
```

## CLI reference

| Flag | Description |
| --- | --- |
| `--whitelist <path>` | Path to a whitelist file |
| `--no-whitelist` | Disable whitelist (overrides `--whitelist`) |
| `--generate-whitelist <pattern>...` | Generate from glob patterns |
| `--whitelist-output <path>` | Output file for `--generate-whitelist` (default: `.whitelist.txt`) |
| `--append` | Append to existing whitelist |
| `--dry-run` | Preview without writing |

## Pre-commit integration

Add `--whitelist` to your hook args:

```yaml
repos:
  - repo: https://github.com/bw-design-group/ignition-lint
    rev: v0.2.4
    hooks:
      - id: ign-lint
        args: ['--config=rule_config.json', '--whitelist=.whitelist.txt', '--files']
```

The full workflow:

```bash
# 1. Generate whitelist
ign-lint --generate-whitelist "views/legacy/**/*.json"

# 2. Annotate it (add comments explaining why files are whitelisted)
$EDITOR .whitelist.txt

# 3. Commit
git add .whitelist.txt
git commit -m "Add whitelist for legacy views (technical debt — JIRA-1234)"

# 4. Update pre-commit config
$EDITOR .pre-commit-config.yaml  # add --whitelist=.whitelist.txt
git add .pre-commit-config.yaml
git commit -m "Wire whitelist into pre-commit"
```

## Best practices

### Document why every entry exists

A whitelist without explanation rots into permanent dead weight. Use comments:

```text
# Wrong context
views/legacy/Dashboard/view.json

# Tracked debt with a date
# Legacy views — refactor scheduled Q2 2026 (JIRA-1234)
views/legacy/Dashboard/view.json
```

### Group related entries

```text
# Legacy views (pre-2024)
views/legacy/Dashboard/view.json
views/legacy/MainScreen/view.json

# Deprecated views (replaced in v2.0)
views/deprecated/OldWidget/view.json

# Third-party vendor code (cannot modify)
views/vendor/VendorDashboard/view.json
```

### Review periodically

Set a calendar reminder. Quarterly is reasonable. Look for:

- Files that no longer exist (the path is stale)
- JIRA tickets that have been closed (the debt is paid; remove the entry)
- Files that have been refactored since you whitelisted them (rerun the linter; remove if it passes)

A quick health check:

```bash
# List whitelisted files that no longer exist
while IFS= read -r file; do
  [[ "$file" =~ ^# ]] && continue
  [[ -z "$file" ]] && continue
  [[ ! -f "$file" ]] && echo "Missing: $file"
done < .whitelist.txt
```

### Commit the whitelist

The whitelist is project configuration. Commit it. Don't `.gitignore` it.

## Performance

Whitelist filtering is fast: O(1) per file via a hash set. Loading a 600-file whitelist + filtering 900 files adds < 2 ms total. The bottleneck remains reading view.json files, not the whitelist.

## Troubleshooting

### Files still being linted despite being whitelisted

Verify the whitelist is loading:

```bash
ign-lint --config rule_config.json --whitelist .whitelist.txt --files "**/view.json" --verbose
# Should print: Loaded whitelist with N files
```

Check the path format — entries must be **relative to the repo root**:

```text
# Right
views/legacy/Dashboard/view.json

# Wrong
/Users/me/projects/myapp/views/legacy/Dashboard/view.json
```

### Pre-commit isn't using the whitelist

Verify `--whitelist=.whitelist.txt` is in the `args` list of your `.pre-commit-config.yaml`. Pre-commit doesn't pick up the whitelist by default — you have to add the flag.

### `--no-whitelist` doesn't seem to do anything

`--no-whitelist` is only meaningful when `--whitelist` is also set. With no `--whitelist` flag at all, no whitelist is being used in the first place.

## FAQ

**Q: Do I have to use a whitelist?**
A: No. By default ignition-lint processes every file passed to it.

**Q: Can I use globs in the whitelist file?**
A: No — only explicit paths. Use `--generate-whitelist` with globs to expand them once into the file.

**Q: Can I have multiple whitelist files?**
A: Only one per invocation. Combine them manually, or use `--append` to merge.

**Q: Does whitelisting hide a file from output entirely?**
A: With `--verbose`, ignored files are reported. Without verbose, they're silently skipped.

## See also

- [Pre-commit integration](./pre-commit.md)
- [Command line](./cli.md)
- [Configuration](../getting-started/configuration.md)
