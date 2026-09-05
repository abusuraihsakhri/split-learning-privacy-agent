"""
Security and input validation tests for Split Learning Privacy Agent.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cli import _resolve_safe_path
from split_learning.cli import _resolve_safe_path as sl_resolve_safe_path

# Project root directory for creating test files within the working directory
PROJECT_DIR = Path(__file__).parent.parent


class TestPathValidation:
    """Test path traversal prevention in CLI batch commands."""

    def test_valid_relative_path(self):
        """Valid relative paths should resolve correctly."""
        result = _resolve_safe_path("sample.csv", must_exist=True)
        assert result.is_file()
        assert str(result).endswith("sample.csv")

    def test_path_traversal_blocked(self):
        """Paths attempting to escape the working directory should be blocked."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            _resolve_safe_path("../../etc/passwd")

    def test_path_traversal_with_nested_dirs(self):
        """Nested path traversal attempts should be blocked."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            _resolve_safe_path("subdir/../../../etc/shadow")

    def test_nonexistent_input_file_raises(self):
        """Requesting must_exist on a missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _resolve_safe_path("nonexistent_file_xyz.csv", must_exist=True)

    def test_output_path_does_not_require_existence(self):
        """Output paths should not require the file to exist."""
        result = _resolve_safe_path("future_output.csv", must_exist=False)
        assert not result.exists()  # file doesn't exist yet
        assert str(result).endswith("future_output.csv")

    def test_split_learning_path_validation(self):
        """Split learning CLI path validation should also block traversal."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            sl_resolve_safe_path("../../../etc/passwd")


class TestAuditSecretKey:
    """Test that AUDIT_SECRET_KEY is required."""

    def test_audit_trail_requires_key(self, monkeypatch):
        """AuditTrail should raise RuntimeError when no key is available."""
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        # Reset the singleton so it re-evaluates
        import agents.base as base
        old_instance = base._AUDIT_INSTANCE
        base._AUDIT_INSTANCE = None
        try:
            from agents.base import AuditTrail
            with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY"):
                AuditTrail()
        finally:
            base._AUDIT_INSTANCE = old_instance

    def test_audit_trail_accepts_key(self):
        """AuditTrail should accept a provided key."""
        from agents.base import AuditTrail
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        assert trail.secret_key == b"test-key-for-unit-tests"

    def test_audit_trail_accepts_env_key(self, monkeypatch):
        """AuditTrail should use AUDIT_SECRET_KEY from environment."""
        monkeypatch.setenv("AUDIT_SECRET_KEY", "env-based-test-key")
        # Reset singleton
        import agents.base as base
        old_instance = base._AUDIT_INSTANCE
        base._AUDIT_INSTANCE = None
        try:
            from agents.base import AuditTrail
            trail = AuditTrail()
            assert trail.secret_key == b"env-based-test-key"
        finally:
            base._AUDIT_INSTANCE = old_instance


class TestBatchErrorHandling:
    """Test batch processing with invalid data."""

    def test_batch_skips_invalid_metrics(self):
        """Batch should skip rows with non-numeric metric values."""
        import csv
        # Create test files within the project directory (path validation requires this)
        test_dir = Path(__file__).parent / "_test_tmp"
        test_dir.mkdir(exist_ok=True)
        input_csv = test_dir / "test_input.csv"
        output_csv = test_dir / "test_output.csv"

        try:
            with open(input_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'task_id', 'target_identifier', 'primary_metric',
                    'secondary_metric', 'is_critical_flag', 'status_descriptor'
                ])
                writer.writeheader()
                writer.writerow({
                    'task_id': 'GOOD-01', 'target_identifier': 'T1',
                    'primary_metric': '10.0', 'secondary_metric': '5.0',
                    'is_critical_flag': 'False', 'status_descriptor': 'NOMINAL'
                })
                writer.writerow({
                    'task_id': 'BAD-01', 'target_identifier': 'T2',
                    'primary_metric': 'not_a_number', 'secondary_metric': '5.0',
                    'is_critical_flag': 'False', 'status_descriptor': 'NOMINAL'
                })

            from cli import main
            exit_code = main(["batch", "-i", str(input_csv), "-o", str(output_csv)])
            assert exit_code == 0

            # Verify output has only the valid row
            with open(output_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['task_id'] == 'GOOD-01'
        finally:
            # Cleanup test files
            if input_csv.exists():
                input_csv.unlink()
            if output_csv.exists():
                output_csv.unlink()
            if test_dir.exists():
                test_dir.rmdir()
