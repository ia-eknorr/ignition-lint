"""
Command-line interface for ignition-lint.
"""

import json
import os
import sys
import argparse
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
	from importlib.metadata import version, PackageNotFoundError
except ImportError:
	# Python < 3.8
	from importlib_metadata import version, PackageNotFoundError

LINE_WIDTH = 120


def get_version() -> str:
	"""Get package version, with fallback for development/testing."""
	try:
		return version('ignition-lint')
	except PackageNotFoundError:
		# Package not installed (development/testing mode)
		# Try to read version from pyproject.toml
		try:
			# Python 3.11+ has tomllib built-in
			try:
				import tomllib
			except ImportError:
				# Python < 3.11, try tomli if available
				try:
					import tomli as tomllib
				except ImportError:
					# No TOML parser available, return dev
					return 'dev'

			pyproject_path = Path(__file__).parent.parent.parent / 'pyproject.toml'
			if pyproject_path.exists():
				with open(pyproject_path, 'rb') as f:
					data = tomllib.load(f)
					return data.get('tool', {}).get('poetry', {}).get('version', 'dev')
		except Exception:
			pass
		return 'dev'


# Handle both relative and absolute imports
try:
	# Try relative imports first (when run as module)
	from .common.flatten_json import read_json_file, write_json_file, flatten_json
	from .common.timing import PerformanceTimer, TimingCollector, FileTimings
	from .common.path_translator import PathTranslator
	from .common.fix_engine import FixEngine
	from .common.fix_operations import FixOperationType
	from .linter import LintEngine
	from .rules import RULES_MAP
except ImportError:
	# Fall back to absolute imports (when run directly or from tests)
	current_dir = Path(__file__).parent
	src_dir = current_dir.parent
	if str(src_dir) not in sys.path:
		sys.path.insert(0, str(src_dir))

	from ignition_lint.common.flatten_json import read_json_file, write_json_file, flatten_json
	from ignition_lint.common.timing import PerformanceTimer, TimingCollector, FileTimings
	from ignition_lint.common.path_translator import PathTranslator
	from ignition_lint.common.fix_engine import FixEngine
	from ignition_lint.common.fix_operations import FixOperationType
	from ignition_lint.linter import LintEngine
	from ignition_lint.rules import RULES_MAP


def cleanup_debug_files() -> None:
	"""
	Clean up old debug files from previous runs to prevent unbounded growth.

	Debug files are Python scripts saved by PylintScriptRule for troubleshooting.
	This removes files from previous runs (different PIDs) while preserving recent files.
	"""
	import time

	# Determine debug directory using same logic as PylintScriptRule
	cwd = os.getcwd()
	debug_dir = None

	# Check if we're in test environment (same logic as _get_debug_directory)
	current_path = cwd
	while current_path != os.path.dirname(current_path):
		if os.path.basename(current_path) == 'tests':
			debug_dir = os.path.join(current_path, "debug")
			break
		elif os.path.exists(os.path.join(current_path, 'tests')):
			debug_dir = os.path.join(current_path, "tests", "debug")
			break
		current_path = os.path.dirname(current_path)

	# Fallback to .ignition-lint/debug
	if not debug_dir:
		debug_dir = os.path.join(cwd, ".ignition-lint", "debug")

	# Only clean if directory exists
	if not os.path.exists(debug_dir):
		return

	current_pid = os.getpid()
	current_time = time.time()

	# Find all .py debug files (format: HHMMSS_pid{PID}_{random}.py)
	files_to_clean = []
	for file_path in Path(debug_dir).glob("*_pid*_*.py"):
		# Extract PID from filename
		if f'_pid{current_pid}_' in file_path.name:
			# Same PID as current run - skip
			continue

		# Check if file is recent (less than 5 seconds old)
		try:
			file_age = current_time - file_path.stat().st_mtime
			if file_age < 5:
				# Very recent file, likely from parallel process - skip
				continue
		except OSError:
			pass

		# Old debug file from previous run - mark for deletion
		files_to_clean.append(file_path)

	# Clean up old files
	if files_to_clean:
		for file_path in files_to_clean:
			try:
				file_path.unlink()
			except OSError:
				# Silently ignore errors
				pass


def cleanup_old_batch_files(output_path: Path) -> None:
	"""
	Clean up old batch files from previous runs to prevent unbounded growth.

	This function is called at the start of a run, before any results are written.
	It removes batch files from previous runs (identified by different PIDs) but
	preserves files from the current run (same PID or very recent).
	"""
	import time

	if not output_path.parent.exists():
		return

	# Get current PID
	current_pid = os.getpid()
	current_time = time.time()

	# Find all related files (both base file and batch files)
	base_name = output_path.stem

	files_to_clean = []

	# Check the base file (e.g., results.txt)
	if output_path.exists():
		try:
			file_age = current_time - output_path.stat().st_mtime
			if file_age >= 5:
				# Old base file from previous run - mark for deletion
				files_to_clean.append(output_path)
		except OSError:
			pass

	# Check batch files (e.g., results_pid*_batch*.txt)
	pattern = f"{base_name}*batch*.txt"
	for file_path in output_path.parent.glob(pattern):
		# Extract PID from filename (e.g., results_pid12345_batch1.txt)
		if f'_pid{current_pid}_' in file_path.name:
			# Same PID as current run - skip
			continue

		# Check if file is recent (less than 5 seconds old)
		# This protects against race conditions with parallel processes
		try:
			file_age = current_time - file_path.stat().st_mtime
			if file_age < 5:
				# Very recent file, likely from parallel process - skip
				continue
		except OSError:
			pass

		# Old batch file from previous run - mark for deletion
		files_to_clean.append(file_path)

	# Check aggregated summary file (e.g., results_AGGREGATED_SUMMARY.txt)
	# These have no PID in the name, so age-based check only.
	# Stale summaries pollute new runs by reporting old totals (see
	# aggregate_batch_results: it reads an existing summary for non-batch paths).
	summary_file = output_path.parent / f"{base_name}_AGGREGATED_SUMMARY.txt"
	if summary_file.exists():
		try:
			file_age = current_time - summary_file.stat().st_mtime
			if file_age >= 5:
				files_to_clean.append(summary_file)
		except OSError:
			pass

	# Clean up old files
	if files_to_clean:
		for file_path in files_to_clean:
			try:
				file_path.unlink()
			except OSError as e:
				# Silently ignore errors (file might be in use or already deleted)
				pass


