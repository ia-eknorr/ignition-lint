"""
Unit tests for batch result cleanup and aggregation.

Covers the regression where a stale ``results_AGGREGATED_SUMMARY.txt`` from a
previous run polluted a later (passing) run's reported totals.
"""

import os
import sys
import shutil
import tempfile
import time
import unittest
from pathlib import Path

current_dir = Path(__file__).parent
tests_dir = current_dir.parent
project_root = tests_dir.parent
sys.path.insert(0, str(project_root / "src"))

from ignition_lint.cli import aggregate_batch_results, cleanup_old_batch_files


def _set_old_mtime(path: Path, age_seconds: int = 60) -> None:
	"""Backdate a file's mtime so cleanup treats it as stale."""
	old_time = time.time() - age_seconds
	os.utime(path, (old_time, old_time))


class TestCleanupOldBatchFiles(unittest.TestCase):
	"""Tests for cleanup_old_batch_files()."""

	def setUp(self):
		self.temp_dir = tempfile.mkdtemp()
		self.temp_path = Path(self.temp_dir)
		self.results_path = self.temp_path / "results.txt"

	def tearDown(self):
		shutil.rmtree(self.temp_dir, ignore_errors=True)

	def test_stale_aggregated_summary_is_deleted(self):
		"""Stale _AGGREGATED_SUMMARY.txt from a previous run is removed."""
		summary = self.temp_path / "results_AGGREGATED_SUMMARY.txt"
		summary.write_text("Total errors:         99\n")
		_set_old_mtime(summary)

		cleanup_old_batch_files(self.results_path)

		self.assertFalse(
			summary.exists(),
			"Stale aggregated summary should have been deleted",
		)

	def test_fresh_aggregated_summary_is_preserved(self):
		"""Recent summary (< 5s) is kept to protect parallel processes."""
		summary = self.temp_path / "results_AGGREGATED_SUMMARY.txt"
		summary.write_text("Total errors:         5\n")
		# Leave mtime at "now" — fresh file.

		cleanup_old_batch_files(self.results_path)

		self.assertTrue(
			summary.exists(),
			"Fresh aggregated summary must not be deleted (parallel-process safety)",
		)

	def test_stale_base_results_file_is_deleted(self):
		"""Stale results.txt from previous run is removed."""
		self.results_path.write_text("Total errors: 99\n")
		_set_old_mtime(self.results_path)

		cleanup_old_batch_files(self.results_path)

		self.assertFalse(self.results_path.exists())

	def test_stale_batch_files_from_other_pid_are_deleted(self):
		"""Old batch files from a different PID are cleaned up."""
		other_pid = os.getpid() + 1  # any PID that isn't ours
		stale_batch = self.temp_path / f"results_pid{other_pid}_batch1.txt"
		stale_batch.write_text("Total errors: 1\n")
		_set_old_mtime(stale_batch)

		cleanup_old_batch_files(self.results_path)

		self.assertFalse(stale_batch.exists())

	def test_current_pid_batch_files_are_preserved(self):
		"""Batch files from the current PID are never deleted."""
		current_pid = os.getpid()
		own_batch = self.temp_path / f"results_pid{current_pid}_batch1.txt"
		own_batch.write_text("Total errors: 1\n")
		_set_old_mtime(own_batch)  # even if mtime is old, same-PID is kept

		cleanup_old_batch_files(self.results_path)

		self.assertTrue(own_batch.exists())

	def test_missing_directory_is_noop(self):
		"""Cleanup on a non-existent parent directory does not raise."""
		missing = self.temp_path / "does_not_exist" / "results.txt"
		# Should simply return without raising.
		cleanup_old_batch_files(missing)


class TestAggregateBatchResults(unittest.TestCase):
	"""Tests for aggregate_batch_results()."""

	def setUp(self):
		self.temp_dir = tempfile.mkdtemp()
		self.temp_path = Path(self.temp_dir)

	def tearDown(self):
		shutil.rmtree(self.temp_dir, ignore_errors=True)

	def test_non_batch_path_does_not_read_stale_summary(self):
		"""
		Regression: a stale summary must not feed totals back to a single-file
		run. Previously, calling with results.txt would read an existing
		AGGREGATED_SUMMARY and return its (stale) numbers.
		"""
		stale_summary = self.temp_path / "results_AGGREGATED_SUMMARY.txt"
		stale_summary.write_text(
			"Files processed:      10\n"
			"Total warnings:       50\n"
			"Total errors:         99\n"
			"Files with issues:    8\n"
			"Clean files:          2\n"
		)

		results_path = self.temp_path / "results.txt"
		results_path.write_text("placeholder\n")

		self.assertIsNone(
			aggregate_batch_results(results_path),
			"Non-batch path must return None even when a stale summary exists",
		)

	def test_batch_path_aggregates_existing_files(self):
		"""When given a batch path with sibling result files, totals are summed."""
		base = self.temp_path / "results.txt"
		base.write_text(
			"Files processed:      3\n"
			"Total warnings:       4\n"
			"Total errors:         1\n"
			"Files with issues:    2\n"
			"Clean files:          1\n"
		)
		batch1 = self.temp_path / f"results_pid{os.getpid()}_batch1.txt"
		batch1.write_text(
			"Files processed:      2\n"
			"Total warnings:       1\n"
			"Total errors:         3\n"
			"Files with issues:    1\n"
			"Clean files:          1\n"
		)

		totals = aggregate_batch_results(batch1)

		self.assertIsNotNone(totals, "Batch path with multiple files should aggregate")
		self.assertEqual(totals['files'], 5)
		self.assertEqual(totals['warnings'], 5)
		self.assertEqual(totals['errors'], 4)
		self.assertEqual(totals['issues'], 3)
		self.assertEqual(totals['clean'], 2)

		summary = self.temp_path / "results_AGGREGATED_SUMMARY.txt"
		self.assertTrue(summary.exists(), "Aggregated summary file should be written")


if __name__ == "__main__":
	unittest.main()
