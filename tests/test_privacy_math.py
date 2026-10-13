"""Numerical and privacy-regression tests."""
import numpy as np
import pytest

from split_learning.secure_aggregation import ShamirSecretSharing, SecureActivationAggregator
from split_learning.privacy_budget import BudgetConfig, CompositionMethod, PrivacyBudgetTracker


def test_shamir_exact_round_trip_signed():
    sss = ShamirSecretSharing()
    vec = np.array([0, 1, -1, 2**40, -(2**40)], dtype=np.int64)
    shares = sss.split_vector(vec, num_shares=5, threshold=3)
    actual = sss.reconstruct_vector([(i + 1, shares[i]) for i in [0, 2, 4]])
    np.testing.assert_array_equal(actual, vec)


def test_shamir_rejects_invalid_configuration():
    sss = ShamirSecretSharing()
    with pytest.raises(ValueError):
        sss.split_vector(np.array([1]), num_shares=2, threshold=3)
    with pytest.raises(TypeError):
        sss.split_vector(np.array([1.3]), num_shares=3, threshold=2)
    with pytest.raises(ValueError):
        sss.reconstruct_vector([(1, np.array([1])), (1, np.array([2]))])


def test_secure_aggregator_averages_signed_vectors():
    agg = SecureActivationAggregator()
    xs = [np.array([-8, 6, 2], dtype=np.int64), np.array([4, 10, -6], dtype=np.int64)]
    shares = [agg.generate_shares(f"client{i}", x, 3) for i, x in enumerate(xs)]
    np.testing.assert_allclose(agg.aggregate_shares(shares, num_participants=3), [-2, 8, -2])


def test_budget_handles_varying_step_epsilons():
    tracker = PrivacyBudgetTracker(BudgetConfig(total_epsilon=10, composition_method=CompositionMethod.BASIC))
    for epoch, clip in enumerate([1.0, 2.0, 0.5], start=1):
        tracker.consume_budget(epoch, "layer", noise_scale=2, clipping_norm=clip, num_samples=32)
    assert tracker.cumulative_epsilon == pytest.approx(1.75)
    assert tracker.cumulative_delta == 0
    assert tracker.get_layer_breakdown()["layer"]["fraction_of_total"] == pytest.approx(1.0)


def test_invalid_budget_steps_rejected_and_no_new_events():
    tracker = PrivacyBudgetTracker(BudgetConfig(total_epsilon=0.1))
    with pytest.raises(ValueError):
        tracker.consume_budget(1, "layer", 0, 1, 1)
    assert tracker.get_status()["total_events"] == 0
    first = tracker.consume_budget(1, "layer", 1, 1, 1)
    assert first["halt_training"]
    with pytest.raises(RuntimeError):
        tracker.consume_budget(2, "layer", 1, 1, 1)


def test_rdp_fallback_does_not_underreport_pure_dp():
    tracker = PrivacyBudgetTracker(BudgetConfig(composition_method=CompositionMethod.RDP))
    tracker.consume_budget(1, "layer", 1, 1, 32)
    tracker.consume_budget(2, "layer", 1, 3, 32)
    assert tracker.cumulative_epsilon == pytest.approx(4.0)