def make_unique_output_path(original_path: Path) -> Path:
	"""
	Generate a unique output file path to prevent overwriting in batch processing.

	When pre-commit or other tools run ignition-lint in multiple batches,
	each batch would overwrite the same output file. This function ensures
	uniqueness by appending PID and batch number if the file already exists.

	Examples:
		results.txt -> results.txt (if doesn't exist)
		results.txt -> results_pid12345_batch1.txt (if exists)
		results.txt -> results_pid12345_batch2.txt (if batch1 also exists)
	"""
	if not original_path.exists():
		return original_path

	# File exists - make it unique with PID and batch number
	pid = os.getpid()
	stem = original_path.stem  # filename without extension
	suffix = original_path.suffix  # .txt, .json, etc.
	parent = original_path.parent

	# Try adding batch numbers until we find one that doesn't exist
	batch_num = 1
	while True:
		new_name = f"{stem}_pid{pid}_batch{batch_num}{suffix}"
		new_path = parent / new_name
		if not new_path.exists():
			return new_path
		batch_num += 1


def load_config(config_path: str) -> Optional[dict]:
	"""
	Load configuration from a JSON file.

	Returns the parsed dict on success (which may legitimately be empty when
	the user wants to run all rules with default kwargs), or None if the file
	cannot be read or parsed.
	"""
	try:
		with open(config_path, 'r', encoding='utf-8') as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError) as e:
		print(f"Error loading config file {config_path}: {e}")
		return None


def load_whitelist(whitelist_path: str) -> set:
	"""
	Load whitelist file containing paths to ignore.

	Args:
		whitelist_path: Path to whitelist text file

	Returns:
		Set of absolute file paths to ignore (empty set if file doesn't exist)
	"""
	whitelist = set()

	try:
		whitelist_file = Path(whitelist_path)
		if not whitelist_file.exists():
			return whitelist

		with open(whitelist_file, 'r', encoding='utf-8') as f:
			for line in f:
				# Strip whitespace
				line = line.strip()

				# Skip empty lines and comments
				if not line or line.startswith('#'):
					continue

				# Convert relative path to absolute
				try:
					file_path = Path(line).resolve()
					whitelist.add(file_path)
				except (ValueError, OSError) as e:
					print(f"⚠️  Warning: Invalid path in whitelist '{line}': {e}")
					continue

		return whitelist

	except (OSError, IOError) as e:
		print(f"⚠️  Warning: Could not read whitelist file {whitelist_path}: {e}")
		return set()


def generate_whitelist(patterns: List[str], output_file: str, append: bool = False, dry_run: bool = False) -> None:
	"""
	Generate whitelist file from glob patterns.

	Args:
		patterns: List of glob patterns to match files
		output_file: Path to output whitelist file
		append: If True, append to existing file; if False, overwrite
		dry_run: If True, print matched files without writing
	"""
	# Collect all matching files
	all_files = []
	for pattern in patterns:
		matching_files = glob.glob(pattern, recursive=True)
		all_files.extend(matching_files)

	# Convert to relative paths and sort
	relative_paths = []
	cwd = Path.cwd()
	for file_path in all_files:
		try:
			abs_path = Path(file_path).resolve()
			relative_path = abs_path.relative_to(cwd)
			relative_paths.append(str(relative_path))
		except (ValueError, OSError):
			# If path can't be made relative, use absolute
			relative_paths.append(file_path)

	# Remove duplicates and sort
	relative_paths = sorted(set(relative_paths))

	if dry_run:
		print(f"🔍 Would add {len(relative_paths)} files to whitelist:")
		for path in relative_paths[:20]:  # Show first 20
			print(f"  {path}")
		if len(relative_paths) > 20:
			print(f"  ... and {len(relative_paths) - 20} more files")
		return

	# Handle append mode
	existing_paths = set()
	if append and Path(output_file).exists():
		try:
			with open(output_file, 'r', encoding='utf-8') as f:
				for line in f:
					line = line.strip()
					if line and not line.startswith('#'):
						existing_paths.add(line)
		except (OSError, IOError) as e:
			print(f"⚠️  Warning: Could not read existing whitelist: {e}")

	# Combine existing and new paths
	if append:
		all_paths = sorted(existing_paths.union(set(relative_paths)))
	else:
		all_paths = relative_paths

	# Write whitelist file
	try:
		output_path = Path(output_file)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		with open(output_path, 'w', encoding='utf-8') as f:
			f.write("# Ignition-lint whitelist - files to ignore during linting\n")
			f.write("# Lines starting with # are comments\n")
			f.write("# One file path per line (relative to repository root)\n")
			f.write(f"# Generated: {len(relative_paths)} files added\n")
			if append and existing_paths:
				f.write(f"# Existing: {len(existing_paths)} files\n")
			f.write("\n")

			for path in all_paths:
				f.write(f"{path}\n")

		mode = "appended to" if append and existing_paths else "generated"
		print(f"✓ Whitelist {mode}: {output_path}")
		print(f"  Total files: {len(all_paths)}")
		if append and existing_paths:
			print(f"  New files: {len(relative_paths)}")
			print(f"  Existing files: {len(existing_paths)}")

	except (OSError, IOError) as e:
		print(f"❌ Error writing whitelist file {output_file}: {e}")
		sys.exit(1)


def create_rules_from_config(config: dict) -> tuple:
	"""
	Create rule instances for every registered rule.

	All registered rules run by default. The user's config provides per-rule
	overrides: `kwargs` to customize behavior, or `enabled: false` to opt out.
	Rules absent from the config run with default kwargs.

	Args:
		config: Configuration dictionary from config file (may be empty)

	Returns:
		Tuple of (rules, statuses):
			rules    -- list of instantiated LintingRule objects
			statuses -- list of dicts describing every registered rule, one per
						rule, with keys:
						  name   : rule class name
						  state  : "loaded" | "disabled" | "error"
						  source : "config" if user supplied kwargs, else "defaults"
						  detail : optional error/skip detail (str or None)
	"""
	# Always-on warning for config keys that don't resolve to a known rule.
	for rule_name, rule_config in config.items():
		if rule_name.startswith("_") or not isinstance(rule_config, dict):
			continue
		if rule_name not in RULES_MAP:
			print(f"Unknown rule in config: {rule_name}")

	rules = []
	statuses = []
	for rule_name, rule_class in RULES_MAP.items():
		rule_config = config.get(rule_name, {})
		if not isinstance(rule_config, dict):
			rule_config = {}

		has_user_kwargs = bool(rule_config.get('kwargs'))
		source = "config" if (rule_name in config or has_user_kwargs) else "defaults"

		if not rule_config.get('enabled', True):
			statuses.append({
				"name": rule_name,
				"state": "disabled",
				"source": source,
				"detail": "enabled=false",
			})
			continue

		kwargs = rule_config.get('kwargs', {})

		try:
			rules.append(rule_class.create_from_config(kwargs))
			statuses.append({
				"name": rule_name,
				"state": "loaded",
				"source": source,
				"detail": None,
			})
		except (TypeError, ValueError, AttributeError) as e:
			print(f"Error creating rule {rule_name}: {e}")
			statuses.append({
				"name": rule_name,
				"state": "error",
				"source": source,
				"detail": str(e),
			})
			continue

	return rules, statuses


