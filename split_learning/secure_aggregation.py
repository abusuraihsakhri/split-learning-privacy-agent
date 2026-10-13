"""
Secure Aggregation for Cut-Layer Activations using Shamir's Secret Sharing.
Protects smashed data at the cut layer during split learning.
Domain: Privacy-Preserving Federated Healthcare & FHE
Standard: HIPAA Safe Harbor / Google SecAgg Standards
"""
import hashlib
import logging
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ActivationShare:
    """A Shamir secret share of a cut-layer activation vector."""
    client_id: str
    share_index: int
    share_values: np.ndarray  # shares of the activation vector
    commitment: List[int]     # Placeholder; no commitment verification is implemented
    timestamp: float = field(default_factory=time.time)


@dataclass
class SecureAggConfig:
    """Configuration for secure aggregation of activations."""
    prime: int = 2**61 - 1
    threshold_fraction: float = 0.5
    padding_enabled: bool = True
    share_refresh_enabled: bool = True


class ShamirSecretSharing:
    """Shamir's Secret Sharing over GF(p) for activation vectors."""

    def __init__(self, prime: int = 2**61 - 1):
        self.prime = prime

    def split_vector(
        self, values: np.ndarray, num_shares: int, threshold: int
    ) -> List[np.ndarray]:
        """Split a vector of values into n shares with threshold t."""
        if not isinstance(num_shares, int) or not isinstance(threshold, int) or not (1 <= threshold <= num_shares < self.prime):
            raise ValueError("Require 1 <= threshold <= num_shares < prime")
        values = np.asarray(values)
        if not np.issubdtype(values.dtype, np.integer):
            raise TypeError("Activations must first be quantized to integer values")
        if values.size == 0:
            raise ValueError("Activation vectors cannot be empty")
        flat = values.flatten().astype(np.int64)
        if np.any(np.abs(flat.astype(object)) > self.prime // 2):
            raise ValueError("Activation magnitude exceeds centered field range")
        all_shares = []
        for _ in range(num_shares):
            all_shares.append(np.zeros(len(flat), dtype=np.int64))

        for idx in range(len(flat)):
            secret = int(flat[idx]) % self.prime
            coefficients = [secret]
            for _ in range(threshold - 1):
                coefficients.append(secrets.randbelow(self.prime))
            for share_idx in range(num_shares):
                x = share_idx + 1
                value = 0
                for power, coeff in enumerate(coefficients):
                    value = (value + coeff * pow(x, power, self.prime)) % self.prime
                all_shares[share_idx][idx] = value

        return [s.reshape(values.shape) for s in all_shares]

    def reconstruct_vector(
        self, shares: List[Tuple[int, np.ndarray]]
    ) -> np.ndarray:
        """Reconstruct vector from shares using Lagrange interpolation."""
        if not shares:
            raise ValueError("No shares provided")
        shape = shares[0][1].shape
        indices = [idx for idx, _ in shares]
        if len(set(indices)) != len(indices) or any(not isinstance(i, int) or i <= 0 or i >= self.prime for i in indices):
            raise ValueError("Share indices must be distinct positive field elements")
        if any(s.shape != shape or not np.issubdtype(s.dtype, np.integer) for _, s in shares):
            raise ValueError("Shares must have matching shapes and integer values")
        flat_shares = [(idx, s.flatten()) for idx, s in shares]
        result = np.zeros(flat_shares[0][1].size, dtype=np.int64)
        weights = []
        for i, (xi, _) in enumerate(flat_shares):
            numerator, denominator = 1, 1
            for j, (xj, _) in enumerate(flat_shares):
                if i != j:
                    numerator = numerator * (-xj) % self.prime
                    denominator = denominator * (xi - xj) % self.prime
            weights.append(numerator * pow(denominator, -1, self.prime) % self.prime)

        # Python integer arithmetic avoids int64 overflow before the modulus.
        for col in range(result.size):
            value = sum(int(share[col]) * weight for (_, share), weight in zip(flat_shares, weights)) % self.prime
            result[col] = value if value <= self.prime // 2 else value - self.prime
        return result.reshape(shape)


class SecureActivationAggregator:
    """Secure aggregation for cut-layer activations in split learning."""

    def __init__(self, config: Optional[SecureAggConfig] = None):
        self.config = config or SecureAggConfig()
        self.sss = ShamirSecretSharing(self.prime)
        self.client_shares: Dict[str, List[ActivationShare]] = {}
        self.max_activation_dim: int = 0

    @property
    def prime(self) -> int:
        return self.config.prime

    def register_client(self, client_id: str, activation_dim: int):
        """Register a client with its activation dimensionality."""
        self.max_activation_dim = max(self.max_activation_dim, activation_dim)
        logger.info(
            f"Client {client_id} registered with dim={activation_dim}, "
            f"max_dim={self.max_activation_dim}"
        )

    def pad_activations(self, activations: np.ndarray) -> np.ndarray:
        """Pad activations to maximum dimension for uniform sharing."""
        if not self.config.padding_enabled:
            return activations
        current_dim = activations.shape[-1]
        if current_dim < self.max_activation_dim:
            pad_width = [(0, 0)] * (len(activations.shape) - 1) + [
                (0, self.max_activation_dim - current_dim)
            ]
            return np.pad(activations, pad_width, mode="constant", constant_values=0)
        return activations

    def generate_shares(
        self,
        client_id: str,
        activations: np.ndarray,
        num_participants: int,
    ) -> List[ActivationShare]:
        """Generate Shamir shares of a client's smashed data."""
        if num_participants < 2:
            raise ValueError("At least two participants are required")
        threshold = max(2, int(num_participants * self.config.threshold_fraction) + 1)
        padded = self.pad_activations(activations)
        share_arrays = self.sss.split_vector(padded, num_participants, threshold)

        shares = []
        for i, share_arr in enumerate(share_arrays):
            share = ActivationShare(
                client_id=client_id,
                share_index=i + 1,
                share_values=share_arr,
                commitment=[],  # simplified
            )
            shares.append(share)

        if client_id not in self.client_shares:
            self.client_shares[client_id] = []
        self.client_shares[client_id] = shares
        return shares

    def aggregate_shares(
        self,
        all_shares: List[List[ActivationShare]],
        num_participants: int,
    ) -> np.ndarray:
        """Aggregate shares from all clients to reconstruct summed activations."""
        if num_participants < 2 or not all_shares:
            raise ValueError("At least two participants and one client share set are required")
        threshold = max(2, int(num_participants * self.config.threshold_fraction) + 1)
        if any(len(client) < threshold for client in all_shares):
            raise ValueError("Insufficient shares for reconstruction")
        shape = all_shares[0][0].share_values.shape
        combined = []
        for position in range(threshold):
            index = all_shares[0][position].share_index
            parts = [client[position] for client in all_shares]
            if any(share.share_index != index or share.share_values.shape != shape for share in parts):
                raise ValueError("Share indices and shapes must align across clients")
            # Combine corresponding shares BEFORE reconstruction. No individual
            # client's activation vector is reconstructed by this aggregator.
            summed = sum((part.share_values.astype(object) for part in parts)) % self.prime
            combined.append((index, np.asarray(summed, dtype=np.int64)))
        total = self.sss.reconstruct_vector(combined)
        return total.astype(np.float64) / len(all_shares)

    def refresh_shares(self, client_id: str, activations: np.ndarray, num_participants: int) -> List[ActivationShare]:
        """Refresh shares after each forward/backward pass."""
        return self.generate_shares(client_id, activations, num_participants)
