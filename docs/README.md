# ignition-lint Developer Documentation

Welcome to the comprehensive developer documentation for ignition-lint! This guide will help you get started with the framework, create custom linting rules, and contribute to the project.

## 🚀 Quick Start

**New to ignition-lint?** Start here:
1. [**Getting Started Tutorial**](#tutorial-creating-your-first-rule) - Build your first rule in 15 minutes
2. [**Developer Guide**](#developer-guide) - Complete reference for rule development
3. [**API Reference**](#api-reference) - Detailed API documentation

**Experienced developer?** Jump to:
- [**API Reference**](#api-reference) - Complete registry API documentation
- [**Troubleshooting**](#troubleshooting) - Common issues and solutions

## 📋 Table of Contents

### Core Documentation

| Document | Description | Best For |
|----------|-------------|----------|
| [**Tutorial: Creating Your First Rule**](tutorial-creating-your-first-rule.md) | Step-by-step hands-on tutorial | Beginners, first-time rule developers |
| [**Developer Guide: Creating Custom Rules**](developer-guide-rule-creation.md) | Comprehensive rule development guide | All developers, complete reference |
| [**API Reference: Rule Registration System**](api-reference-rule-registration.md) | Complete API documentation | Advanced developers, integration work |
| [**Troubleshooting Guide**](troubleshooting-rule-development.md) | Common issues and solutions | When things don't work as expected |

### Project Documentation

| Document | Description | Best For |
|----------|-------------|----------|
| [**Rule Organization Guide**](rule-organization-guide.md) | Rule and test structure organization | Rule developers, project architects |
| [**Local GitHub Actions Testing**](local-github-actions-testing.md) | Test CI/CD workflows locally | Contributors, CI debugging |
| [**Brownfield Architecture**](brownfield-architecture.md) | Project evolution and architecture | Understanding project history |
| [**PRD (Product Requirements)**](prd.md) | Product requirements and planning | Project planning, feature development |

## 📖 Documentation Guide by Use Case

### 🔰 "I want to create my first rule"
**→ Start with:** [Tutorial: Creating Your First Rule](tutorial-creating-your-first-rule.md)

This tutorial will walk you through:
- Setting up your development environment
- Understanding the rule structure
- Creating a complete working rule
- Testing your rule
- Configuring and using your rule

**Time required:** ~30 minutes

### 🔧 "I need to understand the rule system"
**→ Go to:** [Developer Guide: Creating Custom Rules](developer-guide-rule-creation.md)

This comprehensive guide covers:
- Rule development concepts and patterns
- Node types and visitor pattern
- Registration methods and best practices
- Configuration and preprocessing
- Advanced features and cross-node analysis

**Time required:** ~1 hour for complete understanding

### ⚙️ "I need API documentation"
**→ Check:** [API Reference: Rule Registration System](api-reference-rule-registration.md)

Complete API reference including:
- `RuleRegistry` class and methods
- Global functions and decorators
- Exception classes and error handling
- Integration patterns and examples

**Time required:** ~15 minutes to find what you need

### 🐛 "Something's not working"
**→ Visit:** [Troubleshooting Guide](troubleshooting-rule-development.md)

Comprehensive troubleshooting covering:
- Rule registration issues
- Import and module problems
- Configuration issues
- Testing problems
- Runtime errors and performance issues

**Time required:** ~5-10 minutes to find your specific issue

## 🏗️ Framework Architecture Overview

ignition-lint is built on a modular architecture with these key components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   JSON Files    │───▶│ Object Model     │───▶│ Visitor Rules   │
│ (view.json)     │    │ (ViewNode tree)  │    │ (Custom Logic)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ JSON Flattening │    │ Model Builder    │    │ Rule Registry   │
│ (path-value)    │    │ (Tree Creation)  │    │ (Auto Discovery)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Key Concepts:**
- **JSON Flattening**: Converts hierarchical JSON to path-value pairs
- **Object Model**: Builds structured ViewNode representations
- **Visitor Pattern**: Rules process specific node types via visitor methods
- **Rule Registry**: Automatic discovery and validation of custom rules

## 🎯 Rule Development Quick Reference

### Basic Rule Structure
```python
from .common import LintingRule
from .registry import register_rule
from ..model.node_types import NodeType

@register_rule
class MyRule(LintingRule):
    def __init__(self, param="default"):
        super().__init__({NodeType.COMPONENT})
        self.param = param

    @property
    def error_message(self) -> str:
        return "Description of what this rule checks"

    def visit_component(self, component):
        if some_condition:
            self.errors.append(f"{component.path}: Error message")
```

### Common Node Types
- `NodeType.COMPONENT` - UI components (buttons, labels, etc.)
- `NodeType.EXPRESSION_BINDING` - Expression-based bindings
- `NodeType.TAG_BINDING` - Tag-based bindings
- `ALL_SCRIPTS` - All script types (message handlers, transforms, etc.)

### Configuration Example
```json
{
  "MyRule": {
    "enabled": true,
    "kwargs": {
      "param": "custom_value"
    }
  }
}
```

## 🔗 Inter-Document Navigation

### From Tutorial → Other Docs
- **Need more details?** → [Developer Guide](developer-guide-rule-creation.md)
- **API questions?** → [API Reference](api-reference-rule-registration.md)
- **Having issues?** → [Troubleshooting Guide](troubleshooting-rule-development.md)

### From Developer Guide → Other Docs
- **Want hands-on practice?** → [Tutorial](tutorial-creating-your-first-rule.md)
- **Need API details?** → [API Reference](api-reference-rule-registration.md)
- **Stuck on something?** → [Troubleshooting Guide](troubleshooting-rule-development.md)

### From API Reference → Other Docs
- **Want practical examples?** → [Developer Guide](developer-guide-rule-creation.md) or [Tutorial](tutorial-creating-your-first-rule.md)
- **Having integration issues?** → [Troubleshooting Guide](troubleshooting-rule-development.md)

## 🛠️ Development Workflow

### For New Contributors
1. **Read:** [Tutorial: Creating Your First Rule](tutorial-creating-your-first-rule.md)
2. **Practice:** Build the example rule from the tutorial
3. **Reference:** Use [Developer Guide](developer-guide-rule-creation.md) for advanced features
4. **Debug:** Check [Troubleshooting Guide](troubleshooting-rule-development.md) if needed

### For Experienced Developers
1. **Reference:** [API Reference](api-reference-rule-registration.md) for quick lookups
2. **Deep Dive:** [Developer Guide](developer-guide-rule-creation.md) for comprehensive patterns
3. **Debug:** [Troubleshooting Guide](troubleshooting-rule-development.md) for specific issues

### For Contributors and Maintainers
1. **Organization:** [Rule Organization Guide](rule-organization-guide.md) for project structure
2. **Architecture:** [Brownfield Architecture](brownfield-architecture.md) for system understanding
3. **Testing:** [Local GitHub Actions Testing](local-github-actions-testing.md) for CI validation
4. **Planning:** [PRD Documentation](prd.md) for feature requirements

## 📝 Quick Commands Reference

```bash
# Create and test a rule
poetry install
poetry shell

# Run your rule
poetry run python -m ignition_lint --config your_config.json path/to/view.json

# Run tests
cd tests
python test_runner.py --run-all

# Test CI locally
./test-actions.sh
```

## 🤝 Getting Help

### Documentation Issues
- **Can't find what you need?** → Check [Troubleshooting Guide](troubleshooting-rule-development.md)
- **Documentation unclear?** → Open an issue with suggestions for improvement

### Development Issues
- **Rule not working?** → [Troubleshooting Guide](troubleshooting-rule-development.md) has common solutions
- **API questions?** → [API Reference](api-reference-rule-registration.md) has complete specifications
- **Need examples?** → [Developer Guide](developer-guide-rule-creation.md) has multiple complete examples

### Community Support
- **Issues and Bugs:** Use the project's issue tracker
- **Feature Requests:** Check the [PRD](prd.md) and submit enhancement requests
- **Questions:** Start with this documentation, then reach out to maintainers

## 🎉 Success Stories

**"I created my first rule in 20 minutes using the tutorial!"** - Follow the [Tutorial](tutorial-creating-your-first-rule.md) for a similar experience.

**"The API reference made integration straightforward."** - Use the [API Reference](api-reference-rule-registration.md) for your integration needs.

**"The troubleshooting guide saved me hours of debugging."** - Bookmark the [Troubleshooting Guide](troubleshooting-rule-development.md) for quick issue resolution.

---

## 📚 Additional Resources

- **Example Rules:** `src/ignition_lint/rules/_examples/example_rule.py` (excluded from auto-discovery)
- **Test Cases:** `tests/cases/` for real view.json examples
- **Configuration Examples:** `tests/configs/` for rule configuration patterns
- **Framework Code:** `src/ignition_lint/` for understanding internals

**Happy rule development! 🚀**