def _print_rule_breakdown(statuses: list, config_path: str) -> None:
	"""
	Print a per-rule breakdown showing each registered rule's source.

	Called from setup_linter() under --verbose. Loaded rules are shown with
	their kwargs source (the config file or "defaults"); disabled rules are
	shown with the reason; rules that failed to instantiate are shown with
	the error.
	"""
	loaded = [s for s in statuses if s["state"] == "loaded"]
	disabled = [s for s in statuses if s["state"] == "disabled"]
	errored = [s for s in statuses if s["state"] == "error"]

	name_width = max((len(s["name"]) for s in statuses), default=0)
	print(f"✅ Loaded {len(loaded)} rules:")
	for status in loaded:
		source = f"config: {config_path}" if status["source"] == "config" else "defaults"
		print(f"  • {status['name']:<{name_width}}  ({source})")

	for status in disabled:
		print(f"  ⊘ {status['name']:<{name_width}}  (skipped: {status['detail']})")

	for status in errored:
		print(f"  ✗ {status['name']:<{name_width}}  (error: {status['detail']})")


def get_view_file(file_path: Path) -> Dict[str, Any]:
	"""Read and flatten a JSON file."""
	try:
		json_data = read_json_file(file_path)
		return flatten_json(json_data)
	except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError) as e:
		print(f"Error reading or parsing file {file_path}: {e}")
		return {}


def collect_files(args, whitelist: set) -> tuple[List[Path], List[Path]]:
	"""
	Collect files to process based on arguments.

	Args:
		args: Command-line arguments
		whitelist: Set of absolute file paths to ignore

	Returns:
		Tuple of (files_to_process, whitelisted_files)
	"""
	files_to_process = []
	files_ignored = []

	# If filenames are provided directly (e.g., from pre-commit), use them
	if args.filenames:
		for filename in args.filenames:
			file_path = Path(filename)
			if not file_path.exists():
				print(f"Warning: File {filename} does not exist")
				continue

			# Check if file is whitelisted
			abs_path = file_path.resolve()
			if abs_path in whitelist:
				files_ignored.append(file_path)
				# Always print when a file is skipped (not just verbose mode)
				print(f"🔒 Skipped (whitelisted): {file_path}")
				continue

			files_to_process.append(file_path)

	# Otherwise, use glob patterns
	elif args.files:
		for file_pattern in args.files.split(","):
			pattern = file_pattern.strip()
			matching_files = glob.glob(pattern, recursive=True)

			for file_path_str in matching_files:
				file_path = Path(file_path_str)
				# Only include view.json files specifically
				if not file_path.exists() or file_path.name != "view.json":
					continue

				# Check if file is whitelisted
				abs_path = file_path.resolve()
				if abs_path in whitelist:
					files_ignored.append(file_path)
					# Always print when a file is skipped (not just verbose mode)
					print(f"🔒 Skipped (whitelisted): {file_path}")
					continue

				files_to_process.append(file_path)

	# Print summary if verbose mode
	if files_ignored and args.verbose:
		print(f"\n📊 Whitelist Summary: {len(files_ignored)} files skipped")

	return files_to_process, files_ignored


def print_rule_violations(rule_name: str, violations: list, custom_formatted_output: str = None):
	"""
	Print violations for a rule, using custom formatting if available.

	Args:
		rule_name: Name of the rule
		violations: List of violation strings
		custom_formatted_output: Pre-captured custom formatted output for this severity
	"""
	if not violations and not custom_formatted_output:
		return

	print(f"\n  {rule_name}:")

	# Show regular violations first (e.g., indentation errors, data quality issues)
	# Filter out empty placeholders (used for counting only)
	if violations:
		for violation in violations:
			if violation.strip():  # Only show non-empty violations
				print(f"    • {violation}")

	# Then show custom formatted output (e.g., category-grouped pylint violations)
	if custom_formatted_output:
		print(custom_formatted_output)

	print()  # Extra blank line between rules


def print_file_results(lint_results, lint_engine=None) -> tuple[int, int]:
	"""
	Print warnings and errors for a file and return the counts.

	Args:
		lint_results: LintResults object containing warnings and errors
		lint_engine: Optional LintEngine instance (needed for custom rule formatting)

	Returns:
		tuple[int, int]: (warning_count, error_count)
	"""
	warning_count = sum(len(warning_list) for warning_list in lint_results.warnings.values())
	error_count = sum(len(error_list) for error_list in lint_results.errors.values())

	# Get custom formatted outputs if available
	custom_formatted_warnings = lint_results.custom_formatted_warnings if hasattr(
		lint_results, 'custom_formatted_warnings'
	) else {}
	custom_formatted_errors = lint_results.custom_formatted_errors if hasattr(
		lint_results, 'custom_formatted_errors'
	) else {}

	# Print errors first (more critical)
	# Show errors if there are regular violations OR custom formatted errors
	if error_count > 0 or custom_formatted_errors:
		print(f"\n❌ Found {error_count} errors:")
		for rule_name, error_list in lint_results.errors.items():
			custom_output = custom_formatted_errors.get(rule_name)
			print_rule_violations(rule_name, error_list, custom_formatted_output=custom_output)
		# Handle rules that only have custom formatted errors (no regular violations)
		for rule_name, custom_output in custom_formatted_errors.items():
			if rule_name not in lint_results.errors:
				print_rule_violations(rule_name, [], custom_formatted_output=custom_output)

	# Print warnings second
	# Show warnings if there are regular violations OR custom formatted warnings
	if warning_count > 0 or custom_formatted_warnings:
		print(f"\n⚠️  Found {warning_count} warnings:")
		for rule_name, warning_list in lint_results.warnings.items():
			custom_output = custom_formatted_warnings.get(rule_name)
			print_rule_violations(rule_name, warning_list, custom_formatted_output=custom_output)
		# Handle rules that only have custom formatted warnings (no regular violations)
		for rule_name, custom_output in custom_formatted_warnings.items():
			if rule_name not in lint_results.warnings:
				print_rule_violations(rule_name, [], custom_formatted_output=custom_output)

	return warning_count, error_count


