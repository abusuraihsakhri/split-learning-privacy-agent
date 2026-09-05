"""
Shared test fixtures and configuration for Split Learning Privacy Agent tests.
"""
import os
import pytest


def pytest_configure(config):
    """Set test environment variables before test collection."""
    # Set a deterministic test key for HMAC audit trail
    os.environ.setdefault("AUDIT_SECRET_KEY", "test-secret-key-for-unit-tests-only")


@pytest.fixture(autouse=True)
def reset_audit_singleton():
    """Reset the global audit trail singleton between tests for isolation."""
    import agents.base as base
    old_instance = base._AUDIT_INSTANCE
    base._AUDIT_INSTANCE = None
    yield
    base._AUDIT_INSTANCE = old_instance
