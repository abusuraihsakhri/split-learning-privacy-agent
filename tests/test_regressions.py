"""Regression coverage for audited correctness and security behavior."""
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.base import AuditTrail, PHIGuard, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import _resolve_safe_path
from split_learning.cli import _resolve_safe_path as _resolve_split_path


def test_hmac_detects_entry_tampering():
    trail = AuditTrail(secret_key="local-test-key")
    trail.log("unit", "test", "event", {"status": "NOMINAL"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "forged"
    assert not trail.verify_integrity()


def test_hmac_detects_changed_signature_and_bad_record():
    trail = AuditTrail(secret_key="local-test-key")
    trail.log("unit", "test", "event", {"status": "NOMINAL"})
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()
    trail.logs[0].pop("timestamp")
    assert not trail.verify_integrity()


def test_trail_is_read_only_snapshot():
    trail = AuditTrail(secret_key="local-test-key")
    trail.log("unit", "test", "event", {"status": "NOMINAL"})
    snapshot = trail.get_trail()
    snapshot[0]["actor"] = "tampered"
    snapshot.clear()
    assert trail.verify_integrity()
    assert len(trail.get_trail()) == 1


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_metrics_rejected(bad):
    with pytest.raises(ValidationError):
        SystemTaskPayload(task_id="t", target_identifier="key", primary_metric=bad)


def test_empty_ids_and_extra_inputs_rejected():
    for kwargs in (
        {"task_id": ""},
        {"target_identifier": ""},
        {"unrecognized": "value"},
    ):
        params = {"task_id": "TASK", "target_identifier": "KEY", "primary_metric": 1}
        params.update(kwargs)
        with pytest.raises(ValidationError):
            SystemTaskPayload(**params)


def test_attributes_are_checked_for_phi():
    task = SystemTaskPayload(
        task_id="TASK", target_identifier="KEY", primary_metric=1,
        attributes={"note": "MRN-123456"}
    )
    with pytest.raises(SecurityException):
        SystemSupervisor().process_task(task)


def test_sibling_directory_path_not_allowed(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "repo-backup").mkdir()
    monkeypatch.chdir(root)
    for resolve in (_resolve_safe_path, _resolve_split_path):
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve("../repo-backup/file.csv")