def print_statistics(file_path: Path, stats: Dict[str, Any], verbose: bool = False):
	"""Print model statistics for a file."""
	if verbose:
		print(f"\n📊 Model statistics for {file_path}:")
		print(f"  Total nodes: {stats['total_nodes']}")

		print("  Node types found:")
		for node_type, count in stats['node_type_counts'].items():
			print(f"    {node_type}: {count}")

		if stats['components_by_type']:
			print("  Components by type:")
			for comp_type, count in stats['components_by_type'].items():
				print(f"    {comp_type}: {count}")

		if stats.get('rule_coverage'):
			print("  Rule coverage:")
			for rule_name, coverage in stats['rule_coverage'].items():
				target_types = ', '.join(coverage['target_types'])
				print(f"    {rule_name}: {coverage['applicable_node_count']} nodes ({target_types})")


def print_rule_analysis(lint_engine: LintEngine, flattened_json: Dict[str, Any]):
	"""Print detailed rule impact analysis."""
	analysis = lint_engine.analyze_rule_impact(flattened_json)

	print("\n🔍 Rule Impact Analysis:")
	for rule_name, rule_data in analysis.items():
		print(f"  📋 {rule_name}:")
		print(f"    Targets: {', '.join(rule_data['target_types'])}")
		print(f"    Will process: {rule_data['applicable_nodes']} nodes")

		if rule_data['node_details']:
			print("    Sample nodes:")
			for detail in rule_data['node_details']:
				print(f"      • {detail['path']}: {detail['summary']}")
		elif rule_data['sample_paths']:
			print(f"    Sample paths: {', '.join(rule_data['sample_paths'][:3])}")
		print()


def print_debug_nodes(lint_engine: LintEngine, flattened_json: Dict[str, Any], debug_node_types: List[str]):
	"""Print debug information for specific node types."""
	debug_nodes = lint_engine.debug_nodes(flattened_json, debug_node_types or [])
	if debug_node_types:
		print(f"\n🔧 Debug info for node types: {', '.join(debug_node_types)}")
	else:
		print("\n🔧 Debug info for all nodes:")

	for i, node_info in enumerate(debug_nodes[:10]):  # Limit to first 10
		print(f"  {i+1}. {node_info['path']} ({node_info['node_type']})")
		if 'summary' in node_info:
			print(f"     {node_info['summary']}")

	if len(debug_nodes) > 10:
		print(f"     ... and {len(debug_nodes) - 10} more nodes")


def setup_linter(args) -> LintEngine:
	"""Set up the linting engine with rules from configuration."""
	if args.stats_only:
		lint_engine = LintEngine([], debug_output_dir=args.debug_output)
	else:
		config = load_config(args.config)
		if config is None:
			print("❌ No valid configuration found")
			sys.exit(1)

		print(f"🔧 Loaded configuration from {args.config}")
		rules, rule_statuses = create_rules_from_config(config)
		if not rules:
			print("❌ No valid rules configured")
			sys.exit(1)

		lint_engine = LintEngine(rules, debug_output_dir=args.debug_output)

		if args.verbose:
			_print_rule_breakdown(rule_statuses, args.config)

	# Inform about debug output
	if args.debug_output:
		print(f"🔍 Debug output will be saved to: {args.debug_output}")

	return lint_engine


def process_single_file(
	file_path: Path, lint_engine: LintEngine, args, timer: Optional[PerformanceTimer] = None
) -> tuple[int, int, Optional[FileTimings], Optional[Any]]:
	"""Process a single view file and return the warning and error counts plus lint results."""
	if not file_path.exists():
		print(f"⚠️  File {file_path} does not exist, skipping")
		return 0, 0, None, None

	# Print file header before any processing
	print(f"\n📄 Evaluating file:\n    {file_path}")

	# Initialize timers if profiling is enabled
	file_timer = PerformanceTimer() if timer else None
	file_read_ms = 0.0
	flatten_ms = 0.0
	model_build_ms = 0.0
	rule_exec_ms = 0.0

	# Start overall file timing
	if file_timer:
		file_timer.start()

	# Time file reading
	if file_timer:
		timer.start()
	json_data = read_json_file(file_path)
	if file_timer:
		file_read_ms = timer.stop()

	if not json_data:
		print(f"❌ Failed to read file, skipping")
		return 0, 0, None, None

	# Time JSON flattening
	if file_timer:
		timer.start()
	flattened_json = flatten_json(json_data)
	if file_timer:
		flatten_ms = timer.stop()

	if not flattened_json:
		print(f"❌ Failed to parse file, skipping")
		return 0, 0, None, None

	# Time model building
	if file_timer:
		timer.start()
	stats = lint_engine.get_model_statistics(flattened_json)
	if file_timer:
		model_build_ms = timer.stop()

	print_statistics(file_path, stats, args.verbose or args.stats_only)

	# Show rule analysis if requested
	if args.analyze_rules and not args.stats_only:
		print_rule_analysis(lint_engine, flattened_json)

	# Show debug node info if requested
	if args.debug_nodes is not None:
		print_debug_nodes(lint_engine, flattened_json, args.debug_nodes)

	# Run linting (unless stats-only mode)
	file_timings = None
	if not args.stats_only:
		# Set up fix context if fix mode is active
		fix_mode = getattr(args, 'fix', False) or getattr(args, 'fix_dry_run', False)
		path_translator = None
		if fix_mode:
			path_translator = PathTranslator(json_data)

		# Time rule execution
		if file_timer:
			timer.start()
		lint_results = lint_engine.process(
			flattened_json, source_file_path=str(file_path), enable_timing=bool(file_timer),
			json_data=json_data if fix_mode else None, path_translator=path_translator
		)
		if file_timer:
			rule_exec_ms = timer.stop()

		file_warnings, file_errors = print_file_results(lint_results, lint_engine)

		if file_errors == 0 and file_warnings == 0:
			print(f"✅ No issues found")

		# Handle fixes if fix mode is active and there are fixes
		if fix_mode and lint_results.fixes:
			fix_engine = FixEngine(path_translator)
			safe_only = not getattr(args, 'fix_unsafe', False)
			rule_filter = None
			if getattr(args, 'fix_rules', None):
				rule_filter = [r.strip() for r in args.fix_rules.split(',')]

			if getattr(args, 'fix_dry_run', False):
				# Dry run: preview without modifying
				fix_result = fix_engine.dry_run(
					lint_results.fixes, safe_only=safe_only, rule_filter=rule_filter
				)
				print_fix_dry_run(lint_results.fixes, file_path, safe_only, rule_filter)
			else:
				# Apply fixes
				fix_result = fix_engine.apply_fixes(
					lint_results.fixes, safe_only=safe_only, rule_filter=rule_filter
				)
				apply_and_report_fixes(fix_result, json_data, file_path)

		# Create timing record if profiling
		if file_timer:
			total_duration = file_timer.stop()
			file_timings = FileTimings(
				file_path=str(file_path), total_duration_ms=total_duration, file_read_ms=file_read_ms,
				json_flatten_ms=flatten_ms, model_build_ms=model_build_ms,
				rule_execution_ms=rule_exec_ms, rule_timings=lint_results.rule_timings
			)

		return file_warnings, file_errors, file_timings, lint_results

	return 0, 0, None, None


