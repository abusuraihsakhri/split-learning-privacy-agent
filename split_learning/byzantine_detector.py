"""
Byzantine-Resilient Split Learning: Detect and reject poisoned gradients at the cut layer.
Domain: Privacy-Preserving Federated Healthcare & FHE
Standard: HIPAA Safe Harbor / Google SecAgg Standards
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    GRADIENT_NORM = "gradient_norm"
    GRADIENT_DIRECTION = "gradient_direction"
    ACTIVATION_DISTRIBUTION = "activation_distribution"
    SIGN_FLIPPING = "sign_flipping"


@dataclass
class AnomalyEvent:
    """Record of a detected anomaly."""
    client_id: str
    anomaly_type: AnomalyType
    severity: float
    details: Dict[str, Any]
    epoch: int


@dataclass
class ClientTrustRecord:
    """Trust tracking for a split learning client."""
    client_id: str
    trust_score: float = 1.0
    anomaly_history: List[AnomalyEvent] = field(default_factory=list)
    gradient_norms: List[float] = field(default_factory=list)

    def update_trust(self, is_anomalous: bool, severity: float = 0.1):
        if is_anomalous:
            self.trust_score = max(0.0, self.trust_score - severity)
        else:
            self.trust_score = min(1.0, self.trust_score + 0.02)


class GradientValidator:
    """Validate gradients at the cut layer for Byzantine resilience."""

    def __init__(self, norm_threshold_multiplier: float = 3.0, direction_threshold: float = 0.3):
        self.norm_threshold_multiplier = norm_threshold_multiplier
        self.direction_threshold = direction_threshold
        self.client_records: Dict[str, ClientTrustRecord] = {}

    def get_record(self, client_id: str) -> ClientTrustRecord:
        if client_id not in self.client_records:
            self.client_records[client_id] = ClientTrustRecord(client_id=client_id)
        return self.client_records[client_id]

    def validate_gradient_norm(
        self, client_id: str, gradient: np.ndarray, epoch: int
    ) -> Optional[AnomalyEvent]:
        """Flag gradients with norm > threshold_multiplier * median norm."""
        record = self.get_record(client_id)
        norm = float(np.linalg.norm(gradient))
        record.gradient_norms.append(norm)

        if len(record.gradient_norms) < 3:
            return None

        median_norm = np.median(record.gradient_norms)
        if median_norm > 0 and norm > self.norm_threshold_multiplier * median_norm:
            event = AnomalyEvent(
                client_id=client_id,
                anomaly_type=AnomalyType.GRADIENT_NORM,
                severity=norm / median_norm,
                details={"norm": norm, "median_norm": float(median_norm)},
                epoch=epoch,
            )
            record.anomaly_history.append(event)
            record.update_trust(True, severity=0.15)
            logger.warning(
                f"Client {client_id}: gradient norm {norm:.4f} exceeds "
                f"{self.norm_threshold_multiplier}x median {median_norm:.4f}"
            )
            return event
        record.update_trust(False)
        return None

    def validate_gradient_direction(
        self,
        client_id: str,
        gradient: np.ndarray,
        reference_gradient: np.ndarray,
        epoch: int,
    ) -> Optional[AnomalyEvent]:
        """Detect gradient sign flipping attacks."""
        record = self.get_record(client_id)
        norm_g = np.linalg.norm(gradient)
        norm_ref = np.linalg.norm(reference_gradient)
        if norm_g == 0 or norm_ref == 0:
            return None
        cosine_sim = float(np.dot(gradient.flatten(), reference_gradient.flatten()) / (norm_g * norm_ref))

        if cosine_sim < -self.direction_threshold:
            event = AnomalyEvent(
                client_id=client_id,
                anomaly_type=AnomalyType.SIGN_FLIPPING,
                severity=abs(cosine_sim),
                details={"cosine_similarity": cosine_sim},
                epoch=epoch,
            )
            record.anomaly_history.append(event)
            record.update_trust(True, severity=0.2)
            logger.warning(
                f"Client {client_id}: sign-flipping detected "
                f"(cosine_sim={cosine_sim:.4f})"
            )
            return event
        return None

    def validate_activation_distribution(
        self,
        client_id: str,
        activations: np.ndarray,
        expected_mean: float = 0.0,
        expected_std: float = 1.0,
        epoch: int = 0,
    ) -> Optional[AnomalyEvent]:
        """Monitor activation distribution for statistical anomalies."""
        record = self.get_record(client_id)
        act_mean = float(np.mean(activations))
        act_std = float(np.std(activations))

        mean_deviation = abs(act_mean - expected_mean) / max(expected_std, 1e-6)
        std_ratio = act_std / max(expected_std, 1e-6)

        if mean_deviation > 3.0 or std_ratio > 5.0 or std_ratio < 0.1:
            event = AnomalyEvent(
                client_id=client_id,
                anomaly_type=AnomalyType.ACTIVATION_DISTRIBUTION,
                severity=mean_deviation,
                details={
                    "act_mean": act_mean,
                    "act_std": act_std,
                    "mean_deviation": mean_deviation,
                    "std_ratio": std_ratio,
                },
                epoch=epoch,
            )
            record.anomaly_history.append(event)
            record.update_trust(True, severity=0.1)
            return event
        return None


class RobustAggregator:
    """Robust aggregation methods for multi-client split learning."""

    @staticmethod
    def coordinate_wise_median(gradients: List[np.ndarray]) -> np.ndarray:
        """Compute element-wise median of gradient vectors."""
        stacked = np.stack(gradients, axis=0)
        return np.median(stacked, axis=0)

    @staticmethod
    def trimmed_mean(
        gradients: List[np.ndarray], trim_fraction: float = 0.1
    ) -> np.ndarray:
        """Sort per-coordinate, trim top/bottom f%, compute mean."""
        n = len(gradients)
        trim_count = max(1, int(n * trim_fraction))
        stacked = np.stack(gradients, axis=0)
        sorted_grads = np.sort(stacked, axis=0)
        trimmed = sorted_grads[trim_count : n - trim_count]
        if len(trimmed) == 0:
            trimmed = sorted_grads
        return np.mean(trimmed, axis=0)

    @staticmethod
    def trust_weighted_average(
        gradients: List[np.ndarray], trust_scores: List[float]
    ) -> np.ndarray:
        """Weighted average using trust scores."""
        total_trust = sum(trust_scores)
        if total_trust == 0:
            return np.mean(gradients, axis=0)
        result = np.zeros_like(gradients[0])
        for grad, trust in zip(gradients, trust_scores):
            result += (trust / total_trust) * grad
        return result
