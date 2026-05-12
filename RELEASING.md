# Release Process for ignition-lint

## Overview
This document describes the process for releasing new versions of ignition-lint to PyPI.

## Prerequisites
- Maintainer access to GitHub repository
- PyPI credentials configured in GitHub Actions secrets
- All tests passing on main branch
- CHANGELOG.md updated with release notes

## Semantic Versioning
This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backwards-compatible
- **PATCH** (0.0.X): Bug fixes, backwards-compatible

## Release Steps (Fully Automated)

**Workflow Context:**
- Feature development: `feature/*` → PR → `dev` (protected)
- Release prep: RC tag on dev → automated PR creation
- Production release: Tag main → PyPI publish

### Step 1: Tag Dev with Release Candidate

Once all features are merged to dev and you're ready to release:

```bash
git checkout dev
git pull origin dev

# Tag with RC version (triggers automation)
git tag v0.3.1-RC1 -m "Release candidate for v0.3.1"
git push origin v0.3.1-RC1
```

**What happens automatically:**
1. 🤖 GitHub Action triggers on RC tag push
2. 🤖 Extracts version (v0.3.1-RC1 → 0.3.1)
3. 🤖 Finds commits since last release tag
4. 🤖 Generates changelog from commit messages
5. 🤖 Updates `pyproject.toml` version
6. 🤖 Updates `CHANGELOG.md` with generated content
7. 🤖 Commits changes to dev
8. 🤖 Creates PR: dev → main with full changelog

### Step 2: Review and Approve PR

1. Go to Pull Requests → "Release vX.Y.Z"
2. Review the auto-generated changelog
3. **Edit CHANGELOG.md if needed** (fix categorization, add details)
4. Ensure CI checks pass
5. Approve and merge PR to main

### Step 3: Tag Production Release on Main
After PR is merged to main:

```bash
git checkout main
git pull origin main

# Create production release tag
git tag v0.3.1 -m "Release v0.3.1"
git push origin v0.3.1
```

**This triggers the automated PyPI publish workflow.**

### Step 4: Create GitHub Release (Optional but Recommended)
1. Go to https://github.com/bw-design-group/ignition-lint/releases/new
2. Select tag: v0.3.1
3. Release title: "v0.3.1"
4. Click "Generate release notes" or copy from CHANGELOG.md
5. Click "Publish release"

**Note:** GitHub Release is optional. PyPI publish triggers on tag push (Step 3).

### Step 5: Verify PyPI Publication
The publish workflow automatically:
1. Triggers on production tag push (v0.3.1)
2. Builds package with Poetry
3. Publishes to PyPI using configured token

**Monitor progress:**
- Actions: https://github.com/bw-design-group/ignition-lint/actions
- PyPI: https://pypi.org/project/ignition-lint/

### Step 6: Verify Installation
```bash
# Wait 1-2 minutes for PyPI propagation
pip install ignition-lint==X.Y.Z

# Verify version
ignition-lint --version
```

## Testing Release Process

### Test PyPI Workflow
Before production release, test with Test PyPI:

```bash
# 1. Manually trigger workflow
# Go to Actions → Publish to PyPI → Run workflow
# Check "test_pypi" option

# 2. After workflow completes, test installation
pip install --index-url https://test.pypi.org/simple/ ignition-lint==0.3.1
```

## Changelog Maintenance

The release automation transforms your manually maintained changelog.

### Your Workflow: Maintain CHANGELOG.md as You Work

```markdown
# Changelog

## [Unreleased]

### Added
- Support for Python 3.13
- New BadComponentReferenceRule

### Fixed
- Remove unused ignition-api-stubs dependency
- Correct false positive in name pattern

### Changed
- Move pre-commit to dev dependencies
```

### Automation: Version Numbers and Dates

When you tag RC, the automation transforms it to:

```markdown
# Changelog

## [Unreleased]

## [0.3.1] - 2026-02-01

### Added
- Support for Python 3.13
- New BadComponentReferenceRule

### Fixed
- Remove unused ignition-api-stubs dependency
- Correct false positive in name pattern

### Changed
- Move pre-commit to dev dependencies

[Unreleased]: https://github.com/.../compare/v0.3.1...HEAD
[0.3.1]: https://github.com/.../compare/v0.3.0...v0.3.1
```