def format_rule_violations_for_file(rule_name: str, violations: list, custom_formatted_output: str = None) -> str:
	"""
	Format violations for a rule for file output, using custom formatting if available.

	Args:
		rule_name: Name of the rule
		violations: List of violation strings
		custom_formatted_output: Pre-captured custom formatted output from LintResults

	Returns:
		Formatted string for file output
	"""
	if not violations and not custom_formatted_output:
		return ""

	lines = []
	lines.append(f"  {rule_name}:")

	# Show regular violations first (e.g., indentation errors, data quality issues)
	# Filter out empty placeholders (used for counting only)
	if violations:
		for violation in violations:
			if violation.strip():  # Only show non-empty violations
				lines.append(f"    • {violation}")

	# Then show custom formatted output (e.g., category-grouped pylint violations)
	if custom_formatted_output:
		lines.append(custom_formatted_output)

	lines.append("")  # Extra blank line between rules
	lines.append("")

	return '\n'.join(lines)


def write_results_file(
	output_path: Path, results: List[Dict], total_warnings: int, total_errors: int, processed_files: int,
	files_with_issues: int, finalize_results=None, whitelisted_files: List[Path] = None, lint_engine=None
):
	"""Write linting results to an output file with detailed warnings and errors."""
	# Ensure parent directory exists
	output_path.parent.mkdir(parents=True, exist_ok=True)

	# Get rule instances for custom formatting
	rule_instances = {}
	if lint_engine:
		for rule in lint_engine.rules:
			rule_instances[rule.__class__.__name__] = rule

	with open(output_path, 'w', encoding='utf-8') as f:
		f.write("=" * LINE_WIDTH + "\n")
		f.write("IGNITION-LINT RESULTS\n")
		f.write("=" * LINE_WIDTH + "\n\n")

		# Summary
		f.write("SUMMARY\n")
		f.write("-" * LINE_WIDTH + "\n")
		f.write(f"Files processed: {processed_files}\n")
		f.write(f"Total warnings:  {total_warnings}\n")
		f.write(f"Total errors:    {total_errors}\n")
		f.write(f"Files with issues: {files_with_issues}\n")
		f.write(f"Clean files:     {processed_files - files_with_issues}\n")
		if whitelisted_files:
			f.write(f"Files whitelisted: {len(whitelisted_files)}\n")
		f.write("\n")

		# Whitelisted files section
		if whitelisted_files:
			f.write("WHITELISTED FILES (SKIPPED)\n")
			f.write("-" * LINE_WIDTH + "\n")
			f.write(f"The following {len(whitelisted_files)} file(s) were skipped due to whitelist:\n\n")
			for file_path in whitelisted_files:
				f.write(f"  🔒 {file_path}\n")
			f.write("\n")

		# Per-file results
		f.write("PER-FILE RESULTS\n")
		f.write("=" * LINE_WIDTH + "\n\n")

		for result in results:
			# Determine status icon
			if result['errors'] > 0:
				status_icon = "❌"
			elif result['warnings'] > 0:
				status_icon = "⚠️"
			else:
				status_icon = "✅"

			# Separator line before filename for clear blocks
			f.write("-" * LINE_WIDTH + "\n")
			f.write(f"{status_icon} {result['file']}\n")
			f.write("-" * LINE_WIDTH + "\n")

			lint_results = result.get('lint_results')
			if lint_results:
				# Get custom formatted outputs if available
				custom_formatted_warnings = lint_results.custom_formatted_warnings if hasattr(
					lint_results, 'custom_formatted_warnings'
				) else {}
				custom_formatted_errors = lint_results.custom_formatted_errors if hasattr(
					lint_results, 'custom_formatted_errors'
				) else {}

				# Write errors first (more critical)
				if lint_results.errors:
					f.write(f"\nERRORS ({result['errors']} total):\n\n")
					for rule_name, error_list in lint_results.errors.items():
						if error_list:
							custom_output = custom_formatted_errors.get(rule_name)
							formatted = format_rule_violations_for_file(
								rule_name, error_list,
								custom_formatted_output=custom_output
							)
							f.write(formatted)

				# Write warnings second
				if lint_results.warnings:
					f.write(f"\nWARNINGS ({result['warnings']} total):\n\n")
					for rule_name, warning_list in lint_results.warnings.items():
						if warning_list:
							custom_output = custom_formatted_warnings.get(rule_name)
							formatted = format_rule_violations_for_file(
								rule_name, warning_list,
								custom_formatted_output=custom_output
							)
							f.write(formatted)
			else:
				# Fallback to just counts if lint_results not available
				if result['warnings'] > 0:
					f.write(f"  ⚠️  Warnings: {result['warnings']}\n")
				if result['errors'] > 0:
					f.write(f"  ❌ Errors:   {result['errors']}\n")

			f.write("\n")

		# Batch finalization results (if any)
		if finalize_results and (finalize_results.warnings or finalize_results.errors):
			f.write("=" * LINE_WIDTH + "\n")
			f.write("📦 BATCH RULE FINALIZATION RESULTS\n")
			f.write("=" * LINE_WIDTH + "\n\n")

			# Get custom formatted outputs if available
			finalize_custom_formatted_warnings = finalize_results.custom_formatted_warnings if hasattr(
				finalize_results, 'custom_formatted_warnings'
			) else {}
			finalize_custom_formatted_errors = finalize_results.custom_formatted_errors if hasattr(
				finalize_results, 'custom_formatted_errors'
			) else {}

			# Write finalization errors first (more critical)
			if finalize_results.errors:
				error_count = sum(len(e) for e in finalize_results.errors.values())
				f.write(f"\nERRORS ({error_count} total):\n\n")
				for rule_name, error_list in finalize_results.errors.items():
					if error_list:
						custom_output = finalize_custom_formatted_errors.get(rule_name)
						formatted = format_rule_violations_for_file(
							rule_name, error_list, custom_formatted_output=custom_output
						)
						f.write(formatted)

			# Write finalization warnings second
			if finalize_results.warnings:
				warning_count = sum(len(w) for w in finalize_results.warnings.values())
				f.write(f"\nWARNINGS ({warning_count} total):\n\n")
				for rule_name, warning_list in finalize_results.warnings.items():
					if warning_list:
						custom_output = finalize_custom_formatted_warnings.get(rule_name)
						formatted = format_rule_violations_for_file(
							rule_name, warning_list, custom_formatted_output=custom_output
						)
						f.write(formatted)

		f.write("=" * LINE_WIDTH + "\n")
		f.write("END OF RESULTS\n")
		f.write("=" * LINE_WIDTH + "\n")


def aggregate_batch_results(results_path: Path) -> Optional[Dict[str, int]]:
	"""
	Aggregate results from multiple batch files into a summary file.

	When ignition-lint runs in batches (e.g., via pre-commit), multiple result files
	are created. This function aggregates them into a single summary for easy review.

	Returns:
		Dictionary with aggregated totals if multiple batches exist, None otherwise.
		Keys: 'files', 'warnings', 'errors', 'issues', 'clean'
	"""
	import re
	from datetime import datetime

	# Find base name and directory
	parent_dir = results_path.parent
	if '_pid' in results_path.name:
		base_name = results_path.stem.split('_pid')[0]
	else:
		base_name = results_path.stem

	# Only aggregate when this invocation produced a batch file (has _pid and _batch).
	# A non-batch path means this is a standalone or first-batch run; its own totals
	# are already correct and the caller no longer overrides them from the summary.
	is_batch_file = '_pid' in results_path.name and '_batch' in results_path.name
	if not is_batch_file:
		return None

	# Find all related files to aggregate (base file + batch files)
	result_files = []

	# Check if base file exists (e.g., results.txt from first batch)
	base_file = parent_dir / f"{base_name}.txt"
	if base_file.exists():
		result_files.append(base_file)

	# Find all batch files (e.g., results_pid*_batch*.txt)
	pattern = f"{base_name}_pid*.txt"
	batch_files = [f for f in parent_dir.glob(pattern) if 'AGGREGATED_SUMMARY' not in f.name]
	result_files.extend(batch_files)

	# Sort for consistent ordering
	result_files = sorted(result_files)

	if len(result_files) <= 1:
		# Only one file, no need to aggregate
		return None

	# Parse each result file and collect totals
	total_files = 0
	total_warnings = 0
	total_errors = 0
	total_issues = 0
	total_clean = 0
	batch_details = []

	for file_path in result_files:
		try:
			with open(file_path, 'r', encoding='utf-8') as f:
				content = f.read()

				# Extract metrics using regex
				files_match = re.search(r'Files processed:\s+(\d+)', content)
				warnings_match = re.search(r'Total warnings:\s+(\d+)', content)
				errors_match = re.search(r'Total errors:\s+(\d+)', content)
				issues_match = re.search(r'Files with issues:\s+(\d+)', content)
				clean_match = re.search(r'Clean files:\s+(\d+)', content)

				if files_match:
					files = int(files_match.group(1))
					warnings = int(warnings_match.group(1)) if warnings_match else 0
					errors = int(errors_match.group(1)) if errors_match else 0
					issues = int(issues_match.group(1)) if issues_match else 0
					clean = int(clean_match.group(1)) if clean_match else 0

					total_files += files
					total_warnings += warnings
					total_errors += errors
					total_issues += issues
					total_clean += clean

					batch_details.append({
						'filename': file_path.name,
						'files': files,
						'warnings': warnings,
						'errors': errors,
						'issues': issues,
						'clean': clean
					})
		except (OSError, IOError) as e:
			print(f"⚠️  Warning: Could not read {file_path.name}: {e}")
			continue

	# Write aggregated summary
	if batch_details:
		summary_path = parent_dir / f"{base_name}_AGGREGATED_SUMMARY.txt"
		try:
			with open(summary_path, 'w', encoding='utf-8') as f:
				f.write("=" * 80 + "\n")
				f.write("AGGREGATED IGNITION-LINT RESULTS SUMMARY\n")
				f.write("=" * 80 + "\n")
				f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
				f.write(f"Total batches: {len(batch_details)}\n")
				f.write("\n")

				# Overall summary
				f.write("TOTAL SUMMARY ACROSS ALL BATCHES\n")
				f.write("-" * 80 + "\n")
				f.write(f"Files processed:      {total_files}\n")
				f.write(f"Total warnings:       {total_warnings:,}\n")
				f.write(f"Total errors:         {total_errors:,}\n")
				f.write(f"Files with issues:    {total_issues}\n")
				f.write(f"Clean files:          {total_clean}\n")
				f.write("\n")

				# Breakdown by batch
				f.write("BREAKDOWN BY BATCH\n")
				f.write("-" * 80 + "\n")
				for batch in batch_details:
					f.write(
						f"{batch['filename']:<45} "
						f"Files: {batch['files']:>3}  "
						f"Warnings: {batch['warnings']:>4}  "
						f"Errors: {batch['errors']:>4}  "
						f"Issues: {batch['issues']:>3}  "
						f"Clean: {batch['clean']:>3}\n"
					)

				f.write("\n")
				f.write("=" * 80 + "\n")
				f.write("END OF AGGREGATED SUMMARY\n")
				f.write("=" * 80 + "\n")

			print(f"\n📊 Aggregated summary written to: {summary_path}")

			# Return aggregated totals for final summary display
			return {
				'files': total_files,
				'warnings': total_warnings,
				'errors': total_errors,
				'issues': total_issues,
				'clean': total_clean
			}
		except (OSError, IOError) as e:
			print(f"⚠️  Warning: Could not write aggregated summary: {e}")

	return None