**Key Points:**
- ✅ You write the changelog as you work (or before RC tag)
- ✅ Automation handles version numbers and dates
- ✅ Can edit in PR if you forgot something
- ✅ Follows "Keep a Changelog" format

## Rollback Procedure

If issues are discovered after release:

1. **Cannot delete from PyPI** - versions are permanent
2. **Yank the release**: Mark as unstable on PyPI (prevents new installs)
3. **Release patch version**: Fix issues and release next version
4. **Update documentation**: Note issues in CHANGELOG.md

## Troubleshooting

### Build Failures
- Check Poetry configuration: `poetry check`
- Validate dependencies: `poetry update`
- Test local build: `poetry build`

### Authentication Errors
- Verify PYPI_API_TOKEN is configured in GitHub secrets
- Check token hasn't expired
- Ensure token has correct scope (project-specific)

### Version Conflicts
- Ensure pyproject.toml version matches git tag
- Check PyPI doesn't already have this version
- Version numbers cannot be reused

### RC Tag Issues
- RC tags must follow format: `v*-RC*` (e.g., v0.3.1-RC1, v1.0.0-RC2)
- Verify workflow triggers: Actions → Prepare Release from RC Tag
- Check workflow logs for sed/git errors

### PR Creation Failures
- Ensure GITHUB_TOKEN has write permissions
- Check branch protection settings allow bot commits
- Verify no conflicting PRs exist (dev → main)

## Emergency Contact
For urgent release issues, contact repository maintainers:
- Eric Knorr
- Alex Spyksma

## Appendix: Manual Release (Fallback)

If automated workflows fail, you can release manually:

```bash
# 1. Update version
poetry version 0.3.1

# 2. Update CHANGELOG.md manually

# 3. Commit and push
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Prepare release v0.3.1"
git push origin dev

# 4. Merge dev to main (via PR or direct)

# 5. Tag main
git checkout main
git pull
git tag v0.3.1 -m "Release v0.3.1"
git push origin v0.3.1

# 6. Build and publish
poetry build
poetry publish

# 7. Create GitHub Release manually
```

## Appendix: Poetry Publishing Commands Reference

### Configuration
```bash
# View current configuration
poetry config --list

# Add Test PyPI repository
poetry config repositories.testpypi https://test.pypi.org/legacy/

# Configure PyPI token (alternative to secrets)
poetry config pypi-token.pypi <token>
poetry config pypi-token.testpypi <token>
```

### Building
```bash
# Build package (creates wheel and tarball in dist/)
poetry build

# Build only wheel
poetry build -f wheel

# Build only sdist (source distribution)
poetry build -f sdist

# Clean previous builds
rm -rf dist/ build/ *.egg-info
```

### Publishing
```bash
# Publish to PyPI (prompts for credentials if not configured)
poetry publish

# Publish to Test PyPI
poetry publish -r testpypi

# Build and publish in one command
poetry publish --build

# Dry run (validate without publishing)
poetry publish --dry-run
```

### Validation
```bash
# Check pyproject.toml validity
poetry check

# Show package information
poetry show --tree

# Verify what will be included in package
poetry build -v
```

## First Release Setup (v0.3.0)

This section documents the initial PyPI setup steps (already completed for v0.3.0).

### PyPI Account Setup
1. Created accounts on https://pypi.org and https://test.pypi.org
2. Enabled 2FA for security
3. Generated API tokens (account scope for first release)

### Initial Manual Publish
```bash
# Test with Test PyPI first
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry build
poetry publish -r testpypi

# Verify test installation
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    ignition-lint==0.3.0

# Production publish
poetry publish

# Create git tag
git tag v0.3.0 -m "Release v0.3.0 - First PyPI publication"
git push origin v0.3.0
```

### Token Scope Restriction
After first publish, API tokens were restricted to project scope:
1. Deleted account-scoped tokens
2. Created new project-scoped tokens
3. Updated GitHub secrets

This limits the blast radius if tokens are compromised.