def print_fix_dry_run(fixes, file_path, safe_only, rule_filter):
	"""Show proposed fixes without applying them."""
	print(f"\n{'=' * LINE_WIDTH}")
	print(f"Proposed Fixes for {file_path}:")
	print(f"{'=' * LINE_WIDTH}")

	safe_count = 0
	unsafe_count = 0
	filtered_count = 0

	for i, fix in enumerate(fixes, 1):
		# Check rule filter
		if rule_filter and fix.rule_name not in rule_filter:
			filtered_count += 1
			continue

		if fix.is_safe:
			safe_count += 1
			safety_label = "SAFE"
		else:
			unsafe_count += 1
			safety_label = f"UNSAFE - {fix.safety_notes}" if fix.safety_notes else "UNSAFE"

		print(f"\n  Fix {i} ({fix.rule_name}) [{safety_label}]:")
		print(f"    {fix.description}")
		print(f"    Operations:")
		for op in fix.operations:
			if op.operation == FixOperationType.SET_VALUE:
				print(f"      SET {op.format_path()}: '{op.old_value}' -> '{op.new_value}'")
			elif op.operation == FixOperationType.STRING_REPLACE:
				print(f"      REPLACE in {op.format_path()}:")
				print(f"              '{op.old_substring}' -> '{op.new_substring}'")

	total = safe_count + unsafe_count
	print(f"\nSummary: {total} fixes ({safe_count} safe, {unsafe_count} unsafe)")
	if filtered_count:
		print(f"  Filtered out: {filtered_count} (not in --fix-rules)")
	if safe_only and unsafe_count > 0:
		print(f"  --fix would apply: {safe_count} safe fix(es)")
		print(f"  --fix --fix-unsafe would apply: {total} fix(es)")
	else:
		print(f"  Would apply: {total} fix(es)")


def apply_and_report_fixes(fix_result, json_data, file_path):
	"""Apply fixes and report results, writing modified JSON back to file."""
	if fix_result.applied_count > 0:
		print(f"\nApplying fixes to {file_path}:")
		for applied_fix in fix_result.applied:
			print(f"  Applied: {applied_fix.fix.description}")

		# Write modified JSON back to file
		write_json_file(file_path, json_data)
		print(f"  File updated: {file_path}")

	if fix_result.skipped_count > 0:
		for skipped_fix in fix_result.skipped:
			print(f"  Skipped: {skipped_fix.fix.description} ({skipped_fix.skip_reason})")

	print(f"\nApplied: {fix_result.applied_count} fix(es) | "
		f"Skipped: {fix_result.skipped_count} fix(es)")


def print_final_summary(
	processed_files: int, total_warnings: int, total_errors: int, files_with_issues: int, stats_only: bool,
	ignore_warnings: bool = False
):
	"""Print the final summary of the linting process."""
	print("\n📈 Summary:")
	print(f"  Files processed: {processed_files}")

	if not stats_only:
		total_issues = total_warnings + total_errors
		if total_issues == 0:
			print("  ✅ No style inconsistencies found!")
			sys.exit(0)
		else:
			if total_warnings > 0:
				print(f"  ⚠️  Total warnings: {total_warnings}")
			if total_errors > 0:
				print(f"  ❌ Total errors: {total_errors}")
			print(f"  📁 Files with issues: {files_with_issues}")
			print(f"  📁 Clean files: {processed_files - files_with_issues}")

			# Exit with appropriate code based on ignore-warnings mode
			if ignore_warnings and total_errors == 0:
				print("  ✅ No errors found (ignoring warnings)")
				sys.exit(0)
			elif total_errors > 0:
				sys.exit(1)
			else:
				# Has warnings but no errors, and not ignoring warnings
				sys.exit(1)
	else:
		print("  📊 Statistics analysis complete")
		sys.exit(0)


def main():
	"""Main function to lint Ignition view.json files for style inconsistencies."""
	parser = argparse.ArgumentParser(description="Lint Ignition JSON files")
	parser.add_argument(
		"--version",
		action="version",
		version=f"%(prog)s {get_version()}",
	)
	parser.add_argument(
		"--config",
		default="rule_config.json",
		help="Path to configuration JSON file",
	)
	parser.add_argument(
		"--files",
		default="**/view.json",
		help="Comma-separated list of files or glob patterns to lint",
	)
	parser.add_argument(
		"--verbose",
		"-v",
		action="store_true",
		help="Show detailed statistics and information",
	)
	parser.add_argument(
		"--stats-only",
		action="store_true",
		help="Only show statistics, don't run linting rules",
	)
	parser.add_argument(
		"--debug-nodes",
		nargs="*",
		help="Show detailed info for specific node types (e.g., --debug-nodes tag_binding expression_binding)",
	)
	parser.add_argument(
		"--analyze-rules",
		action="store_true",
		help="Show detailed rule impact analysis",
	)
	parser.add_argument(
		"--debug-output",
		help="Directory to save debug files (flattened JSON, model state, statistics)",
	)
	parser.add_argument(
		"--ignore-warnings",
		action="store_true",
		help="Don't fail on warnings, only on errors (warnings are still displayed)",
	)
	parser.add_argument(
		"filenames",
		nargs="*",
		help="Filenames to check (from pre-commit)",
	)
	parser.add_argument(
		"--timing-output",
		help="File path to write detailed timing/profiling report (e.g., timing.txt)",
	)
	parser.add_argument(
		"--results-output",
		help="File path to write linting results (e.g., results.txt)",
	)
	parser.add_argument(
		"--whitelist",
		default=None,
		help="Path to whitelist file containing files to ignore (e.g., .whitelist.txt)",
	)
	parser.add_argument(
		"--no-whitelist",
		action="store_true",
		help="Disable whitelist even if --whitelist is specified (overrides --whitelist)",
	)
	parser.add_argument(
		"--generate-whitelist",
		nargs="+",
		metavar="PATTERN",
		help="Generate whitelist from glob patterns (e.g., 'views/legacy/**/*.json')",
	)
	parser.add_argument(
		"--whitelist-output",
		default=".whitelist.txt",
		help="Output file for generated whitelist (default: .whitelist.txt)",
	)
	parser.add_argument(
		"--append",
		action="store_true",
		help="Append to existing whitelist instead of overwriting (use with --generate-whitelist)",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Show what would be added to whitelist without writing file (use with --generate-whitelist)",
	)
	parser.add_argument(
		"--fix",
		action="store_true",
		help="Apply safe auto-fixes to view.json files",
	)
	parser.add_argument(
		"--fix-unsafe",
		action="store_true",
		help="Also apply fixes that update references (use with --fix)",
	)
	parser.add_argument(
		"--fix-dry-run",
		action="store_true",
		help="Show what fixes would be applied without modifying files",
	)
	parser.add_argument(
		"--fix-rules",
		default=None,
		help="Comma-separated list of rules to apply fixes from (default: all fixable rules)",
	)
	args = parser.parse_args()

	# Handle whitelist generation mode
	if args.generate_whitelist:
		generate_whitelist(
			patterns=args.generate_whitelist, output_file=args.whitelist_output, append=args.append,
			dry_run=args.dry_run
		)
		sys.exit(0)  # Exit after generating whitelist

	# Clean up old batch files from previous runs (prevents unbounded growth)
	if args.results_output:
		cleanup_old_batch_files(Path(args.results_output))
	if args.timing_output:
		cleanup_old_batch_files(Path(args.timing_output))

	# Clean up old debug files from previous runs
	cleanup_debug_files()

	# Load whitelist if specified and not disabled
	whitelist = set()
	if args.whitelist and not args.no_whitelist:
		whitelist = load_whitelist(args.whitelist)
		if whitelist and args.verbose:
			print(f"🔒 Loaded whitelist with {len(whitelist)} files")
		elif not whitelist and args.verbose:
			print(f"⚠️  Whitelist file specified but empty or not found: {args.whitelist}")
	elif args.no_whitelist and args.verbose:
		print("ℹ️  Whitelist disabled via --no-whitelist")

	# Set up the linting engine
	lint_engine = setup_linter(args)

	# Collect files to process (excludes whitelisted files)
	file_paths, whitelisted_files = collect_files(args, whitelist)
	if not file_paths:
		print("❌ No files specified or found")
		sys.exit(0)

	if args.verbose:
		print(f"📁 Processing {len(file_paths)} files")

	# Initialize timing collector if timing output is requested
	timing_collector = TimingCollector() if args.timing_output else None
	performance_timer = PerformanceTimer() if args.timing_output else None

	if timing_collector:
		timing_collector.start_total_timing()
		print(f"🔍 Performance profiling enabled (output: {args.timing_output})")

	# Process each file
	total_warnings = 0
	total_errors = 0
	files_with_issues = 0
	processed_files = 0
	results_buffer = []  # Collect results for file output

	for file_path in file_paths:
		file_warnings, file_errors, file_timings, lint_results = process_single_file(
			file_path, lint_engine, args, performance_timer
		)

		# Track timing if enabled
		if timing_collector and file_timings:
			timing_collector.add_file_timing(file_timings)

		# Collect results for output file if specified
		if args.results_output and not args.stats_only:
			results_buffer.append({
				'file': str(file_path),
				'warnings': file_warnings,
				'errors': file_errors,
				'lint_results': lint_results  # Include detailed messages
			})

		# All functions now return tuples, no need to check for -1
		processed_files += 1
		total_warnings += file_warnings
		total_errors += file_errors
		if file_warnings > 0 or file_errors > 0:
			files_with_issues += 1

	# Finalize batch rules (e.g., PylintScriptRule in batch mode)
	# NOTE: In non-batch mode (default), rules process per-file and finalize() returns empty results
	# This section only produces output for rules running in batch mode (processing all files together)
	finalize_results = None
	if not args.stats_only:
		finalize_results = lint_engine.finalize_batch_rules(enable_timing=bool(performance_timer))

		# Process finalization results (only non-empty when rules run in batch mode)
		if finalize_results.warnings or finalize_results.errors:
			finalize_warning_count = sum(len(w) for w in finalize_results.warnings.values())
			finalize_error_count = sum(len(e) for e in finalize_results.errors.values())

			# If only one file was processed, show batch results in standard format
			# (File path already shown in file header)
			if len(file_paths) == 1:
				# Print warnings
				if finalize_warning_count > 0:
					print(f"\n⚠️ Found {finalize_warning_count} warnings:")
					for rule_name, warning_list in finalize_results.warnings.items():
						if warning_list:
							print(f"  📋 {rule_name} (warning):")
							for warning in warning_list:
								print(f"    • {warning}")
								total_warnings += 1

				# Print errors
				if finalize_error_count > 0:
					print(f"\n❌ Found {finalize_error_count} errors:")
					for rule_name, error_list in finalize_results.errors.items():
						if error_list:
							print(f"  📋 {rule_name} (error):")
							for error in error_list:
								print(f"    • {error}")
								total_errors += 1
			else:
				# Multiple files: show batch results in separate section
				print("\n" + "=" * 80)
				print("📦 Batch Rule Results (All Files)")
				print("=" * 80)

				# Print warnings and errors
				for rule_name, warning_list in finalize_results.warnings.items():
					for warning in warning_list:
						print(f"⚠️ {rule_name}: {warning}")
						total_warnings += 1

				for rule_name, error_list in finalize_results.errors.items():
					for error in error_list:
						print(f"❌ {rule_name}: {error}")
						total_errors += 1

			# Update files_with_issues count if finalization found issues
			if finalize_results.has_errors or finalize_results.warnings:
				files_with_issues = max(files_with_issues, 1)  # At least one file had issues

	# Stop timing if enabled
	if timing_collector:
		timing_collector.stop_total_timing()

	# Write timing report if requested
	if args.timing_output and timing_collector:
		timing_path = make_unique_output_path(Path(args.timing_output))
		timing_collector.write_timing_report(timing_path)

		print("\n" + f"📊 Timing report written to: {timing_path}")

	# Write results file if requested
	if args.results_output and results_buffer:
		results_path = make_unique_output_path(Path(args.results_output))
		write_results_file(
			results_path, results_buffer, total_warnings, total_errors, processed_files, files_with_issues,
			finalize_results, whitelisted_files, lint_engine
		)
		print("\n" + f"📝 Results written to: {results_path}")

		# Write _AGGREGATED_SUMMARY.txt across batch files (CI/disk artifact only).
		# Each invocation prints its own honest totals; we no longer override the
		# terminal summary with aggregated values, since pre-commit runs N separate
		# processes and the escalating per-batch overrides were confusing.
		aggregate_batch_results(results_path)

	# Print final summary
	print_final_summary(
		processed_files, total_warnings, total_errors, files_with_issues, args.stats_only, args.ignore_warnings
	)


if __name__ == "__main__":
	main()
